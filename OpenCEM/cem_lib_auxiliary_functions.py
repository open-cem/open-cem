# Generative AI was used for some Code

import asyncio
import datetime
import logging
import os
import socket
import urllib
import aiohttp.client
import yaml
from OpenCEM.cem_lib_components import CommunicationChannel, PowerSensor, \
    HeatPump, EVCharger, TemperatureSensor, RelaisActuator
from OpenCEM.cem_lib_controllers import ExcessController, StepwiseExcessController, DynamicExcessController, \
    coverage_controller, PriceController
from sgr_library.modbusRTU_interface_async import SgrModbusRtuInterface
from sgr_library.modbusRTU_client_async import SGrModbusRTUClient


def get_local_ip():
    # gets the own ip-address and returns it
    try:
        # Create a socket object
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Use a dummy address to get the local IP address
        s.connect(("8.8.8.8", 80))

        # Get the local IP address
        local_ip = s.getsockname()[0]

        return local_ip
    except Exception as e:
        print("Error:", e)
        return None


IP_address = get_local_ip()     # get the local ip


def create_webpage_dict(devices_list: list) -> dict:
    """
    This function will create a dict with the important information of the devices. Used for the GUI.
    :param devices_list:
    :return: dict with device information. Will be sent later tothe GUI
    """
    return_dict = {}
    devices_dict_list = []
    return_dict["timestamp"] = datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S")

    for device in devices_list:
        device_dict = {}
        try:
            device_dict["name"] = device.name
            device_dict["power"] = device.power_sensor_power
            device_dict["type"] = device.device_type
            device_dict["status"] = device.state
            if device.room_temperature_sensor is not None:
                device_dict["room_temperature"] = device.room_temperature
            if device.storage_temperature_sensor is not None:
                device_dict["storage_temperature"] = device.storage_temperature
            devices_dict_list.append(device_dict)
            if isinstance(device, EvCharger):
                device_dict["ev_state"] = device.ev_state
        except Exception:
            raise NotImplementedError("Error building the dictionary")

    return_dict["devices_list"] = devices_dict_list

    return return_dict


async def send_data_to_webpage(data_dict: dict, session):
    """
    Sends a dict to the /update Endpoint of the Webserver. Used to update the data displayed on the GUI
    :param data_dict: dict created with create_webpage_dict()
    :param session:
    :return:
    """

    url = f'http://{IP_address}:8000/update'

    try:
        max_time_out = aiohttp.client.ClientTimeout(total=3)  # max allowed timeout for a request
        async with session.post(url, json=data_dict, timeout=max_time_out) as response:
            status_code = response.status
        if status_code == 200:
            print('Message sent successfully')
        else:
            print('Failed to send message')
    except asyncio.TimeoutError:
        logging.error("System was not able to send data to the GUI.")


async def check_OpenCEM_shutdown(session):
    """
    Will check if a shutdown of the OpenCEM was requested on the GUI
    :param session: aiohttp session
    :return: True for shutdown, False for no shutdown
    """
    url = f'http://{IP_address}:8000/shutdown_requested'

    try:
        max_time_out = aiohttp.client.ClientTimeout(total=2)  # max allowed timeout for a request
        async with session.get(url, timeout=max_time_out) as response:
            status_code = response.status
            restart_text = await response.text()

        if status_code == 200:
            if restart_text == "True":
                return True
            else:
                return False
        else:
            print('Failed to request "restart_requested" from endpoint')
    except asyncio.TimeoutError:
        logging.error("No response from GUI in time.")
    # return false when request failed
    return False


