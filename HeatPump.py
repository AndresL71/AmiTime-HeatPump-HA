import socket
import struct
import time
from datetime import datetime
import paho.mqtt.client as mqtt
import json

# Configuration
HEATPUMP_IP = ""
HEATPUMP_PORT = 8899
HEATPUMP_MAC = "XX XX XX XX XX XX"

# MQTT Configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_USER = "addons"
MQTT_PASSWORD = "yourpasswordhere"
DEVICE_ID = "heatpump_001"
DEVICE_NAME = "Heat Pump"
MANUFACTURER = "Unknown"
MODEL = "Unknown"

# MQTT Topics
MQTT_TOPIC_PREFIX = f"homeassistant/sensor/{DEVICE_ID}"
MQTT_AVAILABILITY_TOPIC = f"{MQTT_TOPIC_PREFIX}/availability"

# Updated offsets with all corrections
OFFSETS = {
    # Temperatures
    'outdoor_temp': 10,
    'dhw_temp': 14,
    'cooling_water_temp': 18,
    'outlet_temp': 22,
    'inlet_temp': 26,
    'room_temp': 54,
    'outdoor_ambient_2': 254,
    'outdoor_coil_temp': 258,
    'gas_discharge_temp': 262,
    'gas_suction_temp': 266,
    
    # Electrical measurements
    'voltage': 214,
    'current': 218,
    'compressor_freq_limit': 222,
    'compressor_freq': 226,
    
    # Pressure measurements
    'low_pressure': 278,
    'high_pressure': 282,
    
    # Status flags (0143 packet)
    'outdoor_unit_mode': 186,
    'dhw_state': 174,
    'heating_state': 178,
    'cooling_state': 182,
    'defrost_state': 286,
    
    # Set temperatures
    'dhw_set_temp': 166,
    'heating_set_temp': 246,
    'cooling_set_temp': 378,
    
    # 01B3 packet offsets
    'unit_on_off': 2,      # Como float (1.0 = ON, 0.0 = OFF)
    'working_mode': 6,     # Como float (1.0 = DHW, 2.0 = Heating, 3.0 = Cooling)
    'delta_t_compressor_speed': 18,
    'low_noise_mode': 66,  # Como float (1.0 = ON, 0.0 = OFF)
    'heating_delta_t': 250,
    'heating_curve_enabled': 330,  # Como float (1.0 = ON, 0.0 = OFF)
    'heating_curve_ambient_temp_1': 338,
    'heating_curve_water_temp_1': 342,
    'heating_curve_ambient_temp_2': 346,
    'heating_curve_water_temp_2': 350,
    'heating_curve_ambient_temp_3': 354,
    'heating_curve_water_temp_3': 358,
    'heating_curve_ambient_temp_4': 362,
    'heating_curve_water_temp_4': 366,
    'dhw_delta_t': 170,
    'cooling_delta_t': 382,
    
    # Priority settings - CHANGED TO 4-BYTE FLOATS
    'dhw_priority_min_time': 190,  # Now as 4-byte float
    'priority_ambient_start_temp': 306,
    'priority_heating_delta_t': 314,
    'priority_heating_working_time': 318,  # Now as 4-byte float
    
    # Aliases for sensor naming consistency
    'dhw_delta_temp': 170,
    'heating_delta_temp': 250,
    'cooling_delta_temp': 382,
    'shifting_priority_dhw_min_time': 190,  # Alias for dhw_priority_min_time
    'shifting_priority_ambient_start_temp': 306,
    'shifting_priority_heating_delta_temp': 314,
    'shifting_priority_heating_working_time': 318,  # Alias for priority_heating_working_time
}

# MQTT Client
mqtt_client = None

