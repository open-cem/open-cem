import json
import aiohttp
from nicegui import ui
from sgr_commhandler.device_builder import DeviceBuilder
import yaml
import os
import logging
import plotly.graph_objects as go
import asyncio
from OpenCEM_main import main as OpenCEM_main
from multiprocessing import Queue

from shared_queue import plot_queue
# --------------------------
# Global Variables
# --------------------------


import paho.mqtt.client as mqtt

input_fields = {}
params = None
dropdown_identifier = None
dropdown_devices = None
params_datatype = None
device = None

latest_value_box = ui.input(label='Latest Value').classes('w-full')
textbox_setup = ui.input(label='Enter Setup Name').classes('w-full')
textbox_device = ui.input(label='Enter Product Name').classes('w-full')
popUp_deleteSystems = ui.dialog().props('persistent')

selected_datapoints = [] 
checkbox_dict = {} 

# MQTT callback
def on_message(client, userdata, msg):
    value = msg.payload.decode()
    # Update the textbox in the main thread
    #ui.run_later(lambda: latest_value_box.set_value(value))
    latest_value_box.value = value

async def start_mqtt():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect('192.168.137.10', 1883)  # Use your broker address
    client.subscribe('openCEM/value')
    client.loop_start()  # Start MQTT loop in background



def start_plot_update():
    asyncio.create_task(start_mqtt())


def start_OpenCEM():
    #asyncio.create_task(OpenCEM_main())
    pass
# --------------------------
#  Delete System
# --------------------------    

def delete_system():
    global dropdown_systems

    selected_system = dropdown_systems.value
    system_path = f"Systems/{selected_system}"

    if os.path.exists(system_path):
        # Delete the directory and its contents
        os.rmdir(system_path)
        ui.notify(f"The directory '{selected_system}' has been deleted.", type='positive')
    else:
        ui.notify(f"The directory '{selected_system}' does not exist.", type='warning')

def open_popUp_deleteSystems():
    
    #global popUp_deleteSystems
    popUp_deleteSystems.open() 


with popUp_deleteSystems, ui.card():
            ui.label("Bitte System auswählen")
            systems = [f.name for f in os.scandir("Systems") if f.is_dir()]
        
            dropdown_systems = ui.select(
                            options=systems,
                            label='Systems Archive'
                        ).classes('w-full')
            ui.button("Delete", on_click= lambda: (delete_system(),popUp_deleteSystems.close()))


# --------------------------           
# Delete System End 
# --------------------------     



async def newSystem():
    global textbox_setup

    if textbox_setup.value is not None:
        setup_name = textbox_setup.value
        system_path = f"Systems/{setup_name}"

        if not setup_name:
            ui.notify("Please enter a valid setup name.", type='warning')
            return
        if os.path.exists(system_path):
            # Trigger notify if the directory already exists
            ui.notify(f"The directory '{setup_name}' already exists.", type='warning')
        else:
            # Create the directory if it does not exist
            os.makedirs(system_path, exist_ok=True)
            
            ui.notify(f"The directory '{setup_name}' has been created.", type='ongoing')


# --------------------------
# Add Device
# --------------------------
async def load_EIDs_name():
    url = "https://library.smartgridready.ch/prod?release=Published"
    global dropdown_identifier


    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    ui.notify(f'HTTP Error: {response.status}', type='warning')
                    return

                raw_bytes = await response.read()
                data = json.loads(raw_bytes.decode('utf-8'))

                
                identifiers = [item['identifier'] for item in data]
                
                
                if dropdown_identifier:
                    dropdown_identifier.delete()

                dropdown_identifier = ui.select(
                    options=identifiers,
                    label='Published Identifiers'
                ).classes('w-full')

    except Exception as e:
        ui.notify(f'Error: {e}', type='negative')


async def download_EID(EID_name: str):

    if dropdown_identifier and dropdown_identifier.value:
        EID_name = dropdown_identifier.value

    url = f"https://library.smartgridready.ch/{EID_name}?viewDevice"
    
    async with aiohttp.request('GET', url) as response:
        status_code = response.status
        xml_file = await response.read()  # response is xml in bytes

    if status_code == 200:
        try:
            # save file
            with open(f"xml_files/{EID_name}", "wb") as f:  # write it as bytes
                f.write(xml_file)
                
            
        except EnvironmentError:
            ui.notify(f'Error: Unable to save file', type='negative')
            return
    else:
        print(f"Download of SGr File failed.")
        

def handle_change(e, g, k):
    print("pressed checkbox")
    global selected_datapoints
    pair = (g, k)
    if e.value and pair not in selected_datapoints:
        selected_datapoints.append(pair)
    elif not e.value and pair in selected_datapoints:
        selected_datapoints.remove(pair)
    print(f"Selected Datapoints: {selected_datapoints}")