def add_sensor_actuator_controller_by_id(device, sensor_id_list=None, actuator_id=None, controller_id=None,
                                         sensors_list=None, actuators_list=None, controllers_list=None,
                                         actuator_channels=None, channel_config=None):
    """
    This function adds sensors, actuators or a controller to device
    :param actuator_channels: the channel numbers of the actuator that the device uses
    :param channel_config: the configuration of the actuator channels to get a certain mode
    :return:
    """

    # add all the sensors
    for sensor_id in sensor_id_list:

        if sensor_id is not None and sensors_list is not None:
            sensor = search_object_by_id(sensors_list, sensor_id)
            if isinstance(sensor, PowerSensor):
                device.add_power_sensor(sensor)
            if isinstance(sensor, TemperatureSensorRoom):
                device.add_room_temperature_sensor(sensor)
            if isinstance(sensor, TemperatureSensorStorage):
                device.add_storage_temperature_sensor(sensor)

    # add an actuator
    if actuator_id is not None and actuators_list is not None and actuator_channels is not None:
        actuator = search_object_by_id(actuators_list, actuator_id)
        if isinstance(actuator, RelaisActuator):
            device.add_actuator(actuator, actuator_channels)
            if channel_config is not None:
                device.set_mode_config(channel_config)

    # add a controller
    if controller_id is not None and controllers_list is not None:
        controller = search_object_by_id(controllers_list, controller_id)
        device.add_controller(controller)


async def download_xml(uuid):
    """
    This function will download the XML for a SGr Device from the CEM-Cloud and save it as uuid.xml
    :param uuid: the uuid of the SGr-File (given by CEM-Cloud)
    :return:
    """
    url = f"https://cem-cloud-p5.ch/api/smartgridready/{uuid}"
    async with aiohttp.request('GET', url) as response:
        status_code = response.status
        xml_file = await response.read()  # response is xml in bytes

    # request successful
    if status_code == 200:
        try:
            # save file
            with open(f"xml_files/{uuid}.xml", "wb") as f:  # write it as bytes
                f.write(xml_file)
                logging.info(f"Downloaded SGr File with uuid:{uuid} successfully.")
                return True
        except EnvironmentError:
            logging.error(f"Error with writing downloaded XML (uuid: {uuid}) to disk")
    else:
        logging.warning(
            f"Download of SGr File failed. Check connection and uuid ({uuid}) of the devices in the field smartGridreadyFileId.")
    return False


def parse_yaml_devices(path2configurationYaml: str):
    """
    This function reads the list of devices from the configuration yaml, but does not create any instances
    :param path2configurationYaml: The YAML configuration that should get parsed
    :return: list for devices
    """
    devices_list = []
    with open(path2configurationYaml, "r") as f:
        data = yaml.safe_load(f)
        if data.get("devices") is not None:
            devices_data = data["devices"]
            for device in devices_data:
                device_name = device.get("name")
                devices_list.append(device_name)  # add the device to the list and continue for loop with the next device
    return devices_list

