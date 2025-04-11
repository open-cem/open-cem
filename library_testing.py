
from nicegui import ui
from sgr_commhandler.device_builder import DeviceBuilder
import os
import logging

import asyncio


# Global variable to store the device instance


async def main():

    eid_path = 'xml_files/SGr_04_0015_xxxx_StiebelEltron_HeatPump_V1.0.0.xml'
    eid_properties = {
       'tcp_address': '192.168.137.219',
       'slave_id': 1,
       'tcp_port': 502
    }



    
 
    
    device = DeviceBuilder().eid_path(eid_path).properties(eid_properties).build()

    await device.connect_async()
    fp = device.get_functional_profile("HeatCoolCtrl_1")
    
    dp = fp.get_data_point("SupplyWaterTempSetpointComfort")
    dp.set_value
    await dp.set_value_async(22)
    #values = await device.get_values_async()
    #value = await dp.get_value_async()
    #print(value)
    #values = await device.get_data_point("BufferStorageCtrl")
    
    #print(type(unit))
    


    #for k,v in values.items():
        #print(str(k) + ': ' + str(v))
    #await dp.set_value_async(1)
    

    #device.configuration_parameters

    

    #names = [param.name for param in params]

    #print(names)
    #third_words = [item.split()[2] for item in params]

    #print(third_words)
    

    
    #values = await device.get_values_async()
    

    #for k,v in values.items():
    #    print(str(k) + ': ' + str(v))
    


    #get values from the device

    
   




    #value_dp = await dp.get_value_async()
    #print(value_dp)
    

    #set values to the device
    #dp = device.get_functional_profile("EnergyMonitor").get_data_point("ActiveEnergyACtot")
    #unit = dp.unit()
    #fp = device.get_functional_profile("ActivePowerAC")
   

    #values = await dp.get_value_async()
    
    #values = await device.get_data_point("BufferStorageCtrl")
    #print(values)
    #print(type(unit))
    


    #for k,v in values.items():
    #    print(str(k) + ': ' + str(v))











    #device.update_config(params)
    #device.build()
    #param = ["Base URL - baseuri", "Identification - sensor_id", "User Name - username", "Password - password"]

    #dict_param = dict(param)


    #device.describe()
    # await device.connect()
    #await device.read_data()

   
    #device.get_function_profile("ActivePowerAC").get_data_point("ActivePowerACtot").
    #find me here /dev/tty.usbmodem56D11292701 E 19200
    await device.disconnect_async()
# Run the main function
if __name__ == "__main__":
    # Check if an event loop is already running
    try:
        asyncio.run(main())
    except RuntimeError as e:
        print("Event loop is already running. Using alternative execution.")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
#asyncio.run(main())
