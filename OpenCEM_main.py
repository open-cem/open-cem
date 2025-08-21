"""
-------------------------------------------------------
OpenCEM main function
OpenCEM = Open Source Custom Energy Manager
Demonstration for use of SmartGridready library
-------------------------------------------------------
Fachhochschule Nordwestschweiz, Institut für Automation
Authors: Prof. Dr. D. Zogg, S. Ferreira, Ch. Zeltner
Version: 2.0, October 2024
-------------------------------------------------------
"""

# Imports
import asyncio
import logging
import urllib
#from sgr_library import SGrDevice

import aiohttp
from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient
import subprocess
import OpenCEM.cem_lib_components
import yaml

import paho.mqtt.client as mqtt
import json
from OpenCEM.cem_lib_components import Device, PowerSensor, TemperatureSensor, RelaisActuator, HeatPump, EVCharger, OpenCEM_RTU_client
from OpenCEM.cem_lib_controllers import Controller, SwitchingExcessController, DynamicExcessController, TemperatureExcessController
from OpenCEM.cem_lib_loggers import  create_event_logger, create_device_logger, show_logger_in_console
from datetime import datetime, timedelta
from OpenCEM.cem_lib_auxiliary_functions import create_webpage_dict, send_data_to_webpage, parse_yaml, check_OpenCEM_shutdown, ip_address, port, backend_url


from Data_Logger import InfluxDataLogger
import threading


# devices loop
async def calculation_loop(devices_list: list, controllers_list: list, period: int, MQTT_client):
    
    simulation_speed_up_factor = OpenCEM.cem_lib_components.simulation_speed_up_factor
    while True:

        # read all devices
        for device in devices_list:
            error_code = await device.read()
            if error_code:
                print(f"Error reading {device.name}: {error_code}")
        # update webpage
        webpage_dict = create_webpage_dict(devices_list)
        
        print("Webpage dict created:", webpage_dict)
        #await send_data_to_webpage(webpage_dict, HTTP_client)
        MQTT_client.publish('openCEM/value', json.dumps(webpage_dict))
        print("-----------------------------------------------")

        # sleep for a defined period (other tasks may run)
        await asyncio.sleep(period / simulation_speed_up_factor)

async def main():
    try:
        # load OpenCEM settings
        with open("yaml/OpenCEM_settings.yaml", "r") as f:
            settings = yaml.safe_load(f)
            loop_time = settings.get("loop_time")
            simulation_speed_up = settings.get("simulation_speed_up")
            duration = settings.get("duration")
            log_events = settings.get("log_events")
            log_devices = settings.get("log_devices")
            console_logging_level = settings.get("console_logging_level")
            path_OpenCEM_config = settings.get("path_OpenCEM_config")
        

        # set variables for the library
        OpenCEM.cem_lib_components.simulation_speed_up_factor = simulation_speed_up

        # start logging
        if log_events:
            create_event_logger()
        if log_devices:
            create_device_logger()
        if console_logging_level >= 0:
            show_logger_in_console(console_logging_level)
        logging.info("OpenCEM started")

       
        
        
        # parse yaml
        
        communication_dict, communication_channels_list, devices_list, controllers_list = await parse_yaml(path_OpenCEM_config)
    
        """
        # start pymodbus clients - TODO: check this
        for channel in communication_channels_list:
            if channel.type == "MODBUS_RTU":
                await channel.client.connect()
        """

         # start MQTT client
        mqtt_client = mqtt.Client()
        mqtt_client.connect('192.168.137.10', 1883)  # Use your broker address/port if different
        mqtt_client.loop_start()

        # start InfluxDB logger
        influx_logger = InfluxDataLogger(
        influx_host= '192.168.137.221',
        mqtt_broker= '192.168.137.10',
        mqtt_topic='openCEM/value'
        )

        logger_thread = threading.Thread(target=influx_logger.start_logging)
        logger_thread.daemon = True  # Dies when main program dies
        logger_thread.start()
        print("Data Logger (InfluxDB) started in background thread")

        
        # start calculation loop
        task_calculation_loop = asyncio.create_task(
            calculation_loop(devices_list, controllers_list, loop_time, mqtt_client))

        await task_calculation_loop

    except Exception as e:
        print(f"OpenCEM error: {e}")
        logging.error(f"OpenCEM error: {e}")
    finally:
        # Stop calculation loop
        if task_calculation_loop and not task_calculation_loop.done():
            print("  Stopping calculation loop...")
            task_calculation_loop.cancel()
            try:
                await task_calculation_loop
            except asyncio.CancelledError:
                print("  ✅ Calculation loop stopped")

        # Stop MQTT client
        if mqtt_client:
            print("  Stopping MQTT client...")
            try:
                mqtt_client.loop_stop()
                mqtt_client.disconnect()
                print(" MQTT client stopped")
            except Exception as e:
                print(f" MQTT stop error: {e}")
        
        # Wait for logger thread
        if logger_thread and logger_thread.is_alive():
            logger_thread.join(timeout=3)

        # Close communication clients
        for obj in communication_channels_list:
            if obj.client is not None:
                try:
                    if isinstance(obj.client, aiohttp.ClientSession):
                        await obj.client.close()
                    else:
                        obj.client.close()
                except Exception as e:
                    print(f"Error closing client: {e}")

        logging.info("OpenCEM stopped")
        print("OpenCEM cleanup completed")

    
    logging.info("GUI closed, OpenCEM stopped")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())