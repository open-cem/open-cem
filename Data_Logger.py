import json
import datetime
from influxdb import InfluxDBClient
import paho.mqtt.client as mqtt


class InfluxDataLogger:
    def __init__(self, influx_host='localhost', influx_port=8086, 
                 mqtt_broker='localhost', mqtt_port=1883, mqtt_topic='device/data'):
        
        self.influx_client = InfluxDBClient(host=influx_host, port=influx_port)
        self.device_databases = {}
        
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_topic = mqtt_topic
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(self.mqtt_topic)
    
    def _on_mqtt_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            self._process_device_data(data)
        except Exception as e:
            print(f"Error: {e}")

    def _process_device_data(self, data):
        timestamp = data.get('timestamp')
        devices_list = data.get('devices_list', [])
        
        dt = datetime.datetime.strptime(timestamp, '%d/%m/%Y, %H:%M:%S')
        
        for device in devices_list:
            device_name = device['name']
            db_name = f"device_{device_name}"
            
            # Ensure database exists
            if db_name not in self.device_databases:
                existing_dbs = [db['name'] for db in self.influx_client.get_list_database()]
                if db_name not in existing_dbs:
                    self.influx_client.create_database(db_name)
                self.device_databases[db_name] = True
            
            
            for dp in device.get('dp', []):
                measurement_name = f"{dp['fp']}_{dp['dp']}"
                
                datapoint = [{
                    "measurement": measurement_name,
                    "time": dt,
                    "fields": {
                        "value": dp['value'],
                        "unit": dp['unit'],
                        "error_code": dp.get('error_code', 0)
                    }
                }]
                
                self.influx_client.write_points(datapoint, database=db_name) 

    def start_logging(self):
        self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
        self.mqtt_client.loop_forever()

    def stop_logging(self):
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()