# REST API for OpenCEM
# source: https://docs.aiohttp.org/en/stable/web_quickstart.html#run-a-simple-web-server
# D. Zogg, created on Sept 2024
# UNDER CONSTRUCTION: aiohttp compatible with asyncio

# Usage in Browser (GET methods only):
# http://localhost:5000/devices

import json
import asyncio
from aiohttp import web
from OpenCEM.cem_lib_auxiliary_functions import parse_yaml_devices

async def welcome(request):
    return web.Response(text="Welcome to OpenCEM REST API")

async def get_devices(request):
    return web.json_response(devices_list)

if __name__ == '__main__':
#async def main():
    devices_list = ['heatpump', 'evcharging', 'household']
    path_OpenCEM_config = "yaml/openCEM_config.yaml"
    devices_list = parse_yaml_devices(path_OpenCEM_config)

    app = web.Application()
    app.add_routes([web.get('/', welcome),
                    web.get('/devices', get_devices)])

    web.run_app(app, host='localhost', port=5000)

#asyncio.run(main())