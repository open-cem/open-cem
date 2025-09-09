import json
import datetime
from influxdb import InfluxDBClient
import paho.mqtt.client as mqtt


class InfluxDataLogger:
    """
    Logger class for receiving device data via MQTT and storing it in InfluxDB.
    """
    def __init__(self, influx_host='localhost', influx_port=8086, 
                 mqtt_broker='localhost', mqtt_port=1883, mqtt_topic='openCEM/value'):
        """
        Initialize the logger.

        Args:
            influx_host (str): Hostname of the InfluxDB server.
            influx_port (int): Port of the InfluxDB server.
            mqtt_broker (str): Hostname of the MQTT broker.
            mqtt_port (int): Port of the MQTT broker.
            mqtt_topic (str): MQTT topic to subscribe to for device data.
        """
        #initialize InfluxDB client
        self.influx_client = InfluxDBClient(host=influx_host, port=influx_port)
        self.device_databases = {}
        
        # Initialize MQTT client and connection parameters
        self.mqtt_client = mqtt.Client()
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_topic = mqtt_topic
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """
        Callback for MQTT connection.

        Args:
            client: MQTT client instance.
            rc (int): Connection result.
        """
        if rc == 0:
            client.subscribe(self.mqtt_topic)
    
    def _process_device_data(self, data):
        """
        Process and store device data in InfluxDB.

        Args:
            data (dict): Dictionary with keys 'timestamp' and 'devices_list'.
                - timestamp (str): Format '%d/%m/%Y, %H:%M:%S'
                - devices_list (list): List of device dicts, each with:
                    - name (str)
                    - datapoints (list of dicts with keys 'fp', 'dp', 'value', 'unit', 'error_code')
        """
        timestamp = data.get('timestamp')
        devices_list = data.get('devices_list', [])
        
        dt = datetime.datetime.strptime(timestamp, '%d/%m/%Y, %H:%M:%S')
        
        for device in devices_list:
            device_name = device['name']
            db_name = f"device_{device_name}"
            
            # Ensure database exists
            if db_name not in self.device_databases:
                existing_db = [db['name'] for db in self.influx_client.get_list_database()]
                if db_name not in existing_db:
                    self.influx_client.create_database(db_name)
                self.device_databases[db_name] = True
            
            
            for dp in device.get('datapoints', []):
                measurement_name = f"{dp['fp']}_{dp['dp']}"
                try:
                    value = float(dp['value'])
                except (ValueError, TypeError):
                    value = 0.0 
                    
                datapoint = [{
                    "measurement": measurement_name,
                    "time": dt,
                    "fields": {
                        "value": value,
                        "unit": dp['unit'],
                        "error_code": dp.get('error_code', 0)
                    }
                }]
                
                self.influx_client.write_points(datapoint, database=db_name) 


    def _on_mqtt_message(self, client, userdata, msg):
        """
        Callback for incoming MQTT messages.

        Args:
            client: MQTT client instance.
            msg: MQTT message object.
        """
        try:
            data = json.loads(msg.payload.decode())
            print(f"Received data:")
            self._process_device_data(data)
        except Exception as e:
            print(f"Error: {e}")

    
    def start_logging(self):
        """
        Start the MQTT client and begin logging data to InfluxDB.

        """
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
        self.mqtt_client.loop_forever()

    def stop_logging(self):
        """
        Stop the MQTT client and disconnect.

        """
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()