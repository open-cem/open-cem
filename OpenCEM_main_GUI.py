from nicegui import ui
import GUI_functions as gui_func
import os
import plotly.graph_objects as go

ui.button('New System', on_click=gui_func.newSystem)
ui.button('Delete System', on_click=gui_func.open_popUp_deleteSystems)
ui.button('Load EIDs', on_click=gui_func.load_EIDs_name)
ui.button('Get Params', on_click=gui_func.getParams)
ui.button('Add Device', on_click=gui_func.addDevice)
ui.button('Download EID', on_click=gui_func.download_EID)
ui.button('get devices', on_click=gui_func.get_device_list_dropdown)
ui.button('delete devices', on_click=gui_func.delete_device_by_name)

ui.run()