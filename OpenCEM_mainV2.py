# Generative AI was used for some Code
"""
This File runs the OpenCEM main function
"""

# TODO: make it run again!

# Imports
import asyncio
import logging
import urllib
from sgr_library import SGrDevice

import aiohttp
from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient
import subprocess
import OpenCEM.cem_lib_components
import yaml

from OpenCEM.cem_lib_components import Device, PowerSensor, TemperatureSensor, RelaisActuator, HeatPump, EVCharger
from OpenCEM.cem_lib_controllers import Controller, SwitchingExcessController, DynamicExcessController, TemperatureExcessController
from OpenCEM.cem_lib_loggers import create_statistics_logger_devices, create_event_logger, show_logger_in_console
from datetime import datetime, timedelta
from OpenCEM.cem_lib_auxiliary_functions import create_webpage_dict, send_data_to_webpage, parse_yaml, check_OpenCEM_shutdown
from sgr_library.modbusRTU_interface_async import SgrModbusRtuInterface


# devices loop
async def calculation_loop(devices_list: list, controllers_list: list, period: int, HTTP_client):
    simulation_speed_up_factor = OpenCEM.cem_lib_components.simulation_speed_up_factor
    while True:

        for controller in controllers_list:
            error_code = await controller.calc_controller()

        # update webpage
        webpage_dict = create_webpage_dict(devices_list)
        await send_data_to_webpage(webpage_dict, HTTP_client)

        # reset reserved power before the next iteration
        await asyncio.sleep(period / simulation_speed_up_factor
)  # repeat loop every (period) seconds

        # check if a restart is requested
        restart_requested = await check_OpenCEM_shutdown(HTTP_client)
        if restart_requested:
            print("OpenCEM is restarting soon")
            return

async def main():

    # load OpenCEM settings
    with open("yaml/OpenCEM_settings.yaml", "r") as f:
        settings = yaml.safe_load(f)
        loop_time = settings.get("loop_time")
        simulation_speed_up = settings.get("simulation_speed_up")
        duration = settings.get("duration")
        log_events = settings.get("log_events")
        log_stats = settings.get("log_stats")
        console_logging_level = settings.get("console_logging_level")
        installation = settings.get("installation")
        password = settings.get("password")
        token = settings.get("token")
        backend_url = settings.get("backend_url")
        path_OpenCEM_config = settings.get("path_OpenCEM_config")

    # set variables for the library
    OpenCEM.cem_lib_components.simulation_speed_up_factor = simulation_speed_up

    # start logging
    if log_stats:
        create_statistics_logger_devices()
    if log_events:
        create_event_logger()
    if console_logging_level >= 0:
        show_logger_in_console(console_logging_level)
    logging.info("OpenCEM started")

    # start GUI webserver
    gui_subprocess = subprocess.Popen(["venv/Scripts/python", "GUI_server.py"])  # Important!!! for Windows venv/Scripts/python, Linux myenv/bin/python
    await asyncio.sleep(2)    # wait 2 seconds so that the GUI is ready

    # load OpenCEM YAML configuration if available
    if path_OpenCEM_config is None or path_OpenCEM_config == "":
        url = backend_url + "/installations/" + installation + "/configuration?token=" + urllib.parse.quote_plus(token)
        async with aiohttp.request('GET', url) as response:
            status_code = response.status
            yaml_text = await response.text()

        if status_code == 200:
            try:
                with open("yaml/openCEM_config.yaml", "w") as f:
                    yaml.dump(yaml.safe_load(yaml_text), f, sort_keys=False)
                    path_OpenCEM_config = "yaml/openCEM_config.yaml"
                    logging.info("Downloaded YAML configuration successfully.")
            except EnvironmentError:
                logging.error("Error with writing downloaded YAML to disk")
        else:
            logging.warning(
                "YAML could not be downloaded from the server. Check installation nr., backend url and token.")
            gui_subprocess.terminate()  # close GUI subprocess
            logging.info("GUI closed, OpenCEM stopped due to error with downloading configuration YAML.")
            return  # OpenCEM gets stopped

    # parse yaml
    communication_channels_list, devices_list, controllers_list = await parse_yaml(path_OpenCEM_config)
    http_main_channel = next((obj for obj in communication_channels_list if obj.type == "HTTP_MAIN"),
                             None)  # returns the HTTP_MAIN from the list
    http_main_client = http_main_channel.client     # gets the main client from the communicationChannel

    # start pymodbus clients
    for channel in communication_channels_list:
        if channel.type in ["MODBUS_TCP", "MODBUS_RTU"]:
            await channel.client.connect()

    # start calculation loop
    task_calculation_loop = asyncio.create_task(
        calculation_loop(devices_list, controllers_list, loop_time, http_main_client))

    # run main for given duration
    if duration != 0:
        await asyncio.sleep(duration)
        task_calculation_loop.cancel()
    # if no duration is given OpenCEM will run till stopped through the GUI
    else:
        await task_calculation_loop

    # stop programm
    task_calculation_loop.cancel()
    for device in devices_list:
        if device.simulated:
            device.simulation_task.cancel()

    # close running communication clients
    for obj in communication_channels_list:
        if obj.client is not None:
            if isinstance(obj.client, aiohttp.ClientSession):
                await obj.client.close()
            else:
                obj.client.close()

    gui_subprocess.terminate()
    logging.info("GUI closed, OpenCEM stopped")

# to run infinite don't set duration
asyncio.run(main())
