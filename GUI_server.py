"""
-------------------------------------------------------
GUI_Server
Local web GUI for OpenCEM
-------------------------------------------------------
Fachhochschule Nordwestschweiz, Institut für Automation
Authors: Prof. Dr. D. Zogg, S. Ferreira, Ch. Zeltner
Version: 2.0, October 2024
-------------------------------------------------------
"""

from aiohttp import web
import socket
from OpenCEM.cem_lib_auxiliary_functions import get_local_ip

# Global variable to store the latest data
latest_data = {}
shutdown_requested = False

# function for the endpoints
async def handle(request):
    with open('templates/index.html', 'r') as file:
        content = file.read()
    return web.Response(text=content, content_type='text/html')


async def shutdown(request):
    global shutdown_requested
    shutdown_requested = True
    return web.Response(text='OpenCEM will shutdown soon...')


async def shutdown_requested_function(request):
    global shutdown_requested
    return web.Response(text=str(shutdown_requested))


async def update_data(request):
    global latest_data
    data = await request.json()
    latest_data = data  # Update the latest data

    return web.Response(text='Data received and updated successfully.')


async def get_latest_data(request):
    global latest_data
    return web.json_response(latest_data)


def start_GUI_server():
    #global ip_address
    #global port

    app = web.Application()
    # add endpoints to web server
    app.router.add_get('/', handle)
    app.router.add_post('/update', update_data)
    app.router.add_get('/latest_data', get_latest_data)
    app.router.add_post('/shutdown', shutdown)
    app.router.add_get('/shutdown_requested', shutdown_requested_function)

    ip_address = get_local_ip() # get local ip - TODO: activate this again
    #IP_address = '192.168.0.76'

    #ip_address= "10.223.11.58"      # TODO: get from settings
    port = 8000

    web.run_app(app, host=ip_address, port=port)

if __name__ == "__main__":
    start_GUI_server()
