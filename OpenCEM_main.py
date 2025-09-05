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

import asyncio

import aiohttp

import OpenCEM.cem_lib_components
import yaml

import paho.mqtt.client as mqtt

from OpenCEM.cem_lib_components import Device 

from OpenCEM.cem_lib_auxiliary_functions import parse_yaml, calculation_loop


from Data_Logger import InfluxDataLogger
import threading

async def main():
    try:
        # load OpenCEM settings
        with open("yaml/OpenCEM_settings.yaml", "r") as f:
            settings = yaml.safe_load(f)
            loop_time = settings.get("loop_time")
            simulation_speed_up = settings.get("simulation_speed_up")
            log_events = settings.get("log_events")
            log_devices = settings.get("log_devices")
            console_logging_level = settings.get("console_logging_level")
            path_OpenCEM_config = settings.get("path_OpenCEM_config")
        

        # set variables for the library
        OpenCEM.cem_lib_components.simulation_speed_up_factor = simulation_speed_up

        
        # parse yaml
        devices_list  = await parse_yaml(path_OpenCEM_config)
    

         # start MQTT client
        mqtt_client = mqtt.Client()
        mqtt_client.connect('192.168.137.10', 1883) 
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
        print("Data Logger started in background thread")

        
        # start calculation loop
        task_calculation_loop = asyncio.create_task(
            calculation_loop(devices_list, loop_time, mqtt_client))

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
                print(" Calculation loop stopped")

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

       
        print("OpenCEM cleanup completed")


if __name__ == "__main__":
    
    asyncio.run(main())