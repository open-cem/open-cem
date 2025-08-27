from nicegui import ui
import GUI_functions
import os
import plotly.graph_objects as go

def trigger_indicator():
        if status_light.color == 'red':
            status_light.color = 'green'
            status_label.text = 'Live plots: ON'
        else:
            status_light.color = 'red'
            status_label.text = 'Live plots: OFF'


# Create tabs
with ui.tabs().classes('w-full') as tabs:
    config_tab = ui.tab('config', label='Configuration')
    QRCode_tab = ui.tab('QRcode', label='QR Code Configuration')
    control_tab = ui.tab('control', label='Control')
    plots_tab = ui.tab('plots', label='Device Plots')

with ui.tab_panels(tabs, value='config').classes('w-full'):
    
    # Configuration Tab
    with ui.tab_panel('config'):
        system_management_card = ui.card().classes('w-full')
        with system_management_card:
            ui.label('System Management').classes('text-lg font-bold mb-2')
            textbox_system = ui.input(label='Enter System Name').classes('w-full')
            ui.button('New System', on_click=GUI_functions.newSystem)
            ui.button('Delete System', on_click=GUI_functions.open_popUp_deleteSystems)

        device_management = ui.card().classes('w-full')
        config_container = ui.column().classes('w-full')

        #latest_value_box = ui.input(label='Latest Value').classes('w-full')


        with device_management:
            ui.label('Device Management').classes('text-lg font-bold mb-2')
            ui.button('Get new Device', on_click=lambda: GUI_functions.load_local_EIDs(config_container))
            textbox_device = ui.input(label='Enter Product Name').classes('w-full')
            ui.button('Load online EIDs', on_click=GUI_functions.load_online_EIDs, icon='mdi-cloud-download')
            ui.button('Download EID', on_click=GUI_functions.download_EID)
            ui.button('Get Params', on_click=GUI_functions.getParams)
            ui.button('Add Device', on_click=GUI_functions.addDevice)
            ui.button('get Configuration', on_click=lambda: GUI_functions.dynamic_pagination(device_management))
            ui.button('Clear config box', on_click=GUI_functions.clear_config_box)
            ui.button('get devices', on_click=GUI_functions.get_device_list_dropdown)

        ui.button('delete devices', on_click=GUI_functions.delete_device_by_name)

    with ui.tab_panel('QRcode'):
        with ui.row().classes('gap-4'):
            ui.label('QR Code Configuration').classes('text-2xl font-bold mb-4')

            ui.button('get QRCode configuration', on_click=lambda: GUI_functions.yaml_workflow(qr_code_config_container)).props('color=positive')
            qr_code_config_container = ui.column().classes('w-full')

    # Control Tab
    with ui.tab_panel('control'):
        ui.label('OpenCEM Control').classes('text-2xl font-bold mb-4')
        
        with ui.card().classes('w-full'):
            with ui.row().classes('gap-2'):
                ui.button('start OpenCEM', on_click=GUI_functions.start_OpenCEM).props('color=positive')
                ui.button('stop OpenCEM', on_click=GUI_functions.stop_OpenCEM).props('color=negative')
                ui.button('start MQTT/Plots', on_click=GUI_functions.start_mqtt).props('color=primary')
        
        with ui.card().classes('w-full mt-4'):
            ui.label('Latest MQTT Value').classes('text-lg font-bold mb-2')

        # Plots Tab
        # In your OpenCEM_main_GUI.py plots tab:
    with ui.tab_panel('plots'):
        ui.label('Live Device Plots').classes('text-2xl font-bold mb-4')
        
        with ui.card().classes('w-full mb-4'):
            with ui.row().classes('gap-4'):
                hours_input = ui.number('Hours', value=1, min=1, max=48).classes('w-32')
                
                ui.button('Show Archive', 
                        on_click=lambda: GUI_functions.create_plots(hours_input, plots_container)).props('color=secondary')

                ui.button('Start Live', 
                        on_click=lambda: [
                            GUI_functions.start_live_plots(hours_input, plots_container),
                            status_light.props('color=green'),
                            setattr(status_label, 'text', 'Live plots: ON')
                        ]).props('color=positive')
                
                ui.button('Stop Live', 
                        on_click=lambda:[
                            GUI_functions.stop_live_plots(),
                            status_light.props('color=red'),
                            setattr(status_label, 'text', 'Live plots: OFF')
                        ]).props('color=negative')
                
                ui.label('Data updates every 1 second').classes('text-sm text-gray-600')
        
                with ui.row().classes('items-center gap-2'):
                        status_light = ui.icon('circle', color='red').classes('text-lg')
                        status_label = ui.label('Live plots: OFF').classes('text-sm font-bold')

        plots_container = ui.column().classes('w-full')
        
        with plots_container:
            ui.label('Click "Create Plots" first, then "Start Live"').classes('text-center text-gray-500 p-8')

    

ui.run()

"""
# Debug: Zeige alle verfügbaren Funktionen
print("Available functions in GUI_functionstions:")
print(dir(GUI_functionstions))
ui.button('New System', on_click=GUI_functionstions.newSystem)

system_management_card = ui.card().classes('w-full')
with system_management_card:
    ui.label('System Management').classes('text-lg font-bold mb-2')
    ui.button('New System', on_click=GUI_functionstions.newSystem)
    ui.button('Delete System', on_click=GUI_functionstions.open_popUp_deleteSystems)
#ui.button('Load EIDs', on_click=GUI_functions.load_EIDs_name)
device_management = ui.card().classes('w-full')
with device_management:
    ui.label('Device Management').classes('text-lg font-bold mb-2')
    ui.button('Get new Device', on_click=GUI_functionstions.load_local_EIDs)
    ui.button('Load online EIDs', on_click=GUI_functionstions.load_online_EIDs, icon='mdi-cloud-download')
    ui.button('Download EID', on_click=GUI_functionstions.download_EID)
    ui.button('Get Params', on_click=GUI_functionstions.getParams)
    ui.button('Add Device', on_click=GUI_functionstions.addDevice)

    ui.button('get Configuration', on_click=lambda: GUI_functionstions.dynamic_pagination(device_management))
    ui.button('Clear config box', on_click=GUI_functionstions.clear_config_box)

    ui.button('get devices', on_click=GUI_functionstions.get_device_list_dropdown)
    ui.button('delete devices', on_click=GUI_functionstions.delete_device_by_name)
    ui.button('start OpenCEM', on_click=GUI_functionstions.start_OpenCEM)
    ui.button('start plot', on_click=GUI_functionstions.start_mqtt)
ui.run()
"""