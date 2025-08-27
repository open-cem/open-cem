import datetime
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
from influxdb import InfluxDBClient
import yaml
import paho.mqtt.client as mqtt


# Load configuration from YAML file
with open("yaml/OpenCEM_settings.yaml", 'r') as file:
    config = yaml.safe_load(file)

mqtt_address = config.get('mqtt_address')
influxDB_address = config.get('influxDB_address', 'localhost')


# --------------------------
# Global Variables
# --------------------------
opencem_task = None
plot_timer = None
live_plots_active = False
plot_figures = {}
config_container = None




input_fields = {}
params = None
dropdown_identifier = None
dropdown_local_EIDs = None
dropdown_devices = None
params_datatype = None
device = None


popUp_deleteSystems = ui.dialog().props('persistent')
system_config = ui.dialog().props('persistent')

pagination_card = ui.card().classes('w-full')
with pagination_card:
        ui.label("System Configuration").classes('text-lg font-bold')

selected_datapoints = [] 
checkbox_dict = {} 





# MQTT callback
def on_message(client, userdata, msg):
    value = msg.payload.decode()
    # Update the textbox in the main thread
    #ui.run_later(lambda: latest_value_box.set_value(value))
    #latest_value_box.value = value

async def start_mqtt():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(mqtt_address, 1883)  # Use your broker address
    client.subscribe('openCEM/value')
    client.loop_start()  # Start MQTT loop in background





def start_OpenCEM():
    global opencem_task
    
    if opencem_task and not opencem_task.done():
        ui.notify('OpenCEM is already running', type='warning')
        return
    
    opencem_task = asyncio.create_task(OpenCEM_main())
    ui.notify('OpenCEM started', type='positive')

def stop_OpenCEM():
    global opencem_task
    
    if opencem_task and not opencem_task.done():
        opencem_task.cancel()
        ui.notify('OpenCEM stopped', type='info')
    else:
        ui.notify('OpenCEM is not running', type='warning')  
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

#---------------------------
# configuration
#---------------------------

def show_overview(data):
    ui.label(f"Installation Name: {data.get('installationName', '')}").classes('text-xl font-bold')
    ui.label(f"Creation Timestamp: {data.get('creationTimestamp', '')}").classes('mb-2')
    ui.label("Devices:").classes('text-lg font-bold mt-2')
    eid_list = [device.get('smartGridreadyEID', '') for device in data.get('devices', [])]
    ui.label(eid_list)

def show_device_page(device):
    with ui.card():
        ui.label(f"Device Name: {device.get('name', '')}").classes('text-lg font-bold')
        ui.label(f"Type: {device.get('type', '')}")
        ui.label(f"EID: {device.get('smartGridreadyEID', '')}")
        ui.label(f"Logging: {device.get('isLogging', '')}")
        ui.label(f"Simulation Model: {device.get('simulationModel', '')}")
        ui.label("Parameters:")
        for k, v in device.get('param', {}).items():
            ui.label(f"{k}: {v}")
        ui.label("Datapoints:")
        for dp in device.get('datapoints', []):
            ui.label(f"fp: {dp.get('fp', '')}, dp: {dp.get('dp', '')}")

