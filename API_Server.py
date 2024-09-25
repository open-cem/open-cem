# REST API for OpenCEM
# source: https://www.moesif.com/blog/technical/api-development/Building-RESTful-API-with-Flask/
# D. Zogg, created on Sept 2024
# UNDER CONSTRUCTION

# Installation:
# pip install flask
# OPEN ISSUE: ONLY RUNS on Python 3.8

# Usage in Browser (GET methods only):
# http://127.0.0.1:5000/devices
# http://127.0.0.1:5000/actuators
# http://127.0.0.1:5000/sensors

import json
from flask import Flask, jsonify, request
app = Flask(__name__)

import yaml
path_OpenCEM_config = "yaml/openCEM_config.yaml"

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
   # TODO: parse yaml
   # communication_channels_list, actuators_list, sensors_list, controllers_list, devices_list = parse_yaml(path_OpenCEM_config)

   devices_list = ['heatpump', 'evcharging', 'household']
   actuators_list = ['relais', 'switch1', 'switch2']
   sensors_list = ['temperature', 'power1', 'power2']

   # run server
   app.run(port=5000)