def log(message):
    """Print timestamped log messages"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def connect_mqtt():
    """Connect to MQTT broker"""
    global mqtt_client
    try:
        mqtt_client = mqtt.Client()
        mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        log(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        return True
    except Exception as e:
        log(f"MQTT connection failed: {e}")
        return False

def publish_mqtt_discovery():
    """Publish MQTT autodiscovery configuration for all sensors"""
    if not mqtt_client:
        return
    
    # Sensor configurations - updated with consistent naming
    sensors = {
        # Temperature sensors
        'outdoor_temp': {
            'name': 'Outdoor Temperature',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        'dhw_temp': {
            'name': 'DHW Temperature',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        'cooling_water_temp': {
            'name': 'Cooling Water Temperature',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        'outlet_temp': {
            'name': 'Outlet Temperature',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        'inlet_temp': {
            'name': 'Inlet Temperature',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        'room_temp': {
            'name': 'Room Temperature',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        'outdoor_ambient_2': {
            'name': 'Outdoor Ambient 2',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        'outdoor_coil_temp': {
            'name': 'Outdoor Coil Temperature',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        'gas_discharge_temp': {
            'name': 'Gas Discharge Temperature',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        'gas_suction_temp': {
            'name': 'Gas Suction Temperature',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        
        # Electrical sensors
        'voltage': {
            'name': 'Voltage',
            'unit': 'V',
            'device_class': 'voltage',
            'state_class': 'measurement'
        },
        'current': {
            'name': 'Current',
            'unit': 'A',
            'device_class': 'current',
            'state_class': 'measurement'
        },
        'compressor_freq_limit': {
            'name': 'Compressor Frequency Limit',
            'unit': 'Hz',
            'state_class': 'measurement'
        },
        'compressor_freq': {
            'name': 'Compressor Frequency',
            'unit': 'Hz',
            'state_class': 'measurement'
        },
        
        # Pressure sensors
        'low_pressure': {
            'name': 'Low Pressure',
            'unit': 'bar',
            'state_class': 'measurement'
        },
        'high_pressure': {
            'name': 'High Pressure',
            'unit': 'bar',
            'state_class': 'measurement'
        },
        
        # Set temperature sensors (01B3 packet)
        'dhw_set_temp': {
            'name': 'DHW Set Temperature',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        'dhw_delta_temp': {
            'name': 'DHW Delta Temperature',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        'heating_set_temp': {
            'name': 'Heating Set Temperature',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        'heating_delta_temp': {
            'name': 'Heating Delta Temperature',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        'cooling_set_temp': {
            'name': 'Cooling Set Temperature',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        'cooling_delta_temp': {
            'name': 'Cooling Delta Temperature',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        
        # Heating curve sensors (01B3 packet)
        'heating_curve_ambient_temp_1': {
            'name': 'Heating Curve Ambient Temp 1',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        'heating_curve_water_temp_1': {
            'name': 'Heating Curve Water Temp 1',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        'heating_curve_ambient_temp_2': {
            'name': 'Heating Curve Ambient Temp 2',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        'heating_curve_water_temp_2': {
            'name': 'Heating Curve Water Temp 2',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        'heating_curve_ambient_temp_3': {
            'name': 'Heating Curve Ambient Temp 3',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        'heating_curve_water_temp_3': {
            'name': 'Heating Curve Water Temp 3',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        
        # Priority settings (01B3 packet) - UPDATED FOR FLOAT VALUES
        'shifting_priority_ambient_start_temp': {
            'name': 'Priority Ambient Start Temp',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        'shifting_priority_heating_delta_temp': {
            'name': 'Priority Heating Delta Temp',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        
        # Time settings - UPDATED FOR FLOAT VALUES
        'shifting_priority_dhw_min_time': {
            'name': 'DHW Minimum Working Time',
            'unit': 'min',
            'state_class': 'measurement'
        },
        'priority_heating_working_time': {
            'name': 'Heating Working Time',
            'unit': 'min',
            'state_class': 'measurement'
        },
        
        # Delta T sensor
        'delta_t_compressor_speed': {
            'name': 'Delta T Compressor Speed',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        
        # Mode sensors
        'outdoor_unit_mode': {
            'name': 'Outdoor Unit Mode',
            'state_class': 'measurement'
        },
        'working_mode': {
            'name': 'Working Mode',
            'state_class': 'measurement'
        },
    }

    # Binary sensors
    binary_sensors = {
        'dhw_state': {
            'name': 'DHW Working State',
            'device_class': 'running',
            'payload_on': 'true',
            'payload_off': 'false'
        },
        'heating_state': {
            'name': 'Heating Working State',
            'device_class': 'heat',
            'payload_on': 'true',
            'payload_off': 'false'
        },
        'cooling_state': {
            'name': 'Cooling Working State',
            'device_class': 'cold',
            'payload_on': 'true',
            'payload_off': 'false'
        },
        'defrost_state': {
            'name': 'Defrost State',
            'device_class': 'problem',
            'payload_on': 'true',
            'payload_off': 'false'
        },
        'unit_on_off': {
            'name': 'Unit On/Off',
            'device_class': 'power',
            'payload_on': '1',
            'payload_off': '0'
        },
        'low_noise_mode': {
            'name': 'Low Noise Mode',
            'device_class': 'sound',
            'payload_on': '1',
            'payload_off': '0'
        },
        'heating_curve_enabled': {
            'name': 'Heating Curve Enabled',
            'device_class': 'power',
            'payload_on': '1',
            'payload_off': '0'
        },
    }

    # Device information
    device_info = {
        "identifiers": [DEVICE_ID],
        "name": DEVICE_NAME,
        "manufacturer": MANUFACTURER,
        "model": MODEL,
        "sw_version": "1.0"
    }
    
    # Publish discovery config for each sensor
    for sensor_id, config in sensors.items():
        if sensor_id not in OFFSETS or OFFSETS[sensor_id] is None:
            log(f"Skipping {sensor_id} - no offset defined")
            continue
            
        topic = f"{MQTT_TOPIC_PREFIX}/{sensor_id}/config"
        
        # Regular sensor
        payload = {
            "name": config['name'],
            "state_topic": f"{MQTT_TOPIC_PREFIX}/{sensor_id}/state",
            "availability_topic": MQTT_AVAILABILITY_TOPIC,
            "device": device_info,
            "unique_id": f"{DEVICE_ID}_{sensor_id}"
        }
        
        if 'unit' in config:
            payload["unit_of_measurement"] = config['unit']
        if 'device_class' in config:
            payload["device_class"] = config['device_class']
        if 'state_class' in config:
            payload["state_class"] = config['state_class']
        
        mqtt_client.publish(topic, json.dumps(payload), retain=True)
        log(f"Published discovery config for {sensor_id}")
        time.sleep(0.1)
    
    # Publish discovery config for each binary sensor
    for sensor_id, config in binary_sensors.items():
        if sensor_id not in OFFSETS or OFFSETS[sensor_id] is None:
            log(f"Skipping binary sensor {sensor_id} - no offset defined")
            continue
            
        topic = f"{MQTT_TOPIC_PREFIX}/{sensor_id}/config"
        
        payload = {
            "name": config['name'],
            "device_class": config['device_class'],
            "state_topic": f"{MQTT_TOPIC_PREFIX}/{sensor_id}/state",
            "availability_topic": MQTT_AVAILABILITY_TOPIC,
            "payload_on": config['payload_on'],
            "payload_off": config['payload_off'],
            "device": device_info,
            "unique_id": f"{DEVICE_ID}_{sensor_id}_binary"
        }
        
        mqtt_client.publish(topic, json.dumps(payload), retain=True)
        log(f"Published discovery config for binary sensor {sensor_id}")
        time.sleep(0.1)


def publish_mqtt_state(sensor_id, value):
    """Publish sensor state to MQTT"""
    if mqtt_client:
        topic = f"{MQTT_TOPIC_PREFIX}/{sensor_id}/state"
        mqtt_client.publish(topic, str(value))
        mqtt_client.publish(MQTT_AVAILABILITY_TOPIC, "online", retain=True)

def decode_float(bytes_data):
    """Decode 4-byte little-endian float"""
    try:
        return struct.unpack('<f', bytes_data)[0]
    except:
        return None

def decode_bool(byte_data):
    """Decode boolean value"""
    try:
        return bool(byte_data)
    except:
        return None

def decode_uint8(byte_data):
    """Decode single byte as unsigned integer"""
    try:
        return struct.unpack('<B', bytes([byte_data]))[0]
    except:
        return None

def decode_int16(bytes_data):
    """Decode 2-byte little-endian signed integer"""
    try:
        return struct.unpack('<h', bytes_data)[0]
    except:
        return None

def decode_uint16(bytes_data):
    """Decode 2-byte little-endian unsigned integer"""
    try:
        return struct.unpack('<H', bytes_data)[0]
    except:
        return None

def debug_raw_data(parameters, offset, length=4, description=""):
    """Debug function to show raw data at specific offset"""
    if offset + length <= len(parameters):
        raw_data = parameters[offset:offset+length]
        log(f"DEBUG {description} at offset {offset}: {raw_data.hex()}")
        return raw_data
    return None

def analyze_0143_packet(parameters):
    """Analyze 0143 packet with all known offsets"""
    log("=== 0143 Packet Analysis ===")
    
    # Debug: mostrar datos crudos en offsets importantes
    debug_raw_data(parameters, OFFSETS['dhw_state'], 1, "DHW State raw")
    debug_raw_data(parameters, OFFSETS['heating_state'], 1, "Heating State raw")
    debug_raw_data(parameters, OFFSETS['cooling_state'], 1, "Cooling State raw")
    debug_raw_data(parameters, OFFSETS['defrost_state'], 1, "Defrost State raw")
    
    # Temperature readings
    log("Temperatures:")
    for name, offset in OFFSETS.items():
        if 'temp' in name and offset is not None and offset + 4 <= len(parameters):
            value = decode_float(parameters[offset:offset+4])
            if value is not None:
                log(f"  {name.replace('_', ' ').title()}: {value:.1f}Â°C")
                publish_mqtt_state(name, value)
    
    # Electrical measurements
    log("Electrical Measurements:")
    voltage = decode_float(parameters[OFFSETS['voltage']:OFFSETS['voltage']+4])
    current = decode_float(parameters[OFFSETS['current']:OFFSETS['current']+4])
    comp_freq = decode_float(parameters[OFFSETS['compressor_freq']:OFFSETS['compressor_freq']+4])
    comp_freq_limit = decode_float(parameters[OFFSETS['compressor_freq_limit']:OFFSETS['compressor_freq_limit']+4])
    
    if voltage is not None:
        log(f"  Voltage: {voltage:.1f}V")
        publish_mqtt_state('voltage', voltage)
    if current is not None:
        log(f"  Current: {current:.1f}A")
        publish_mqtt_state('current', current)
    if comp_freq is not None:
        log(f"  Compressor Frequency: {comp_freq:.1f}Hz")
        publish_mqtt_state('compressor_freq', comp_freq)
    if comp_freq_limit is not None:
        log(f"  Compressor Frequency Limit: {comp_freq_limit:.1f}Hz")
        publish_mqtt_state('compressor_freq_limit', comp_freq_limit)
    
    # Pressure measurements
    log("Pressure Measurements:")
    low_press = decode_float(parameters[OFFSETS['low_pressure']:OFFSETS['low_pressure']+4])
    high_press = decode_float(parameters[OFFSETS['high_pressure']:OFFSETS['high_pressure']+4])
    
    if low_press is not None:
        log(f"  Low Pressure: {low_press:.1f}bar")
        publish_mqtt_state('low_pressure', low_press)
    if high_press is not None:
        log(f"  High Pressure: {high_press:.1f}bar")
        publish_mqtt_state('high_pressure', high_press)
    
    # Status flags - INTENTAR COMO FLOAT PRIMERO
    log("Status Flags:")
    
    # Intentar leer como floats de 4 bytes
    if OFFSETS['dhw_state'] + 4 <= len(parameters):
        dhw_state_float = decode_float(parameters[OFFSETS['dhw_state']:OFFSETS['dhw_state']+4])
        if dhw_state_float is not None:
            log(f"  DHW State (float): {'ON' if dhw_state_float == 1.0 else 'OFF'} (raw: {dhw_state_float})")
            publish_mqtt_state('dhw_state', 'true' if dhw_state_float == 1.0 else 'false')
    
    if OFFSETS['heating_state'] + 4 <= len(parameters):
        heating_state_float = decode_float(parameters[OFFSETS['heating_state']:OFFSETS['heating_state']+4])
        if heating_state_float is not None:
            log(f"  Heating State (float): {'ON' if heating_state_float == 1.0 else 'OFF'} (raw: {heating_state_float})")
            publish_mqtt_state('heating_state', 'true' if heating_state_float == 1.0 else 'false')
    
    if OFFSETS['cooling_state'] + 4 <= len(parameters):
        cooling_state_float = decode_float(parameters[OFFSETS['cooling_state']:OFFSETS['cooling_state']+4])
        if cooling_state_float is not None:
            log(f"  Cooling State (float): {'ON' if cooling_state_float == 1.0 else 'OFF'} (raw: {cooling_state_float})")
            publish_mqtt_state('cooling_state', 'true' if cooling_state_float == 1.0 else 'false')
    
    if OFFSETS['defrost_state'] + 4 <= len(parameters):
        defrost_state_float = decode_float(parameters[OFFSETS['defrost_state']:OFFSETS['defrost_state']+4])
        if defrost_state_float is not None:
            log(f"  Defrost State (float): {'ON' if defrost_state_float == 1.0 else 'OFF'} (raw: {defrost_state_float})")
            publish_mqtt_state('defrost_state', 'true' if defrost_state_float == 1.0 else 'false')
    
    # TambiÃƒÂ©n intentar como byte individual (backup)
    if OFFSETS['dhw_state'] < len(parameters):
        dhw_state_byte = decode_uint8(parameters[OFFSETS['dhw_state']])
        if dhw_state_byte is not None:
            log(f"  DHW State (byte): {'ON' if dhw_state_byte else 'OFF'} (raw: {dhw_state_byte})")
    
    if OFFSETS['outdoor_unit_mode'] < len(parameters):
        unit_mode = decode_uint8(parameters[OFFSETS['outdoor_unit_mode']])
        if unit_mode is not None:
            log(f"  Unit Mode: {unit_mode}")
            publish_mqtt_state('outdoor_unit_mode', unit_mode)

def analyze_01b3_packet(parameters):
    """Analyze 01B3 packet with all known offsets - CORREGIDO PARA FLOATS"""
    log("=== 01B3 Packet Analysis ===")
    
    # Debug: mostrar datos crudos en offsets importantes
    debug_raw_data(parameters, OFFSETS['unit_on_off'], 4, "Unit On/Off raw")
    debug_raw_data(parameters, OFFSETS['working_mode'], 4, "Working Mode raw")
    debug_raw_data(parameters, OFFSETS['low_noise_mode'], 4, "Low Noise Mode raw")
    debug_raw_data(parameters, OFFSETS['heating_curve_enabled'], 4, "Heating Curve Enabled raw")
    
    # Read set temperatures
    set_temps = {
        'dhw_set_temp': OFFSETS['dhw_set_temp'],
        'heating_set_temp': OFFSETS['heating_set_temp'],
        'cooling_set_temp': OFFSETS['cooling_set_temp']
    }
    
    for name, offset in set_temps.items():
        if offset is not None and offset + 4 <= len(parameters):
            value = decode_float(parameters[offset:offset+4])
            if value is not None:
                log(f"  {name.replace('_', ' ').title()}: {value:.1f}Â°C")
                publish_mqtt_state(name, value)
    
    # Unit status - LEER COMO FLOATS
    log("Unit Status:")
    
    # Para unit_on_off (offset 2) - como float
    if OFFSETS['unit_on_off'] + 4 <= len(parameters):
        unit_on_off = decode_float(parameters[OFFSETS['unit_on_off']:OFFSETS['unit_on_off']+4])
        if unit_on_off is not None:
            log(f"  Unit On/Off: {'ON' if unit_on_off == 1.0 else 'OFF'} (raw: {unit_on_off})")
            publish_mqtt_state('unit_on_off', 1 if unit_on_off == 1.0 else 0)
    
    # Para working_mode (offset 6) - como float
    if OFFSETS['working_mode'] + 4 <= len(parameters):
        working_mode = decode_float(parameters[OFFSETS['working_mode']:OFFSETS['working_mode']+4])
        if working_mode is not None:
            mode_names = {1.0: 'DHW', 2.0: 'Heating', 3.0: 'Cooling'}
            mode_name = mode_names.get(working_mode, f'Unknown ({working_mode})')
            log(f"  Working Mode: {mode_name} (raw: {working_mode})")
            publish_mqtt_state('working_mode', int(working_mode))
    
    # Para low_noise_mode (offset 66) - como float
    if OFFSETS['low_noise_mode'] + 4 <= len(parameters):
        low_noise_mode = decode_float(parameters[OFFSETS['low_noise_mode']:OFFSETS['low_noise_mode']+4])
        if low_noise_mode is not None:
            log(f"  Low Noise Mode: {'ON' if low_noise_mode == 1.0 else 'OFF'} (raw: {low_noise_mode})")
            publish_mqtt_state('low_noise_mode', 1 if low_noise_mode == 1.0 else 0)
    
    # Para heating_curve_enabled (offset 330) - como float
    if OFFSETS['heating_curve_enabled'] + 4 <= len(parameters):
        heating_curve_enabled = decode_float(parameters[OFFSETS['heating_curve_enabled']:OFFSETS['heating_curve_enabled']+4])
        if heating_curve_enabled is not None:
            log(f"  Heating Curve Enabled: {'ON' if heating_curve_enabled == 1.0 else 'OFF'} (raw: {heating_curve_enabled})")
            publish_mqtt_state('heating_curve_enabled', 1 if heating_curve_enabled == 1.0 else 0)
    
    # Resto del anÃƒÂ¡lisis (delta T, curva de calefacciÃƒÂ³n, prioridades)
    # Delta T values
    log("Delta T Values:")
    delta_t_compressor = decode_float(parameters[OFFSETS['delta_t_compressor_speed']:OFFSETS['delta_t_compressor_speed']+4])
    heating_delta_t = decode_float(parameters[OFFSETS['heating_delta_t']:OFFSETS['heating_delta_t']+4])
    dhw_delta_t = decode_float(parameters[OFFSETS['dhw_delta_t']:OFFSETS['dhw_delta_t']+4])
    cooling_delta_t = decode_float(parameters[OFFSETS['cooling_delta_t']:OFFSETS['cooling_delta_t']+4])
    
    if delta_t_compressor is not None:
        log(f"  Delta T Compressor Speed: {delta_t_compressor:.1f}Â°C")
        publish_mqtt_state('delta_t_compressor_speed', delta_t_compressor)
    if heating_delta_t is not None:
        log(f"  Heating Delta T: {heating_delta_t:.1f}Â°C")
        publish_mqtt_state('heating_delta_t', heating_delta_t)
        publish_mqtt_state('heating_delta_temp', heating_delta_t)
    if dhw_delta_t is not None:
        log(f"  DHW Delta T: {dhw_delta_t:.1f}Â°C")
        publish_mqtt_state('dhw_delta_t', dhw_delta_t)
        publish_mqtt_state('dhw_delta_temp', dhw_delta_t)
    if cooling_delta_t is not None:
        log(f"  Cooling Delta T: {cooling_delta_t:.1f}Â°C")
        publish_mqtt_state('cooling_delta_t', cooling_delta_t)
        publish_mqtt_state('cooling_delta_temp', cooling_delta_t)
    
    # Heating curve parameters
    log("Heating Curve Parameters:")
    heating_curve_params = {
        'heating_curve_ambient_temp_1': OFFSETS['heating_curve_ambient_temp_1'],
        'heating_curve_water_temp_1': OFFSETS['heating_curve_water_temp_1'],
        'heating_curve_ambient_temp_2': OFFSETS['heating_curve_ambient_temp_2'],
        'heating_curve_water_temp_2': OFFSETS['heating_curve_water_temp_2'],
        'heating_curve_ambient_temp_3': OFFSETS['heating_curve_ambient_temp_3'],
        'heating_curve_water_temp_3': OFFSETS['heating_curve_water_temp_3'],
        'heating_curve_ambient_temp_4': OFFSETS['heating_curve_ambient_temp_4'],
        'heating_curve_water_temp_4': OFFSETS['heating_curve_water_temp_4'],
    }
    
    for name, offset in heating_curve_params.items():
        if offset is not None and offset + 4 <= len(parameters):
            value = decode_float(parameters[offset:offset+4])
            if value is not None:
                log(f"  {name.replace('_', ' ').title()}: {value:.1f}Â°C")
                publish_mqtt_state(name, value)
    
    # Priority settings - UPDATED TO USE 4-BYTE FLOATS
    log("Priority Settings:")
    
    # dhw_priority_min_time (offset 190, 4 bytes as float)
    if OFFSETS['dhw_priority_min_time'] + 4 <= len(parameters):
        dhw_priority_min_time = decode_float(parameters[OFFSETS['dhw_priority_min_time']:OFFSETS['dhw_priority_min_time']+4])
        if dhw_priority_min_time is not None:
            log(f"  DHW Priority Min Time: {dhw_priority_min_time:.1f} min")
            publish_mqtt_state('dhw_priority_min_time', dhw_priority_min_time)
            publish_mqtt_state('shifting_priority_dhw_min_time', dhw_priority_min_time)
    
    # priority_ambient_start_temp (offset 306, 4 bytes)
    if OFFSETS['priority_ambient_start_temp'] + 4 <= len(parameters):
        priority_ambient_start_temp = decode_float(parameters[OFFSETS['priority_ambient_start_temp']:OFFSETS['priority_ambient_start_temp']+4])
        if priority_ambient_start_temp is not None:
            log(f"  Priority Ambient Start Temp: {priority_ambient_start_temp:.1f}Â°C")
            publish_mqtt_state('priority_ambient_start_temp', priority_ambient_start_temp)
            publish_mqtt_state('shifting_priority_ambient_start_temp', priority_ambient_start_temp)
    
    # priority_heating_delta_t (offset 314, 4 bytes)
    if OFFSETS['priority_heating_delta_t'] + 4 <= len(parameters):
        priority_heating_delta_t = decode_float(parameters[OFFSETS['priority_heating_delta_t']:OFFSETS['priority_heating_delta_t']+4])
        if priority_heating_delta_t is not None:
            log(f"  Priority Heating Delta T: {priority_heating_delta_t:.1f}Â°C")
            publish_mqtt_state('priority_heating_delta_t', priority_heating_delta_t)
            publish_mqtt_state('shifting_priority_heating_delta_temp', priority_heating_delta_t)
    
    # priority_heating_working_time (offset 318, 4 bytes as float)
    if OFFSETS['priority_heating_working_time'] + 4 <= len(parameters):
        priority_heating_working_time = decode_float(parameters[OFFSETS['priority_heating_working_time']:OFFSETS['priority_heating_working_time']+4])
        if priority_heating_working_time is not None:
            log(f"  Priority Heating Working Time: {priority_heating_working_time:.1f} min")
            publish_mqtt_state('priority_heating_working_time', priority_heating_working_time)
            publish_mqtt_state('shifting_priority_heating_working_time', priority_heating_working_time)

def monitor_heatpump():
    """Monitor heat pump and decode all known parameters"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect((HEATPUMP_IP, HEATPUMP_PORT))
        
        log("Starting comprehensive monitoring...")
        
        # Publish discovery configs
        publish_mqtt_discovery()
        
        while True:
            data = sock.recv(1024)
            if data and len(data) >= 13:
                command = data[12]
                parameters = data[13:]
                
                if command == 0x01:  # 0143 packet
                    log("\n" + "="*60)
                    log("0143 PACKET - REALTIME DATA")
                    analyze_0143_packet(parameters)
                    
                elif command == 0x02:  # 01B3 packet
                    log("\n" + "="*60)
                    log("01B3 PACKET - SET PARAMETERS")
                    analyze_01b3_packet(parameters)
                    
                else:
                    log(f"\nUnknown packet type: {command:02X}")
                
            time.sleep(1)
                
    except Exception as e:
        log(f"Monitoring stopped: {e}")
        if mqtt_client:
            mqtt_client.publish(MQTT_AVAILABILITY_TOPIC, "online", retain=True)
    finally:
        if sock:
            sock.close()