async def parse_yaml(path2configurationYaml: str):
    """
    This function reads a configuration yaml, creates instances of devices, sensors, etc. and connects them.
    :param path2configurationYaml: The YAML configuration that should get parsed
    :return: lists for devices, communicationChannels, sensors, actuators, controllers
    """
    with open(path2configurationYaml, "r") as f:
        data = yaml.safe_load(f)

        #vdefine empty lists
        communication_channels_list = []
        actuators_list = []
        sensors_list = []
        controllers_list = []
        devices_list = []

        # parse communication channels
        if data.get("communicationChannels") is not None:

            # parse every communicationChannel from the list
            for communication_channel in data.get("communicationChannels"):
                type = communication_channel["type"]
                extra = communication_channel["extra"]
                communication_channels_list.append(CommunicationChannel(type, extra))

        # create Client for HTTP Communication. OpenCEM_id is 1 for this Client
        http_main_client = CommunicationChannel("HTTP_MAIN", None)
        communication_channels_list.append(http_main_client)

        # hotfix for SGr Library creating multiple clients. now only one global client exists for RTU
        sgr_rtu_client = http_main_channel = next(
            (obj for obj in communication_channels_list if obj.type == "MODBUS_RTU"),
            None)  # returns the MODBUS_RTU communication channel
        if sgr_rtu_client is not None:
            SgrModbusRtuInterface.globalModbusRTUClient = SGrModbusRTUClient("", "", "",
                                                                             client=sgr_rtu_client)  # set the global client for SGr RTU Devices

        # parse actuators
        if data.get("actuators") is not None:
            data_actuators = data["actuators"]

            # parse every actuator from the list
            for actuator in data_actuators:
                name = actuator["name"]
                type = actuator["type"]
                smartgridreadyEID = actuator.get("smartGridreadyEID")
                nativeEID = actuator.get("nativeEID")
                isLogging = actuator["isLogging"]
                communication_channel = actuator["communicationChannel"]
                extra = actuator["extra"]

                # find communication channel
                #communication_channel_temp = search_object_by_id(communication_channels_list, communication_channel)

                if type == "RELAIS_SWITCH":
                    ip_address = extra["address"]
                    n_channels = extra["nChannels"]
                    relais = RelaisActuator(name=name, type=type, smartGridreadyEID=smartgridreadyEID,
                                            nativeEID=nativeEID, isLogging=isLogging,
                                            communicationChannel=communication_channel,
                                            address=ip_address,nChannels=n_channels)
                    actuators_list.append(relais)
                else:
                    raise NotImplementedError(f"Actuator {type} not known")

        # create Sensors
        if data.get("sensors") is not None:
            data_sensors = data["sensors"]

            # parse every sensor from the list
            for sensor in data_sensors:
                type = sensor.get("type")
                name = sensor.get("name")
                model = sensor.get("model")
                smartgridreadyEID = actuator.get("smartGridreadyEID")
                smartgridready_XML = f"../SGrPython/xml_files/{smartgridreadyEID}.xml"
                nativeEID = actuator.get("nativeEID")
                native_YAML = f"yaml/{nativeEID}.yaml"
                simulationModel = actuator.get("simulationModel")
                isLogging = sensor.get("isLogging")
                communication_channel = sensor.get("communicationId")
                extra = sensor.get("extra")

                # find communication channel
                #communication_channel_temp = search_object_by_id(communication_channels_list, communication_id)
                #if communication_channel_temp is not None:
                #    comm_type = communication_channel_temp.type
                #else:
                #    raise NotImplementedError

                # decision tree for sensor type
                match type:
                    case "POWER_SENSOR":
                        address = extra["address"]
                        hasEnergyImport = extra["hasEnergyImport"]
                        hasEnergyExport = extra["hasEnergyExport"]
                        maxPower = extra["maxPower"]

                        sensor_temporary = PowerSensor(name=name, type=type, smartGridreadyEID=smartgridready_XML,
                                                       nativeEID=native_YAML, isLogging=isLogging,
                                                       communicationChannel=communication_channel,
                                                       address=address, has_energy_import=hasEnergyImport,
                                                       has_energy_export=hasEnergyExport, maxPower=maxPower)

                    case "TEMPERATURE_SENSOR":
                        address = extra["address"]
                        maxTemp = extra["maxTemp"]
                        minTemp = extra["minTemp"]

                        sensor_temporary = TemperatureSensor(name=name, type=type, smartGridreadyEID=smartgridready_XML,
                                                       nativeEID=native_YAML, isLogging=isLogging,
                                                       communicationChannel=communication_channel,
                                                       address=address, minTemp=minTemp, maxTemp=maxTemp)


                    case _:
                        raise NotImplementedError(f"Sensor {type} not known")

                sensors_list.append(sensor_temporary)

        # parse devices

        if data.get("devices") is not None:
            devices_data = data["devices"]

            for device in devices_data:
                name = device.get("name")
                type = device.get("type")
                smartgridreadyEID = device.get("smartGridreadyEID")
                smartgridreadyEID_path = f"xml/{smartgridreadyEID}.xml" # TODO: adapt path
                nativeEID = device.get("nativeEID")
                nativeEID_path = f"yaml/{nativeEID}.yaml" # TODO: adapt path
                simulationModel = device.get("simulationModel")
                isLogging = device.get("isLogging")
                communicationChannel = device.get("communicationChannel")
                extra = device.get("extra")

                # decision tree for device types
                match type:
                    case "POWER_SENSOR":
                        address = extra["address"]
                        hasEnergyImport = extra["hasEnergyImport"]
                        hasEnergyExport = extra["hasEnergyExport"]
                        maxPower = extra["maxPower"]

                        device_temporary = PowerSensor(name=name, type=type, smartGridreadyEID=smartgridreadyEID,
                                                       nativeEID=nativeEID, isLogging=isLogging,
                                                       communicationChannel=communication_channel,
                                                       address=address, has_energy_import=hasEnergyImport,
                                                       has_energy_export=hasEnergyExport, maxPower=maxPower)

                    case "TEMPERATURE_SENSOR":
                        address = extra["address"]
                        maxTemp = extra["maxTemp"]
                        minTemp = extra["minTemp"]

                        device_temporary = TemperatureSensor(name=name, type=type, smartGridreadyEID=smartgridready_XML,
                                                             nativeEID=native_YAML, isLogging=isLogging,
                                                             communicationChannel=communication_channel,
                                                             address=address, minTemp=minTemp, maxTemp=maxTemp)
                    case "RELAIS_SWITCH":
                        ip_address = extra["address"]
                        n_channels = extra["nChannels"]
                        device_temporary = RelaisActuator(name=name, type=type, smartGridreadyEID=smartgridreadyEID,
                                                nativeEID=nativeEID, isLogging=isLogging,
                                                communicationChannel=communication_channel,
                                                address=ip_address, nChannels=n_channels)

                    case "HEAT_PUMP":
                        address = extra.get("address")
                        port = extra.get("port")
                        minPower = extra.get("minPower")
                        maxPower = extra.get("maxPower")

                        device_temporary = HeatPump(name=name, type=type,
                                                    smartGridreadyEID=smartgridreadyEID, nativeEID=nativeEID,
                                                    simulationModel=simulationModel,isLogging=isLogging,
                                                    communicationChannel=communicationChannel,address=address,
                                                    port=port,minPower=minPower,maxPower=maxPower)


                    case "EV_CHARGER":
                        address = extra.get("address")
                        port = extra.get("port")
                        minPower = extra.get("minPower")
                        maxPower = extra.get("maxPower")
                        phases = extra.get("phases")

                        device_temporary = EVCharger(name=name, type=type,
                                    smartGridreadyEID=smartgridreadyEID, nativeEID=nativeEID,
                                    simulationModel=simulationModel, isLogging=isLogging,
                                    communicationChannel=communication_channel, address=address,
                                    port=port, minPower=minPower, maxPower=maxPower, phases=phases)

                devices_list.append(device_temporary)   # add the device to the list and continue for loop with the next device

        # parse controllers

         # CONTROLLERS UNDER CONSTRUCTION

        if data.get("controllers") is not None:
            controllers_data = data["controllers"]

            for controller in controllers_data:
                name = controller["name"]
                type = controller["type"]
                extra = controller["extra"]

                # decision tree for controller type
                match type:
                    case "EXCESS_CONTROLLER":
                        limit = int(extra["limit"])
                        controller_temporary = ExcessController(limit=limit, OpenCEM_id=OpenCEM_id)
                    case "STEPWISE_EXCESS_CONTROLLER":
                        limits = extra["limits"]
                        controller_temporary = StepwiseExcessController(limits=limits, OpenCEM_id=OpenCEM_id)
                    case "DYNAMIC_EXCESS_CONTROLLER":
                        min_limit = extra["limitMin"]
                        max_limit = extra["limitMax"]
                        controller_temporary = DynamicExcessController(min_limit=min_limit, max_limit=max_limit,
                                                                       OpenCEM_id=OpenCEM_id)
                    case "COVERAGE_CONTROLLER":
                        limit = int(extra["limit"])
                        controller_temporary = coverage_controller(limit=limit, OpenCEM_id=OpenCEM_id)
                    case "PRICE_CONTROLLER":
                        gridTarif = extra["gridTarif"]
                        solarTarif = extra["solarTarif"]
                        minState = extra["minState"]
                        maxState = extra["maxState"]
                        controller_temporary = PriceController(min_state=minState, max_state=maxState,
                                                               solar_tarif=solarTarif, grid_tarif=gridTarif,
                                                               OpenCEM_id=OpenCEM_id)
                    case _:
                        raise NotImplementedError("Controller type not known.")

                controllers_list.append(controller_temporary)


        # return all the lists
        return communication_channels_list, actuators_list, sensors_list, controllers_list, devices_list
