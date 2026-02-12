import json
import aiohttp
from nicegui import ui
from sgr_commhandler.device_builder import DeviceBuilder
import yaml
import os
import plotly.graph_objects as go
import asyncio
from OpenCEM_main import main as OpenCEM_main
from influxdb import InfluxDBClient
import paho.mqtt.client as mqtt
import config_helper


# Load configuration from YAML file
config_path = os.environ.get('CONFIG_PATH', 'System_Settings')
xml_path = os.environ.get('XML_PATH', 'xml_files')
try:
    with open(os.path.join(config_path, "OpenCEM_settings.yaml"), "r") as file:
        config = yaml.safe_load(file)
except Exception:
    config = {}

# Override configuration with environment variables
mqtt_address = config_helper.get_setting('MQTT_HOST', 'mqtt_address', settings=config, default_value='localhost')
mqtt_port = config_helper.get_setting('MQTT_PORT', 'mqtt_port', settings=config, default_value=1883)
influxDB_address = config_helper.get_setting('INFLUX_HOST', 'influxDB_address', settings=config, default_value='localhost')
influxDB_port = config_helper.get_setting('INFLUX_PORT', 'influxDB_port', settings=config, default_value=8086)
influxDB_user = config_helper.get_setting('INFLUX_USER', 'influxDB_user', settings=config, default_value='')
influxDB_password = config_helper.get_setting('INFLUX_PASSWORD', 'influxDB_password', settings=config, default_value='')


# --------------------------
# Global Variables
# --------------------------
opencem_task = None
plot_timer = None
live_plots_active = False
plot_figures = {}
LocalEID_container = None
mqtt_container = None


input_fields = {}
params = None
dropdown_identifier = None
dropdown_local_EIDs = None
dropdown_devices = None
params_datatype = None
device = None


selected_datapoints = []
checkbox_dict = {}


def on_connect(client, userdata, flags, rc):
    """
    Callback for when the MQTT client connects to the broker.


    """
    if rc == 0:
        # Subscribe to your topic after a successful connection
        client.subscribe("openCEM/value")
        print("Connected to MQTT broker and subscribed to topic.")
    else:
        print(f"Failed to connect to MQTT broker, return code {rc}")


def on_message(client, userdata, msg):
    global mqtt_container
    mqtt_message = msg.payload.decode()
    if mqtt_container is not None:
        mqtt_container.clear()
        with mqtt_container:
            ui.label(f"Received data: {mqtt_message}").classes("text-sm")


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(mqtt_address, mqtt_port)
client.loop_start()


def start_OpenCEM(latest_value_container):
    global opencem_task
    global mqtt_container
    mqtt_container = latest_value_container
    if opencem_task and not opencem_task.done():
        ui.notify("OpenCEM is already running", type="warning")
        return

    opencem_task = asyncio.create_task(OpenCEM_main())
    ui.notify("OpenCEM started", type="positive")


def stop_OpenCEM():
    global opencem_task

    if opencem_task and not opencem_task.done():
        opencem_task.cancel()
        ui.notify("OpenCEM stopped", type="info")
    else:
        ui.notify("OpenCEM is not running", type="warning")


# ---------------------------
# configuration
# ---------------------------


def show_overview(data):
    ui.label(f"Installation Name: {data.get('installationName', '')}").classes(
        "text-xl font-bold"
    )
    ui.label(f"Creation Timestamp: {data.get('creationTimestamp', '')}").classes("mb-2")
    ui.label("Devices:").classes("text-lg font-bold mt-2")
    eid_list = [
        device.get("smartGridreadyEID", "") for device in data.get("devices", [])
    ]
    ui.label(eid_list)


def show_device_page(device):
    with ui.card():
        ui.label(f"Device Name: {device.get('name', '')}").classes("text-lg font-bold")
        ui.label(f"Type: {device.get('type', '')}")
        ui.label(f"EID: {device.get('smartGridreadyEID', '')}")
        ui.label(f"Logging: {device.get('isLogging', '')}")
        ui.label(f"Simulation Model: {device.get('simulationModel', '')}")
        ui.label("Parameters:")
        for k, v in device.get("param", {}).items():
            ui.label(f"{k}: {v}")
        ui.label("Datapoints:")
        for dp in device.get("datapoints", []):
            ui.label(f"fp: {dp.get('fp', '')}, dp: {dp.get('dp', '')}")


