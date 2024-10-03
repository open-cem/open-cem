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
from OpenCEM.cem_lib_controllers import Controller, SwitchingExcessController, DynamicExcessController, TemperatureExcessController
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


#IP_address = get_local_ip()     # get the local ip - TODO: activate this again
IP_address = "192.168.0.76"


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
            device_dict["type"] = device.type
            device_dict["state"] = device.state
            device_dict["value"] = f"{device.value:.2f}"
            device_dict["unit"] = device.unit
            device_dict["error_code"] = device.error_code

            devices_dict_list.append(device_dict)

        except Exception:
            raise NotImplementedError("Error building the device dictionary")

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
            print('Data sent successfully to webpage')
        else:
            print('Failed to send data to webpage')
    except asyncio.TimeoutError:
        logging.error("System was not able to send data to the webpage.")


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
            print('Failed to get "shutdown_requested" from webpage')
    except asyncio.TimeoutError:
        logging.error("No response from webpage in time.")
    # return false when request failed
    return False

async def download_xml(uuid):
    """
    This function will download the XML for a SGr Device from the CEM-Cloud and save it as uuid.xml
    :param uuid: the uuid of the SGr-File (given by CEM-Cloud)
    :return:
    """
    url = f"https://cem-cloud-p5.ch/api/smartgridready/{uuid}"      # TODO: set url as aparameter
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

def find_device(devices_list: list, name: str):

    device_found = None

    for device in devices_list:
        if device.name == name:
            device_found = device

    return device_found


async def parse_yaml(path2configurationYaml: str):
    """
    This function reads a configuration yaml, creates instances of devices, sensors, etc. and connects them.
    :param path2configurationYaml: The YAML configuration that should get parsed
    :return: lists for communicationChannels, devices and controllers
    """
    with open(path2configurationYaml, "r") as f:
        data = yaml.safe_load(f)

        #vdefine empty lists
        communication_channels_list = []
        devices_list = []
        controllers_list = []

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
                                                       nativeEID=nativeEID, simulationModel=simulationModel,
                                                       isLogging=isLogging,
                                                       communicationChannel=communicationChannel,
                                                       address=address, has_energy_import=hasEnergyImport,
                                                       has_energy_export=hasEnergyExport, maxPower=maxPower)

                    case "TEMPERATURE_SENSOR":
                        address = extra["address"]
                        maxTemp = extra["maxTemp"]
                        minTemp = extra["minTemp"]

                        device_temporary = TemperatureSensor(name=name, type=type, smartGridreadyEID=smartgridreadyEID,
                                                             nativeEID=nativeEID, simulationModel=simulationModel,
                                                             isLogging=isLogging,
                                                             communicationChannel=communicationChannel,
                                                             address=address, minTemp=minTemp, maxTemp=maxTemp)
                    case "RELAIS_SWITCH":
                        ip_address = extra["address"]
                        n_channels = extra["nChannels"]
                        device_temporary = RelaisActuator(name=name, type=type, smartGridreadyEID=smartgridreadyEID,
                                                nativeEID=nativeEID, simulationModel=simulationModel,
                                                isLogging=isLogging,
                                                communicationChannel=communicationChannel,
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
                                    communicationChannel=communicationChannel, address=address,
                                    port=port, minPower=minPower, maxPower=maxPower, phases=phases)

                devices_list.append(device_temporary)   # add the device to the list and continue for loop with the next device

        # parse controllers

        if data.get("controllers") is not None:
            controllers_data = data["controllers"]

            for controller in controllers_data:
                name = controller["name"]
                type = controller["type"]
                mainMeterStr = controller["mainMeter"]
                mainMeter = find_device(devices_list,mainMeterStr)
                deviceMeterStr = controller["deviceMeter"]
                deviceMeter = find_device(devices_list,deviceMeterStr)
                controlledDeviceStr = controller["controlledDevice"]
                controlledDevice = find_device(devices_list,controlledDeviceStr)
                functionalProfile = controller["functionalProfile"]
                controllerSettings = controller["controllerSettings"]


                # decision tree for controller type
                match type:
                    case "SWITCHING_EXCESS_CONTROLLER":
                        controller_temporary = SwitchingExcessController(name=name, mainMeter=mainMeter,
                                                                         deviceMeter=deviceMeter, controlledDevice=controlledDevice,
                                                                         controllerSettings=controllerSettings)
                    case "DYNAMIC_EXCESS_CONTROLLER":
                        controller_temporary = DynamicExcessController(name=name, mainMeter=mainMeter,
                                                                        deviceMeter=deviceMeter,
                                                                        controlledDevice=controlledDevice,
                                                                        controllerSettings=controllerSettings)
                    case "TEMPERATURE_EXCESS_CONTROLLER":
                        controller_temporary = TemperatureExcessController(name=name, mainMeter=mainMeter,
                                                                        deviceMeter=deviceMeter,
                                                                        controlledDevice=controlledDevice,
                                                                        functionalProfile=functionalProfile,
                                                                        controllerSettings=controllerSettings)

                    case _:
                        raise NotImplementedError("Controller type not known.")

                controllers_list.append(controller_temporary)


        # return all the lists
        return communication_channels_list, devices_list, controllers_list
