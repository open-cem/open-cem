"""
---------------------------------------------------------------
cem_lib_auxiliary functions
Library for OpenCEM
Contains auxiliary functions for web and yaml parsing
---------------------------------------------------------------
Fachhochschule Nordwestschweiz, Institut für Automation
Authors: Prof. Dr. D. Zogg, S. Ferreira, Ch. Zeltner, M. Krebs
Version: 2.1, February 2026
---------------------------------------------------------------
"""

import asyncio
import datetime
import yaml
from OpenCEM.cem_lib_components import Device
import OpenCEM.cem_lib_components
import json


async def calculation_loop(devices_list: list, period: int, MQTT_client):

    simulation_speed_up_factor = OpenCEM.cem_lib_components.simulation_speed_up_factor
    while True:

        # read all devices
        for device in devices_list:
            await device.read()
        # update webpage
        value_dict = create_dict(devices_list)

        MQTT_client.publish("openCEM/value", json.dumps(value_dict))
        print("-----------------------------------------------")

        # sleep for a defined period (other tasks may run)
        await asyncio.sleep(period / simulation_speed_up_factor)


def create_dict(devices_list: list) -> dict:
    """
    This function will create a dict with the important information of the devices. Used for the GUI.
    :param devices_list:
    :return: dict with device information. Will be sent later tothe GUI
    """
    return_dict = {}
    devices_dict_list = []
    return_dict["timestamp"] = datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
    # print("devices_list", devices_list)

    for device in devices_list:
        device_dict = {}
        try:
            device_dict["name"] = device.name
            device_dict["datapoints"] = device.datapoint_values

            devices_dict_list.append(device_dict)

        except Exception:
            raise NotImplementedError("Error building the device dictionary")

    return_dict["devices_list"] = devices_dict_list

    return return_dict


async def parse_yaml(path2configurationYaml: str):
    """
    This function reads a configuration yaml, creates instances of devices, sensors, etc. and connects them.
    :param path2configurationYaml: The YAML configuration that should get parsed
    :return: lists for communicationChannels, devices and controllers
    """
    with open(path2configurationYaml, "r") as f:

        devices_list = []
        EID_param = {}

        # parse devices
        data = yaml.safe_load(f)
        if data.get("devices") is not None:
            devices_data = data["devices"]

            for device in devices_data:
                print("device", device)
                name = device.get("name")
                smartgridreadyEID = "xml_files/" + device.get("smartGridreadyEID")
                EID_param = device.get("parameters")
                dp_list = device.get("datapoints", [])

                device_temporary = Device(
                    name=name,
                    smartGridreadyEID=smartgridreadyEID,
                    param=EID_param,
                    dp_list=dp_list,
                )

                if smartgridreadyEID is not None:
                    print("smartgridreadyEID", smartgridreadyEID)
                    print("EID_param", EID_param)
                    print(type(EID_param))
                    await device_temporary.connect(
                        smartgridreadyEID, EID_param
                    )  # initialize the device with the SGr EID and parameters

                devices_list.append(
                    device_temporary
                )  # add the device to the list and continue for loop with the next device

        return devices_list
