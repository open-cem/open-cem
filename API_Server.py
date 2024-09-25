# REST API for OpenCEM
# source: https://www.moesif.com/blog/technical/api-development/Building-RESTful-API-with-Flask/
# D. Zogg, created on Sept 2024
# UNDER CONSTRUCTION: flask not compatible with asyncio yet

# Installation:
# run "pip install flask" on Python Console

# Usage in Browser (GET methods only):
# http://127.0.0.1:5000/devices
# http://127.0.0.1:5000/actuators
# http://127.0.0.1:5000/sensors

import json
from flask import Flask, jsonify, request
app = Flask(__name__)

#import asyncio
from OpenCEM.cem_lib_auxiliary_functions import parse_yaml_devices

@app.route('/devices', methods=['GET'])
def get_devices():
 return jsonify(devices_list)

@app.route('/sensors', methods=['GET'])
def get_sensors():
 return jsonify(sensors_list)

@app.route('/actuators', methods=['GET'])
def get_actuators():
 return jsonify(actuators_list)


@app.route('/sensors', methods=['POST'])
def create_sensors():
 sensors_list = json.loads(request.data)
 if not sensors_list:
   return jsonify({ 'error': 'Invalid sensors properties.' }), 400

@app.route('/sensors/<int:id>', methods=['PUT'])
def update_sensors(id: int):
  updated_sensor = json.loads(request.data)
  # TODO: replace sensor with given id
  if not updated_sensor:
   return jsonify({'error': 'Invalid sensors properties.'}), 400

if __name__ == '__main__':
   # TODO: parse yaml asyncio
   #communication_channels_list, actuators_list, sensors_list, controllers_list, devices_list = parse_yaml(
   #    path_OpenCEM_config)

   devices_list = ['heatpump', 'evcharging', 'household']
   actuators_list = ['relais', 'switch1', 'switch2']
   sensors_list = ['temperature', 'power1', 'power2']

   path_OpenCEM_config = "yaml/openCEM_config.yaml"
   devices_list = parse_yaml_devices(path_OpenCEM_config)

   # run server
   app.run(port=5000)