async def dynamic_pagination(device_card, config_container):
    """Create dynamic pagination for the YAML data."""
    # Clear the container before creating new pagination
    with config_container:

        config_container.clear()

        yaml_file_path = os.path.join(config_path, "config.yaml")
        with open(yaml_file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Prepare pages
        pages = []

        # Add the overview page
        def overview_page():
            show_overview(data)

        pages.append(overview_page)

        # Add a page for each device
        for device in data.get("devices", []):

            def make_device_page(dev=device):
                show_device_page(dev)

            pages.append(make_device_page)

        def render_page(page_index: int):
            config_container.clear()
            with config_container:

                ui.pagination(
                    min=0,  # Minimum page index
                    max=len(pages) - 1,  # Maximum page index
                    value=page_index,  # Current page index
                    direction_links=True,  # Show first/last page links
                    on_change=lambda e: render_page(
                        e.value
                    ),  # Callback to render the selected page
                )
                # Render the selected page content
                pages[page_index]()

                # Render the first page initially

        render_page(0)


# --------------------------
# Add Device
# --------------------------


async def load_local_EIDs(LocalEID, param):
    """
    Load available local EID files and display them in a dropdown.

    Args:
        LocalEID: The UI container where the dropdown will be placed.
        param: The parameter container to be cleared.
    """
    global xml_path
    global dropdown_local_EIDs
    global LocalEID_container
    param_container = param
    LocalEID_container = LocalEID
    param_container.clear()

    # Get the list of XML files in the xml_files directory
    xml_files = [f for f in os.listdir(xml_path) if f.endswith(".xml")]

    # Remove previous dropdown if it exists
    if dropdown_local_EIDs:
        dropdown_local_EIDs.delete()

    # Show dropdown with available EIDs
    with LocalEID_container:
        dropdown_local_EIDs = ui.select(options=xml_files, label="Local EIDs").classes(
            "w-full"
        )


async def load_online_EIDs():
    """
    Load available EIDs from the online SmartGridReady library and display them in a dropdown.
    """

    url = "https://library.smartgridready.ch/prod?release=Published"
    global dropdown_identifier

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    ui.notify(f"HTTP Error: {response.status}", type="warning")
                    return

                raw_bytes = await response.read()
                data = json.loads(raw_bytes.decode("utf-8"))

                # Extract identifiers for dropdown
                identifiers = [item["identifier"] for item in data]

                # Remove previous dropdown if it exists
                if dropdown_identifier:
                    dropdown_identifier.delete()

                dropdown_identifier = ui.select(
                    options=identifiers, label="Online EIDs"
                ).classes("w-full")

    except Exception as e:
        ui.notify(f"Error: {e}", type="negative")


async def download_EID(EID_name: str):
    """
    Download the selected EID file from the library and save it locally.

    Args:
        EID_name (str): The identifier of the EID to download.
    """
    global xml_path

    # use the selected value from the dropdown
    if dropdown_identifier and dropdown_identifier.value:
        EID_name = dropdown_identifier.value

    url = f"https://library.smartgridready.ch/{EID_name}?viewDevice"

    async with aiohttp.request("GET", url) as response:
        status_code = response.status
        xml_file = await response.read()

    if status_code == 200:
        try:

            with open(os.path.join(xml_path, EID_name), "wb") as f:  # write it as bytes
                f.write(xml_file)

        except EnvironmentError:
            ui.notify("Error: Unable to save file", type="negative")
            return
    else:
        print("Download of SGr File failed.")


async def getParams(param_container):
    """
    Load parameters and datapoints from the selected EID and create input fields and checkboxes.

    Args:
        param_container: The UI container where parameter fields and datapoint checkboxes will be placed.
    """
    global xml_path
    global params
    global device
    global params_datatype
    global dropdown_identifier
    global dropdown_local_EIDs
    global selected_datapoints

    param_container.clear()
    eid_path = os.path.join(xml_path, dropdown_local_EIDs.value)

    # Build device from EID
    device = DeviceBuilder().eid_path(eid_path).build()
    text = device.configuration_parameters

    # Prepare parameter names and types
    params = {param.name: "" for param in text}
    params_datatype = {
        param.name: next(
            (
                attr
                for attr in dir(param.type)
                if not attr.startswith("_")
                and getattr(param.type, attr) not in (None, "EmptyType()")
            ),
            None,
        )
        for param in text
    }

    with param_container:
        ui.label("Enter Parameter Values").classes("text-xl font-bold mb-4")

        global input_fields

        # Create input fields for each parameter
        for key in params:
            with ui.row():
                ui.label(key).classes("w-28")
                input_fields[key] = ui.input(placeholder=params_datatype[key])

        # Get datapoints from device description
        device_describtion = device.describe()
        data_dict = device_describtion[1]
        checkbox_items = [
            (group, key) for group, values in data_dict.items() for key in values.keys()
        ]

        # Create checkboxes for datapoints
        ui.label("Choose Datapoints:").classes("text-xl font-bold mt-6 mb-2")
        for group, key in checkbox_items:
            label = f"{group} : {key}"
            cb = ui.checkbox(label)
            checkbox_dict[(group, key)] = cb


async def addDevice(param_container):
    """
    Validate parameter input, collect selected datapoints, and add the device to the YAML configuration.

    Args:
        param_container: The UI container to clear after saving.
    """

    global config_path
    global input_fields
    global params
    global device
    global params_datatype
    global selected_datapoints
    global dropdown_local_EIDs

    yaml_file_path = os.path.join(config_path, "config.yaml")

    # Collect checked datapoints
    checked_datapoints = [
        {"fp": pair[0], "dp": pair[1]} for pair, cb in checkbox_dict.items() if cb.value
    ]

    # expected data types for validation
    expected_data_types = {
        "int16": int,
        "int32": int,
        "int": int,
        "float": float,
        "bool": bool,
        "string": str,
    }

    # Validate and convert input values
    for key, input_field in input_fields.items():
        value = input_field.value
        expected_type = params_datatype[key]

        # Validate and convert the value
        try:
            if expected_type in expected_data_types:
                # Convert the value to the expected type
                params[key] = expected_data_types[expected_type](value)
            else:
                raise ValueError(f"Unsupported data type: {expected_type}")
        except ValueError as e:
            ui.notify(f"Invalid value for {key}: {e}", type="negative")
            return

    ui.notify("Values validated and saved!")

    # Prepare new device entry
    new_device = {
        "name": device.device_information.name,
        "smartGridreadyEID": dropdown_local_EIDs.value,
        "parameters": params,
        "datapoints": checked_datapoints,
        "type": "DEVICE",
    }

    try:
        # Read the existing YAML file
        with open(yaml_file_path, "r") as file:
            existing_data = yaml.safe_load(file) or {}

        device_list = existing_data.get("devices", [])

        # Check if device already exists
        eid = new_device.get("smartGridreadyEID", "")
        found = False
        for idx, dev in enumerate(device_list):
            if dev.get("smartGridreadyEID", "") == eid:
                device_list[idx] = new_device  # update existing
                found = True
                break
        if not found:
            device_list.append(new_device)  # add new

        existing_data["devices"] = device_list

        # Write the updated data back to the YAML file
        with open(os.path.join(config_path, "config.yaml"), "w") as file:
            yaml.dump(existing_data, file, sort_keys=False, default_flow_style=False)
            ui.notify("Devices are safed in configuration file!", type="positive")

        ui.notify("Configuration saved to YAML file!")

        param_container.clear()
    except Exception as e:
        ui.notify(f"Error saving to YAML: {e}", type="negative")
        print(f"Error: {e}")


async def get_device_list_dropdown():
    """
    Create a dropdown UI element with the list of device from the YAML configuration.

    """
    global dropdown_devices

    device_list = get_device_list()

    # Remove previous dropdown if it exists
    if dropdown_devices:
        dropdown_devices.delete()

    # Create new dropdown with device names
    dropdown_devices = ui.select(options=device_list, label="Device List").classes(
        "w-full"
    )

    # Set the default value to the first device in the list
    if device_list:
        dropdown_devices.value = device_list[0]


async def delete_device_by_name():
    """
    Delete the selected device from the YAML configuration file.

    """
    global config_path
    global dropdown_devices

    yaml_file_path = os.path.join(config_path, "config.yaml")

    # Get the selected device name from the dropdown
    if dropdown_devices and dropdown_devices.value:
        device_name = dropdown_devices.value

    try:
        # Load existing YAML data
        with open(yaml_file_path, "r") as file:
            data = yaml.safe_load(file) or {}

        devices = data.get("devices", [])
        # Filter out devices with the given name
        new_devices = [
            device for device in devices if device.get("name") != device_name
        ]
        data["devices"] = new_devices

        # Save the updated YAML data
        with open(yaml_file_path, "w") as file:
            yaml.dump(data, file, sort_keys=False, default_flow_style=False)

        print(f"Device with name '{device_name}' deleted.")
    except Exception as e:
        print(f"Error deleting device: {e}")
    await get_device_list_dropdown()


def get_device_list():
    """
    Read the YAML configuration and return a list of device names.

    Returns:
        list: List of device names (str) from the YAML config.
    """
    global config_path
    yaml_file_path = os.path.join(config_path, "config.yaml")
    try:
        with open(yaml_file_path, "r") as file:
            data = yaml.safe_load(file)
            devices = data.get("devices", [])
            return [
                device.get("name") for device in devices
            ]  # Return a list of device names
    except FileNotFoundError:
        print(f"File not found: {yaml_file_path}")
        return []
    except yaml.YAMLError as e:
        print(f"Error reading YAML file: {e}")
        return []


# ----------------------------
# Plot functions
# ----------------------------


def load_available_devices(device_select):
    """Load devices that have data in InfluxDB"""
    global influxDB_address, influxDB_port, influxDB_user, influxDB_password
    try:
        client = InfluxDBClient(influxDB_address, influxDB_port, username=influxDB_user, password=influxDB_password)
        databases = client.get_list_database()

        device_names = []
        for db in databases:
            db_name = db["name"]
            if db_name.startswith("device_"):
                device_name = db_name.replace("device_", "")
                device_names.append(device_name)

        client.close()
        device_select.options = device_names
        if device_names:
            device_select.value = device_names[0]

        ui.notify(f"Found {len(device_names)} devices with data", type="positive")

    except Exception as e:
        ui.notify(f"Error loading devices: {e}", type="negative")


def create_plots(hours_input, plots_container):
    """Create plots once, then only update data"""
    global plot_figures
    global influxDB_address, influxDB_port, influxDB_user, influxDB_password

    if live_plots_active:
        ui.notify("Already running", type="warning")
        return

    try:
        client = InfluxDBClient(influxDB_address, influxDB_port, username=influxDB_user, password=influxDB_password)
        databases = client.get_list_database()
        device_dbs = [
            db["name"] for db in databases if db["name"].startswith("device_")
        ]

        plots_container.clear()
        plot_figures.clear()

        if not device_dbs:
            with plots_container:
                ui.label("No devices found").classes("text-center text-red-500")
            return

        hours = hours_input.value or 1
        colors = ["blue", "red", "green", "orange", "purple", "brown", "pink"]

        with plots_container:
            ui.label(f"Live Plots (Last {int(hours)}h)").classes(
                "text-xl font-bold mb-4"
            )

            for db_name in device_dbs:
                device_name = db_name.replace("device_", "")
                client.switch_database(db_name)

                # Get measurements
                measurements_query = client.query("SHOW MEASUREMENTS")
                measurements = [
                    list(point.values())[0] for point in measurements_query.get_points()
                ]

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
                                times = [p["time"] for p in points]
                                values = [p["value"] for p in points]
                                unit = points[0].get("unit", "")

                                trace_name = measurement.replace("_", " - ")
                                if unit:
                                    trace_name += f" [{unit}]"

                                fig.add_trace(
                                    go.Scatter(
                                        x=times,
                                        y=values,
                                        mode="lines+markers",
                                        name=trace_name,
                                        line=dict(
                                            width=2, color=colors[i % len(colors)]
                                        ),
                                        marker=dict(size=3),
                                    )
                                )
                        except Exception as e:
                            print(f"Error querying measurement {measurement}: {e}")
                            continue

                    if fig.data:
                        fig.update_layout(
                            title=f"Device: {device_name}",
                            xaxis_title="Time",
                            yaxis_title="Values",
                            height=400,
                            hovermode="x unified",
                        )

                        # Create plot widget and store reference
                        with ui.card().classes("w-full mb-4"):
                            ui.label(f"📊 {device_name}").classes("text-lg font-bold")
                            plot_widget = ui.plotly(fig).classes("w-full")

                            # Store references for updates
                            plot_figures[device_name] = {
                                "figure": fig,
                                "widget": plot_widget,
                                "measurements": measurements,
                                "db_name": db_name,
                            }

        client.close()
        ui.notify("Plots created for live updates", type="positive")

    except Exception as e:
        print(f"Error creating optimized plots: {e}")
        ui.notify(f"Error creating plots: {e}", type="negative")


def update_live_plots_data(hours_input):
    """Update only the data in existing plots"""
    global plot_figures
    global influxDB_address, influxDB_port, influxDB_user, influxDB_password

    if not plot_figures:
        return

    try:
        client = InfluxDBClient(influxDB_address, influxDB_port, username=influxDB_user, password=influxDB_password)
        hours = hours_input.value or 1

        for device_name, plot_data in plot_figures.items():
            try:
                client.switch_database(plot_data["db_name"])

                # Update each trace
                for i, measurement in enumerate(plot_data["measurements"]):
                    try:
                        # FIX: Correct time syntax
                        query = f'SELECT * FROM "{measurement}" WHERE time > now() - {int(hours)}h ORDER BY time ASC'
                        result = client.query(query)
                        points = list(result.get_points())

                        if points:
                            new_times = [p["time"] for p in points]
                            new_values = [p["value"] for p in points]

                            # Update trace data
                            if i < len(plot_data["figure"].data):
                                plot_data["figure"].data[i].x = new_times
                                plot_data["figure"].data[i].y = new_values
                    except Exception as e:
                        print(f"Error updating measurement {measurement}: {e}")
                        continue

                # Refresh the plot widget
                plot_data["widget"].update()

            except Exception as e:
                print(f"Error updating device {device_name}: {e}")
                continue

        client.close()
        # print(f"Plot data updated at {datetime.now().strftime('%H:%M:%S')}")

    except Exception as e:
        print(f"Error updating plot data: {e}")


# Modified live plot functions
def start_live_plots(hours_input, plots_container):
    """Start live plot updates with data-only updates"""
    global plot_timer, live_plots_active

    if live_plots_active:
        ui.notify("Already running", type="warning")
        return

    # Create plots once
    create_plots(hours_input, plots_container)

    # Start timer for data updates only
    live_plots_active = True
    plot_timer = ui.timer(1.0, lambda: update_live_plots_data(hours_input))

    ui.notify("Live plots started (1s data updates)", type="positive")


def stop_live_plots():
    """Stop live plot updates"""
    global plot_timer, live_plots_active

    if plot_timer:
        plot_timer.cancel()
        plot_timer = None

    live_plots_active = False
    ui.notify("Live plots stopped", type="info")


def show_device_info(device_select, device_info_container):
    """Show available measurements for selected device"""
    global influxDB_address, influxDB_port, influxDB_user, influxDB_password

    if not device_select.value:
        return

    try:
        device_name = device_select.value
        db_name = f"device_{device_name}"

        client = InfluxDBClient(influxDB_address, influxDB_port, username=influxDB_user, password=influxDB_password, database=db_name)
        result = client.query("SHOW MEASUREMENTS")
        measurements = [list(point.values())[0] for point in result.get_points()]
        client.close()

        device_info_container.clear()
        with device_info_container:
            ui.label(f"Available datapoints for {device_name}:").classes("font-bold")
            for measurement in measurements:
                # Split fp_dp back to readable format
                parts = measurement.split("_", 1)
                if len(parts) == 2:
                    fp, dp = parts
                    ui.label(f"• {fp} - {dp}").classes("ml-4 text-sm")
                else:
                    ui.label(f"• {measurement}").classes("ml-4 text-sm")

    except Exception as e:
        with device_info_container:
            ui.label(f"Error loading device info: {e}").classes("text-red-500")


# QR Code Configuration
async def download_yaml_from_qr(url: str, qr_code_container):
    """
    Download a YAML configuration file from a given QR-Code URL, parse it and display the  devices in the interface.

    Args:
        url (str): The URL to download the YAML file from.
        qr_code_container: The UI container to display the device list.

    Returns:
        list: List of device dictionaries found in the YAML file.
    """
    qr_code_container.clear()
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                ui.notify(f"Download error: {response.status}", type="negative")
                return []
            raw_bytes = await response.read()
            devices = yaml.safe_load(raw_bytes.decode("utf-8"))
            print(type(devices))

            # Extrahiere und zeige alle Gerätenamen in NiceGUI
            device_list = devices.get("devices", [])
            with qr_code_container:
                with ui.card():
                    ui.label("Found devices:").classes("text-lg font-bold")
                    for device in device_list:
                        name = device.get("name", "")
                        xml_name = device.get("smartGridreadyEID", "")
                        ui.label(f"• {name}  |  EID: {xml_name}").classes("ml-4")
            return device_list


async def show_datapoint_selection(devices, qr_code_container):
    """
    For each device, display all available datapoints as checkboxes.

    Args:
        devices (list): List of device dictionaries.
        qr_code_container: The UI container to display the selection UI.
    """
    qr_code_container.clear()
    device_checkbox_mapping = {}
    dev = None
    with qr_code_container:
        for device_info in devices:
            eid_file = device_info.get("smartGridreadyEID", "")
            eid_path = os.path.join("xml_files", eid_file) if eid_file else ""
            # Check if EID file exists locally
            if not eid_file or not os.path.exists(eid_path):
                ui.notify(
                    f"EID-Datei '{eid_file}' für Gerät '{device_info.get('name', '')}' nicht gefunden! "
                    "Please download the EID before.",
                    type="negative",
                )
                return
            try:
                dev = DeviceBuilder().eid_path(eid_path).build()
                description = dev.describe()
                data_dict = description[1]
            except Exception as e:
                ui.notify(
                    f"Error during EID load for {device_info.get('name', '')}: {e}",
                    type="negative",
                )
                continue

            checkbox_dict = {}
            ui.label(f'Datapoints for device: {device_info.get("name", "")}').classes(
                "text-xl font-bold mt-4"
            )
            for group, values in data_dict.items():
                for key in values.keys():
                    cb = ui.checkbox(f"{group}: {key}")
                    checkbox_dict[(group, key)] = cb

            device_checkbox_mapping[device_info.get("name", "")] = (
                device_info,
                checkbox_dict,
            )

        # save all selections for all devices
        def save_all_selections():
            """
            Collects all selected datapoints for all devices and saves them to the YAML file.
            If a device already exists it is updated. otherwise it is added.
            """
            global config_path
            yaml_file_path = os.path.join(config_path, "config.yaml")
            try:
                # Load existing data if available
                if os.path.exists(yaml_file_path):
                    with open(yaml_file_path, "r") as file:
                        existing_data = yaml.safe_load(file) or {}
                else:
                    existing_data = {}

                device_list = existing_data.get("devices", [])

                # Save selection for each device
                for name, (
                    device_info,
                    checkbox_dict,
                ) in device_checkbox_mapping.items():
                    selected = [
                        {"fp": pair[0], "dp": pair[1]}
                        for pair, cb in checkbox_dict.items()
                        if cb.value
                    ]
                    device_info["datapoints"] = selected

                    # Check if device already exists
                    eid = device_info.get("smartGridreadyEID", "")
                    device_info["type"] = "DEVICE"
                    found = False
                    for idx, dev in enumerate(device_list):
                        if dev.get("smartGridreadyEID", "") == eid:
                            device_list[idx] = device_info
                            found = True
                            break
                    if not found:
                        device_list.append(device_info)

                existing_data["devices"] = device_list

                # Write updated device list back to YAML
                with open(yaml_file_path, "w") as file:
                    yaml.dump(
                        existing_data, file, sort_keys=False, default_flow_style=False
                    )
                ui.notify("Devices are safed in configuration file!", type="positive")
            except Exception as e:
                ui.notify(f"Error during safe: {e}", type="negative")

        ui.button("Add all datapoints", on_click=save_all_selections).classes("mt-4")


async def yaml_workflow(qr_code_container):
    url = (
        "https://fl-17-166.zhdk.cloud.switch.ch/api/config/testlab?secret=TestsTestLab"
    )
    devices = await download_yaml_from_qr(url, qr_code_container)
    if devices:
        await show_datapoint_selection(devices, qr_code_container)
