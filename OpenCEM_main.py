"""
---------------------------------------------------------------
OpenCEM main function
OpenCEM = Open Source Custom Energy Manager
Demonstration for use of SmartGridready library
---------------------------------------------------------------
Fachhochschule Nordwestschweiz, Institut für Automation
Authors: Prof. Dr. D. Zogg, S. Ferreira, Ch. Zeltner, M. Krebs
Version: 2.1, February 2026
---------------------------------------------------------------
"""

# Imports
import logging
import asyncio
import OpenCEM.cem_lib_components
import yaml
import os
import paho.mqtt.client as mqtt
from OpenCEM.cem_lib_auxiliary_functions import parse_yaml, calculation_loop
import config_helper

from Data_Logger import InfluxDataLogger
import threading

# Load configuration from YAML file
config_path = os.environ.get('CONFIG_PATH', 'settings')
try:
    with open(os.path.join(config_path, "OpenCEM_settings.yaml"), "r") as file:
        config = yaml.safe_load(file)
except Exception:
    config = {}

# Override configuration with environment variables
mqtt_address = config_helper.get_setting('MQTT_HOST', 'mqtt_address', settings=config, default_value='localhost')
mqtt_port = int(config_helper.get_setting('MQTT_PORT', 'mqtt_port', settings=config, default_value=1883))
influxDB_address = config_helper.get_setting('INFLUX_HOST', 'influxDB_address', settings=config, default_value='localhost')
influxDB_port = int(config_helper.get_setting('INFLUX_PORT', 'influxDB_port', settings=config, default_value=8086))
influxDB_user = config_helper.get_setting('INFLUX_USER', 'influxDB_user', settings=config, default_value='')
influxDB_password = config_helper.get_setting('INFLUX_PASSWORD', 'influxDB_password', settings=config, default_value='')
loop_time = int(config_helper.get_setting('LOOP_TIME', 'loop_time', settings=config, default_value=60))
simulation_speed = float(config_helper.get_setting('SIMULATION_SPEED', 'simulation_speed', settings=config, default_value=1.0))


async def main():
    global config_path
    global mqtt_address, mqtt_port
    global influxDB_address, influxDB_port, influxDB_user, influxDB_password
    global loop_time, simulation_speed
    try:
        # set variables for the library
        OpenCEM.cem_lib_components.simulation_speed_up_factor = simulation_speed

        # parse yaml
        devices_list = await parse_yaml(os.path.join(config_path, "config.yaml"))

        # start MQTT client
        mqtt_client = mqtt.Client()
        mqtt_client.connect(mqtt_address, mqtt_port)
        mqtt_client.loop_start()

        # start InfluxDB logger
        influx_logger = InfluxDataLogger(
            influx_host=influxDB_address,
            influx_port=influxDB_port,
            influx_user=influxDB_user,
            influx_password=influxDB_password,
            mqtt_broker=mqtt_address,
            mqtt_port=mqtt_port,
            mqtt_topic="openCEM/value",
        )
        # start logger thread
        logger_thread = threading.Thread(target=influx_logger.start_logging)
        logger_thread.daemon = True
        logger_thread.start()
        print("InfluxDB logger thread started")

        # start calculation loop
        task_calculation_loop = asyncio.create_task(
            calculation_loop(devices_list, loop_time, mqtt_client)
        )

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
            print("Stopping MQTT client")
            try:
                mqtt_client.loop_stop()
                mqtt_client.disconnect()
                print("MQTT client stopped")
            except Exception as e:
                print(f"MQTT stop error: {e}")

        # Wait for logger thread
        if logger_thread and logger_thread.is_alive():
            logger_thread.join(timeout=3)

        print("OpenCEM cleanup completed")


if __name__ == "__main__":
    asyncio.run(main())