async def getParams():
    global params
    global device
    global params_datatype
    global dropdown_identifier
    global selected_datapoints 
    eid_path = 'xml_files/' + dropdown_identifier.value

    print(f"Selected EID: {dropdown_identifier.value}")
    print(f"Selected EID path: {eid_path}")
    #eid_path = 'xml_files/SGr_04_0015_xxxx_StiebelEltron_HeatPump_V1.0.0.xml'

    device = DeviceBuilder().eid_path(eid_path).build()
    
    text = device.configuration_parameters
    
    params = {param.name: '' for param in text}
    
    params_datatype = {
    param.name: next(
        (attr for attr in dir(param.type)
         if not attr.startswith('_') and getattr(param.type, attr) not in (None, "EmptyType()")),
        None
    )
    for param in text
    }

    #params_datatype = {param.name: next((k for k, v in param.type.items() if v is not None), None) for param in text}
    
    print(params_datatype)
    ui.label('Enter Parameter Values').classes('text-xl font-bold mb-4')

    global input_fields

    # Create input fields for each parameter
    for key in params:
        with ui.row():
            ui.label(key).classes('w-28')  
            input_fields[key] = ui.input(placeholder= params_datatype[key])


    device_describtion = device.describe()
    data_dict = device_describtion[1]
    checkbox_items = [
        (group, key)
        for group, values in data_dict.items()
        for key in values.keys()
    ]

    #selected_datapoints = []

    ui.label('Choose Datapoints:').classes('text-xl font-bold mt-6 mb-2')
    for group, key in checkbox_items:
        label = f'{group} : {key}'
        cb = ui.checkbox(label)
        checkbox_dict[(group, key)] = cb
        #cb.on('change', lambda e, g=group, k=key: handle_change(e, g, k))
        

async def addDevice():
    #parameter
    global input_fields
    global params
    global device
    global params_datatype
    global selected_datapoints
    yaml_file_path = 'yaml/config.yaml'

    #checked_datapoints = [dict(pair) for pair, cb in checkbox_dict.items() if cb.value]
    checked_datapoints = [
        {'fp': pair[0], 'dp': pair[1]}
        for pair, cb in checkbox_dict.items() if cb.value
    ]
    print(f"Diese Checkboxen sind ausgewählt: {checked_datapoints}")
    print(type(checked_datapoints))
    expected_data_types = {

        'int16': int,
        'int32': int,
        'int': int,
        'float': float,
        'bool': bool,
        'string': str,
    }

    
       # Validate and convert input values
    
    for key, input_field in input_fields.items():
        value = input_field.value  # Get the user input
        expected_type = params_datatype[key]  # Get the expected data type 

        # Validate and convert the value
        try:
            if expected_type in expected_data_types:
                # Convert the value to the expected type
                params[key] = expected_data_types[expected_type](value)
            else:
                raise ValueError(f"Unsupported data type: {expected_type}")
        except ValueError as e:
            ui.notify(f"Invalid value for {key}: {e}", type='negative')
            print(f"Error: Invalid value for {key}: {e}")
            return  # Stop saving if validation fails


    ui.notify('Values validated and saved!')

    new_device = {
            'name': textbox_device.value,
            'type': False, #device.device_information.device_category,
            'smartGridreadyEID': device.device_information.name,
            'simulationModel': None,
            'isLogging': False,
            'param': params,
            'datapoints': checked_datapoints
        }
    try:
        # Read the existing YAML file (if it exists)
        with open(yaml_file_path, 'r') as file:
            existing_data = yaml.safe_load(file)  # Load existing data or initialize as empty

        
        print(type(existing_data))
        print(new_device)
        existing_data["devices"].append(new_device)  # Append new device to the list of devices
        # Ensure the existing data is a list
        
        # Update the existing data with the new parameters
        

        # Write the updated data back to the YAML file
        with open('yaml/config.yaml', 'w') as file:
            yaml.dump(existing_data, file, sort_keys=False, default_flow_style=False)

        ui.notify('Configuration saved to YAML file!')
        print(f"Updated YAML file: {yaml_file_path}")

    except Exception as e:
        ui.notify(f'Error saving to YAML: {e}', type='negative')
        print(f"Error: {e}")




async def get_device_list_dropdown(): 
    global dropdown_devices

    device_list = get_device_list()
    if dropdown_devices:
        dropdown_devices.delete()

    dropdown_devices = ui.select(
        options=device_list,
        label='Device List'
    ).classes('w-full')

    # Set the default value to the first device in the list
    if device_list:
        dropdown_devices.value = device_list[0]    


async def delete_device_by_name():
    yaml_file_path = 'yaml/config.yaml'
    global dropdown_devices

    if dropdown_devices and dropdown_devices.value:
        device_name = dropdown_devices.value

    try:
        # Load existing YAML data
        with open(yaml_file_path, 'r') as file:
            data = yaml.safe_load(file) or {}

        devices = data.get('devices', [])
        # Filter out devices with the given name
        new_devices = [device for device in devices if device.get('name') != device_name]
        data['devices'] = new_devices

        # Save the updated YAML data
        with open(yaml_file_path, 'w') as file:
            yaml.dump(data, file, sort_keys=False, default_flow_style=False)

        print(f"Device(s) with name '{device_name}' deleted.")
    except Exception as e:
        print(f"Error deleting device: {e}")
    await get_device_list_dropdown()

    
def get_device_list():
    yaml_file_path = 'yaml/config.yaml'
    try:
        with open(yaml_file_path, 'r') as file:
            data = yaml.safe_load(file)
            devices = data.get('devices', [])
            return [device.get('name') for device in devices]  # Return a list of device names
    except FileNotFoundError:
        print(f"File not found: {yaml_file_path}")
        return []
    except yaml.YAMLError as e:
        print(f"Error reading YAML file: {e}")
        return []