async def dynamic_pagination(device_card):
    """Create dynamic pagination for the YAML data."""
    # Clear the container before creating new pagination
    pagination_card.clear()
    
    # 1. Read the YAML file
    yaml_file_path = 'yaml/config.yaml'
    with open(yaml_file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    # 2. Prepare pages
    pages = []

    # Add the overview page
    def overview_page():
        show_overview(data)
    pages.append(overview_page)

    # Add a page for each device
    for device in data.get('devices', []):
        def make_device_page(dev=device):  # Use default argument to freeze the value
            show_device_page(dev)
        pages.append(make_device_page)

    # 3. Render pages using the container

    

    def render_page(page_index: int):
        pagination_card.clear()  # Clear the container before rendering the new page
        with pagination_card:
                    # Add pagination at the top
            ui.pagination(
                min=0,  # Minimum page index
                max=len(pages) - 1,  # Maximum page index
                value=page_index,  # Current page index
                direction_links=True,  # Show first/last page links
                on_change=lambda e: render_page(e.value)  # Callback to render the selected page
            )
                    # Render the selected page content
            pages[page_index]()

            # Render the first page initially
    render_page(0)

def clear_config_box():
    pagination_card.clear()
    
async def newSystem():

   
    
    with ui.card() as box_new_system:
        textbox_system = ui.input(label='Enter System Name').classes('w-full')
        def create_system_action():
            system_name = textbox_system.value
            system_path = f"Systems/{system_name}"
            if not system_name:
                ui.notify("Please enter a valid system name.", type='warning')
                return
            if os.path.exists(system_path):
                ui.notify(f"The directory '{system_name}' already exists.", type='warning')
            else:
                os.makedirs(system_path, exist_ok=True)
                ui.notify(f"The directory '{system_name}' has been created.", type='positive')
            box_new_system.delete()  
        ui.button('Create System', on_click=create_system_action).classes('mt-2')
    """
    global textbox_system

    if textbox_system.value is not None:
        system_name = textbox_system.value
        system_path = f"Systems/{system_name}"

        if not system_name:
            ui.notify("Please enter a valid system name.", type='warning')
            return
        if os.path.exists(system_path):
            # Trigger notify if the directory already exists
            ui.notify(f"The directory '{system_name}' already exists.", type='warning')
        else:
            # Create the directory if it does not exist
            os.makedirs(system_path, exist_ok=True)

            ui.notify(f"The directory '{system_name}' has been created.", type='ongoing')
    """

# --------------------------
# Add Device
# --------------------------

async def load_local_EIDs(config):
    global dropdown_local_EIDs
    global config_container
    config_container = config
    config_container.clear()
    # Get the list of XML files in the xml_files directory
    xml_files = [f for f in os.listdir('xml_files') if f.endswith('.xml')]
    
    if dropdown_local_EIDs:
        dropdown_local_EIDs.delete()

    with config_container:
        dropdown_local_EIDs = ui.select(
            options=xml_files,
            label='Local EIDs'
        ).classes('w-full')


async def load_online_EIDs():
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
                    label='Online EIDs'
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
        

async def getParams():
    global params
    global device
    global params_datatype
    global dropdown_identifier
    global dropdown_local_EIDs
    global selected_datapoints 
    eid_path = 'xml_files/' + dropdown_local_EIDs.value

    print(f"Selected EID: {dropdown_local_EIDs.value}")
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
    global dropdown_local_EIDs
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
            'name': device.device_information.name,
            'type': False, #device.device_information.device_category,
            'smartGridreadyEID': f"xml_files/ {dropdown_local_EIDs.value}",
            'EID_param': None,
            'nativeEID': None,
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


#----------------------------
#Plot functions
#----------------------------

def load_available_devices(device_select):
    """Load devices that have data in InfluxDB"""
    try:
        client = InfluxDBClient('localhost', 8086)
        databases = client.get_list_database()
        
        device_names = []
        for db in databases:
            db_name = db['name']
            if db_name.startswith('device_'):
                device_name = db_name.replace('device_', '')
                device_names.append(device_name)
        
        client.close()
        device_select.options = device_names
        if device_names:
            device_select.value = device_names[0]
        
        ui.notify(f'Found {len(device_names)} devices with data', type='positive')
        
    except Exception as e:
        ui.notify(f'Error loading devices: {e}', type='negative')

def create_plots(hours_input, plots_container):
    """Create plots once, then only update data"""
    global plot_figures
    
    if live_plots_active:
        ui.notify('Already running', type='warning')
        return

    try:
        client = InfluxDBClient(influxDB_address, 8086)
        databases = client.get_list_database()
        device_dbs = [db['name'] for db in databases if db['name'].startswith('device_')]
        
        plots_container.clear()
        plot_figures.clear()
        
        if not device_dbs:
            with plots_container:
                ui.label('No devices found').classes('text-center text-red-500')
            return
        
        hours = hours_input.value or 1
        colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink']
        
        with plots_container:
            ui.label(f'Live Plots (Last {int(hours)}h)').classes('text-xl font-bold mb-4')
            
            for db_name in device_dbs:
                device_name = db_name.replace('device_', '')
                client.switch_database(db_name)
                
                # Get measurements
                measurements_query = client.query('SHOW MEASUREMENTS')
                measurements = [list(point.values())[0] for point in measurements_query.get_points()]
                
                if measurements:
                    # Create figure once
                    fig = go.Figure()
                    
                    for i, measurement in enumerate(measurements):
                        try:
                            # FIX: Correct InfluxDB time syntax
                            query = f'SELECT * FROM "{measurement}" WHERE time > now() - {int(hours)}h ORDER BY time ASC'
                            result = client.query(query)
                            points = list(result.get_points())
                            
                            if points:
                                times = [p['time'] for p in points]
                                values = [p['value'] for p in points]
                                unit = points[0].get('unit', '')
                                
                                trace_name = measurement.replace('_', ' - ')
                                if unit:
                                    trace_name += f' [{unit}]'
                                
                                fig.add_trace(go.Scatter(
                                    x=times,
                                    y=values,
                                    mode='lines+markers',
                                    name=trace_name,
                                    line=dict(width=2, color=colors[i % len(colors)]),
                                    marker=dict(size=3)
                                ))
                        except Exception as e:
                            print(f"Error querying measurement {measurement}: {e}")
                            continue
                    
                    if fig.data:
                        fig.update_layout(
                            title=f'Device: {device_name}',
                            xaxis_title='Time',
                            yaxis_title='Values',
                            height=400,
                            hovermode='x unified'
                        )
                        
                        # Create plot widget and store reference
                        with ui.card().classes('w-full mb-4'):
                            ui.label(f'📊 {device_name}').classes('text-lg font-bold')
                            plot_widget = ui.plotly(fig).classes('w-full')
                            
                            # Store references for updates
                            plot_figures[device_name] = {
                                'figure': fig,
                                'widget': plot_widget,
                                'measurements': measurements,
                                'db_name': db_name
                            }
        
        client.close()
        ui.notify('Plots created for live updates', type='positive')
        
    except Exception as e:
        print(f"Error creating optimized plots: {e}")
        ui.notify(f'Error creating plots: {e}', type='negative')

def update_live_plots_data(hours_input):
    """Update only the data in existing plots"""
    global plot_figures
    
    if not plot_figures:
        return
    
    try:
        client = InfluxDBClient(influxDB_address, 8086)
        hours = hours_input.value or 1
        
        for device_name, plot_data in plot_figures.items():
            try:
                client.switch_database(plot_data['db_name'])
                
                # Update each trace
                for i, measurement in enumerate(plot_data['measurements']):
                    try:
                        # FIX: Correct time syntax
                        query = f'SELECT * FROM "{measurement}" WHERE time > now() - {int(hours)}h ORDER BY time ASC'
                        result = client.query(query)
                        points = list(result.get_points())
                        
                        if points:
                            new_times = [p['time'] for p in points]
                            new_values = [p['value'] for p in points]
                            
                            # Update trace data
                            if i < len(plot_data['figure'].data):
                                plot_data['figure'].data[i].x = new_times
                                plot_data['figure'].data[i].y = new_values
                    except Exception as e:
                        print(f"Error updating measurement {measurement}: {e}")
                        continue
                
                # Refresh the plot widget
                plot_data['widget'].update()
                
            except Exception as e:
                print(f"Error updating device {device_name}: {e}")
                continue
        
        client.close()
        print(f"📊 Plot data updated at {datetime.now().strftime('%H:%M:%S')}")
        
    except Exception as e:
        print(f"Error updating plot data: {e}")

# Modified live plot functions
def start_live_plots(hours_input, plots_container):
    """Start live plot updates with data-only updates"""
    global plot_timer, live_plots_active
    
    if live_plots_active:
        ui.notify('Already running', type='warning')
        return
    
    # Create plots once
    create_plots(hours_input, plots_container)
    
    # Start timer for data updates only
    live_plots_active = True
    plot_timer = ui.timer(1.0, lambda: update_live_plots_data(hours_input))
    
    ui.notify('Live plots started (1s data updates)', type='positive')

def stop_live_plots():
    """Stop live plot updates"""
    global plot_timer, live_plots_active
    
    if plot_timer:
        plot_timer.cancel()
        plot_timer = None
    
    live_plots_active = False
    ui.notify('Live plots stopped', type='info')
    


def show_device_info(device_select, device_info_container):



    """Show available measurements for selected device"""
    if not device_select.value:
        return
    
    try:
        device_name = device_select.value
        db_name = f"device_{device_name}"

        client = InfluxDBClient(influxDB_address, 8086, database=db_name)
        result = client.query('SHOW MEASUREMENTS')
        measurements = [list(point.values())[0] for point in result.get_points()]
        client.close()
        
        device_info_container.clear()
        with device_info_container:
            ui.label(f'Available datapoints for {device_name}:').classes('font-bold')
            for measurement in measurements:
                # Split fp_dp back to readable format
                parts = measurement.split('_', 1)
                if len(parts) == 2:
                    fp, dp = parts
                    ui.label(f'• {fp} - {dp}').classes('ml-4 text-sm')
                else:
                    ui.label(f'• {measurement}').classes('ml-4 text-sm')
    
    except Exception as e:
        with device_info_container:
            ui.label(f'Error loading device info: {e}').classes('text-red-500')





async def download_yaml_from_qr(url: str, qr_code_container) -> list:
    qr_code_container.clear()
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                ui.notify(f"Download error: {response.status}", type='negative')
                return []
            raw_bytes = await response.read()
            devices = yaml.safe_load(raw_bytes.decode('utf-8'))
            print(type(devices))

            # Extrahiere und zeige alle Gerätenamen in NiceGUI
            device_list = devices.get('devices', [])
            with qr_code_container:
                with ui.card():
                    ui.label('Gefundene Geräte:').classes('text-lg font-bold')
                    for device in device_list:
                        name = device.get('name', '')
                        xml_name = device.get('smartGridreadyEID', '')
                        ui.label(f'• {name}  |  EID: {xml_name}').classes('ml-4')
            return device_list


async def show_datapoint_selection(devices, qr_code_container):
    """Zeigt für jedes Gerät die Datenpunkte als Checkboxen an und speichert die Auswahl gesammelt."""
    qr_code_container.clear()
    device_checkbox_mapping = {}  # device_info -> checkbox_dict

    with qr_code_container:
        for device_info in devices:
            eid_file = device_info.get('smartGridreadyEID', '')
            eid_path = os.path.join('xml_files', eid_file) if eid_file else ''
            if not eid_file or not os.path.exists(eid_path):
                ui.notify(
                    f"EID-Datei '{eid_file}' für Gerät '{device_info.get('name', '')}' nicht gefunden! "
                    "Bitte zuerst das EID herunterladen.",
                    type='negative'
                )
                return
            try:
                dev = DeviceBuilder().eid_path(eid_path).build()
                description = dev.describe()
                data_dict = description[1]
            except Exception as e:
                ui.notify(f"Fehler beim Laden der EID für {device_info.get('name', '')}: {e}", type='negative')
                continue

            checkbox_dict = {}
            ui.label(f'Datenpunkte für Gerät: {device_info.get("name", "")}').classes('text-xl font-bold mt-4')
            for group, values in data_dict.items():
                for key in values.keys():
                    cb = ui.checkbox(f'{group}: {key}')
                    checkbox_dict[(group, key)] = cb

            device_checkbox_mapping[device_info.get('name', '')] = (device_info, checkbox_dict)

        # EIN Button für alle Geräte!
        def save_all_selections():
            yaml_file_path = 'yaml/testing.yaml'
            try:
                # Lade bestehende Daten, falls vorhanden
                if os.path.exists(yaml_file_path):
                    with open(yaml_file_path, 'r') as file:
                        existing_data = yaml.safe_load(file) or {}
                else:
                    existing_data = {}

                device_list = existing_data.get('devices', [])

                # Für jedes Gerät die Auswahl speichern
                for name, (device_info, checkbox_dict) in device_checkbox_mapping.items():
                    selected = [
                        {'fp': pair[0], 'dp': pair[1]}
                        for pair, cb in checkbox_dict.items() if cb.value
                    ]
                    device_info['datapoints'] = selected

                    # Prüfe, ob das Gerät schon existiert
                    eid = device_info.get('smartGridreadyEID', '')
                    found = False
                    for idx, dev in enumerate(device_list):
                        if dev.get('smartGridreadyEID', '') == eid:
                            device_list[idx] = device_info
                            found = True
                            break
                    if not found:
                        device_list.append(device_info)

                existing_data['devices'] = device_list

                # Schreibe die aktualisierte Geräteliste zurück
                with open(yaml_file_path, 'w') as file:
                    yaml.dump(existing_data, file, sort_keys=False, default_flow_style=False)
                ui.notify('Alle Geräte wurden in testing.yaml gespeichert!', type='positive')
            except Exception as e:
                ui.notify(f'Fehler beim Speichern in testing.yaml: {e}', type='negative')

        ui.button('Alle Datenpunkte übernehmen', on_click=save_all_selections).classes('mt-4')
        #print("selected_devices" + selected_devices)
    #return selected_devices

async def yaml_workflow(qr_code_container):
    url = "https://fl-17-166.zhdk.cloud.switch.ch/api/config/matt-test?secret=mirdochwurscht"
    devices = await download_yaml_from_qr(url, qr_code_container)
    if devices:
        await show_datapoint_selection(devices, qr_code_container)

