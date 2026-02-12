import os
import asyncio
from sgr_commhandler.device_builder import DeviceBuilder

xml_path = os.environ.get('XML_PATH', 'xml_files')
eid_path = os.path.join(xml_path, 'SGr_02_mmmm_8288089799_Smart-me_SubMeterElectricity_V1.1.0.xml')
eid_properties = {
    "device_id": "f25f4e20-b803-de4e-e75c-2714e2c0c2d9",
    "username": "smartgridready2024@gmail.com",
    "password": "SmartGrid%24",
}


async def test_device_points():
    # Device bauen und Datenpunkte extrahieren
    dev = DeviceBuilder().eid_path(eid_path).build()
    description = dev.describe()
    data_dict = description[1]
    print("Extrahierte Datenpunkte:")
    for group, values in data_dict.items():
        for key in values.keys():
            print(f"{group}: {key}")

    # Device mit Properties verbinden
    device = DeviceBuilder().eid_path(eid_path).properties(eid_properties).build()
    await device.connect_async()

    # Alle extrahierten Datenpunkte abfragen
    print("\nWerte aller Datenpunkte:")
    for group, values in data_dict.items():
        for key in values.keys():
            try:
                dp = device.get_data_point((group, key))
                value = await dp.get_value_async()
                unit = dp.unit().name if dp.unit() else "NONE"
                print(f"{group}/{key}: {value} {unit}")
            except Exception as e:
                print(f"Fehler bei {group}/{key}: {e}")

    await device.disconnect_async()

if __name__ == "__main__":
    asyncio.run(test_device_points())
