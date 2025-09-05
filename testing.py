import asyncio
from sgr_commhandler.device_builder import DeviceBuilder

eid_path = 'xml_files/SGr_04_mmmm_dddd_Webasto_Next_V0.1.xml'
eid_properties = {
    "tcp_address": "192.168.137.119",
    "tcp_port": 502
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