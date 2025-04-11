from nicegui import ui

def get_params():
    # This function will be called when the button is clicked
    # You can add your logic here to get the parameters from the device
    print("Button clicked!")

ui.button('Click me!', on_click=get_params)

ui.run()