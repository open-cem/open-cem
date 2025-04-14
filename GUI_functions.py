import json
import aiohttp
from nicegui import ui

dropdown = None  # We'll store the select component here

async def fetch_EIDs():
    url = "https://library.smartgridready.ch/prod"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    ui.notify(f'HTTP Error: {response.status}', type='warning')
                    return

                raw_bytes = await response.read()
                data = json.loads(raw_bytes.decode('utf-8'))

                # Adjust if necessary
                identifiers = [item['identifier'] for item in data if item.get('releaseState') == 'Published']

                global dropdown
                if dropdown:
                    dropdown.delete()

                dropdown = ui.select(
                    options=identifiers,
                    label='Published Identifiers'
                ).classes('w-full')

    except Exception as e:
        ui.notify(f'Error: {e}', type='negative')


async def download_EID(EID_name):
    if dropdown and dropdown.value:
        EID_name = dropdown.value
    url = f"https://library.smartgridready.ch/{EID_name}?viewDevice"
    
    async with aiohttp.request('GET', url) as response:
        status_code = response.status
        xml_file = await response.read()  # response is xml in bytes

    # request successful
    if status_code == 200:
        try:
            # save file
            with open(f"xml_files/{EID_name}", "wb") as f:  # write it as bytes
                f.write(xml_file)
                
            
        except EnvironmentError:
            ui.notify(f'Error: Unable to save file', type='negative')
            return
    else:
        print(
            f"Download of SGr File failed. Check connection and uuid () of the devices in the field smartGridreadyFileId.")
