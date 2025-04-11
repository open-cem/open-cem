import ast
import re
import json

import aiohttp
from pymodbus.client import ModbusTcpClient, AsyncModbusTcpClient
import yaml
import requests
from requests.auth import HTTPBasicAuth
from pymodbus.client import ModbusSerialClient as ModbusClient

global_rtu_client = False

class NativeDevice:

    def __init__(self, config):
        with open("yaml_files/" + config, "r") as f:
            s = f.read()

        self.config = yaml.safe_load(s)
        #placeholdersdict = self.get_placeholders(config)
        #self.yaml_data = self.update_yaml(config, placeholdersdict)
        #self.config = self.yaml_data

        #self.connect()

    def get_placeholders(self, yaml_data):
        """
        Extrahiert Platzhalterinformationen aus der Konfiguration.

        :param yaml_data: Die YAML-Daten als Dictionary.
        :return: Die Platzhalter als Dictionary.
        """
        placeholder_dict = yaml_data['configuration'][2].get('placeholder_info', {})
        #print(placeholder_dict)
        return placeholder_dict

    def replace_placeholders(self, text, placeholder):
        #with open("EID_params/" + placeholder, "r") as f:
         #   s = f.read()

        #placeholder_dict = yaml.safe_load(s)
        placeholder_dict = placeholder
        placeholders = set(placeholder_dict.keys())
        for key in placeholders:
            placeholder_pattern = r"_" + key + r"_"
            text = re.sub(placeholder_pattern, placeholder_dict[key], text)
        return text

    def update_yaml(self, placeholder):
        """
        Ersetzt Platzhalter in den YAML-Daten durch die entsprechenden Werte.

        :param yaml_data: Die YAML-Daten als Dictionary.
        :param placeholder_dict: Die Platzhalter als Dictionary.
        :return: Die aktualisierten YAML-Daten als Dictionary.
        """



        json_string = json.dumps(self.config)
        replaced_test = self.replace_placeholders(json_string, placeholder)
        self.yaml_data = json.loads(replaced_test)
        #return yaml_data
        self.register_map = self.create_register_map(self.yaml_data)

    def create_register_map(self, yaml_replaced):
        """
        Erstellt eine Dictionary aus den Funktionsprofilen.

        :param yaml_data: Die YAML-Daten als Dictionary.
        :return: Die Funktionsprofile als Dictionary.
        """
        register_map = {}
        functional_profiles = yaml_replaced.get('FunctionalProfiles', [])

        for profile in functional_profiles:
            for profile_name, registers in profile.items():
                for reg_name, reg_info in registers.items():
                    register_map[reg_name] = reg_info

        return register_map

    def connect(self):

        com_type = self.yaml_data['configuration'][0].get('Interfacetype')
        interface = self.yaml_data['configuration'][1].get('Interface')
        
        # decision tree for CommunicationChannel type
        match com_type:

            case "MODBUS_TCP":

                address = interface["address"]
                port = interface["port"]
                print(address)
                print(port)
                self.client = ModbusTcpClient(address, port = port)

                if self.client.connect():
                    print("Connected to Modbus server")

                if not self.client.connect():
                    raise ConnectionError("NOT  connect to Modbus server")
                # evtl Routeradresse
                # ethernet port
                pass

            case "MODBUS_RTU":
                global global_rtu_client
                if not global_rtu_client:
                    port= interface["PortName"] 
                    baudrate= int(interface["Baudrate"])
                    parity= interface["Parity"]
                    stopbits= int(interface["Stopbits"])
                    bytesize= int(interface["Bytesize"])
                    print("Stopbitstyp________________________________")
                    print(type(bytesize))
                    self.client = ModbusClient(
                        port= port, 
                        baudrate= baudrate,
                        parity= parity,
                        stopbits= stopbits,
                        bytesize=   bytesize,
                        timeout=1
                    )
                    global_rtu_client = True
                else:
                    print("Client already exists")
                

            case "HTTP_LOCAL":
                self.client = None
          
            case "HTTP_MAIN":
                self.client = aiohttp.ClientSession()

            case "REST_API":
                if interface["authentication"]["AuthenticationMethod"] == "BearerSecurityScheme":
                    header = interface["authentication"]["BearerSecurity"]["Header"]
                    body = interface["authentication"]["BearerSecurity"]["Body"]
                    method = interface["authentication"]["BearerSecurity"]["Method"]
                    EndPoint = interface["authentication"]["BearerSecurity"]["EndPoint"]
                    BaseURL = interface["BaseURL"]
                    payload1 = json.dumps(body)

                    self.token = requests.request(method, BaseURL + EndPoint, headers=header, data=payload1)
                    self.token = self.token.json()
                    self.token = self.token["accessToken"]
                    print("connected")
                    print("token")
                    print(self.token)
                elif interface["authentication"]["AuthenticationMethod"] == "BasicSecurityScheme":
                    print("BasicSecurityScheme")
                    pass
                elif interface["authentication"]["AuthenticationMethod"] == "NoSecurityScheme":
                    
                    pass
                else:
                    raise NotImplementedError("Authentication method" + interface["authentication"]["AuthenticationMethod"])

            case _:
                raise NotImplementedError(f"Communication {type} not known.")

    def read_Value(self, data_point):


        error_code = 22
        interface = self.yaml_data['configuration'][1].get('Interface')
        com_type = self.yaml_data['configuration'][0].get('Interfacetype')
        dp_info = self.register_map.get(data_point)

        if not dp_info:
            raise ValueError(f"Register {data_point} not found")
        

        # decision tree for CommunicationChannel type
        match com_type:

            case "MODBUS_TCP":
                offset = self.yaml_data['configuration'][1]['Interface']['FirstRegisterAddress']
                address = dp_info['Register']
                size = dp_info['Size']
                scaling = dp_info['Scaling']

                
                result = self.client.read_input_registers(address - offset, size, 1)
                
                if result.isError():
                    raise IOError(f"Error reading register {address}")

                return result.registers[0]*scaling, dp_info['Unit'], error_code
            case "MODBUS_RTU":
                slave_ID = int(interface["SlaveAddress"])
                address = dp_info['Register']
                size = dp_info['Size']
                scaling = dp_info['Scaling']

                offset = interface["FirstRegisterAddress"]
                response = self.client.read_holding_registers(address + offset, size, slave = slave_ID)
                return response.registers[0] * scaling , dp_info['Unit'], error_code
            case "HTTP_LOCAL":
                pass
            case "REST_API":
                baseURL = self.yaml_data['configuration'][1]['Interface']['BaseURL']
                response_scheme = dp_info['Response_scheme']
                header = dp_info['Header']
                header_key, header_value = header.split(": ")
                endpoint = dp_info['EndPoint']
                full_endpoint = baseURL + endpoint
                method = dp_info['Method']


                if interface["authentication"]["AuthenticationMethod"] == "BearerSecurityScheme":
                   
                    
                    headers ={
                                "Authorization": f"Bearer {self.token}",
                                "Accept" : "application/json"
                             }
                    response = requests.request(method, full_endpoint, headers=headers)

                    response = json.loads(response.text)
                   
                    # Evaluate the response_scheme as a function
                    response = eval(response_scheme)

                if interface["authentication"]["AuthenticationMethod"] == "BasicSecurityScheme":
                    username = interface["authentication"]["username"]
                    password = interface["authentication"]["password"]
                    response = requests.request(method,
                                full_endpoint,
                                auth=HTTPBasicAuth(username,password)
                            )
                    response = json.loads(response.text)
                    print(response)
                    # Evaluate the response_scheme as a function
                    response = eval(response_scheme)

                if interface["authentication"]["AuthenticationMethod"] == "NoSecurityScheme":
                    
                    header = {
                                "Accept" : "application/json"
                             }
                    
                    if "Data" in dp_info:
                        data = dp_info['Data']
                        response = requests.request(method, full_endpoint, data=data)
                    elif "Params" in dp_info:
                        params = dp_info['Params']
                        response = requests.request(method, full_endpoint, params=params)
                    else:
                        response = requests.request(method, full_endpoint, headers=header)
                       
                    #Data = ast.literal_eval(data)

                    response = json.loads(response.text)
                
                    
                    response = eval(response_scheme)

                return response , dp_info['Unit'], error_code


            case "MQTT":

                pass
            case _:
                pass

    def write_Value(self, functional_profile, data_point, value):
        pass


