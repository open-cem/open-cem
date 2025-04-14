from nicegui import ui
import GUI_functions as gui_func


selected_box = ui.input(label='Selected Identifier').classes('w-full')







ui.button('Load EIDs', on_click=gui_func.fetch_EIDs)
ui.button('Download EID', on_click=gui_func.download_EID)

ui.run()