def capture_specific_packet(packet_type):
    """Capture a specific packet type"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect((HEATPUMP_IP, HEATPUMP_PORT))
        
        target_command = 0x01 if packet_type == "0143" else 0x02
        
        log(f"Waiting for {packet_type} packet...")
        start_time = time.time()
        while time.time() - start_time < 30:  # 30 second timeout
            data = sock.recv(1024)
            if data and len(data) >= 13 and data[12] == target_command:
                log(f"Received {packet_type} packet: {len(data)} bytes")
                parameters = data[13:]
                
                if packet_type == "0143":
                    analyze_0143_packet(parameters)
                else:
                    analyze_01b3_packet(parameters)
                
                return
                
        log(f"Timeout waiting for {packet_type} packet")
                
    except Exception as e:
        log(f"Error: {e}")
    finally:
        if sock:
            sock.close()

def main():
    """Main function"""
    # Connect to MQTT first
    if not connect_mqtt():
        log("MQTT connection failed. Continuing without MQTT...")
    
    while True:
        print("\n=== Complete Heat Pump Analyzer ===")
        print("1. Monitor all packets continuously (with MQTT)")
        print("2. Capture and analyze 0143 packet")
        print("3. Capture and analyze 01B3 packet (set temperatures)")
        print("4. Show current offsets")
        print("5. Publish MQTT discovery configs")
        print("6. Exit")
        
        choice = input("Select option: ").strip()
        
        if choice == "1":
            print("\n" + "="*60)
            log("Starting continuous monitoring (Ctrl+C to stop)")
            print("="*60)
            monitor_heatpump()
            
        elif choice == "2":
            print("\n" + "="*60)
            capture_specific_packet("0143")
            print("="*60)
            
        elif choice == "3":
            print("\n" + "="*60)
            log("Capturing 01B3 packet...")
            capture_specific_packet("01B3")
            print("="*60)
            
        elif choice == "4":
            print("\nCurrent Offsets:")
            for name, offset in OFFSETS.items():
                print(f"  {name}: {offset}")
            
        elif choice == "5":
            if mqtt_client:
                publish_mqtt_discovery()
                log("MQTT discovery configs published")
            else:
                log("MQTT not connected")
                
        elif choice == "6":
            log("Exiting...")
            if mqtt_client:
                mqtt_client.publish(MQTT_AVAILABILITY_TOPIC, "offline", retain=True)
                mqtt_client.loop_stop()
                mqtt_client.disconnect()
            break
            
        else:
            log("Invalid option")

if __name__ == "__main__":
    main()
