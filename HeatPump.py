import socket
import struct
import time
from datetime import datetime
import paho.mqtt.client as mqtt
import json

# Configuration
HEATPUMP_IP = "10.0.0.73"
HEATPUMP_PORT = 8899
HEATPUMP_MAC = "xx xx xx xx xx xx"

# MQTT Configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_USER = "addons"
MQTT_PASSWORD = ""
DEVICE_ID = "heatpump_001"
DEVICE_NAME = "Heat Pump"
MANUFACTURER = "Unknown"
MODEL = "Unknown"

# MQTT Topics
MQTT_TOPIC_PREFIX = f"homeassistant/sensor/{DEVICE_ID}"
MQTT_AVAILABILITY_TOPIC = f"{MQTT_TOPIC_PREFIX}/availability"

# Updated offsets from your discovery
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
    
    # Status flags
    'outdoor_unit_mode': 210,
    'dhw_state': 146,
    'heating_state': 150,
    'cooling_state': 154,
    'defrost_state': 162,
    
    # Set temperatures (to be found)
    'dhw_set_temp': 166,
    'heating_set_temp': 246,
    'cooling_set_temp': 378,
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
    
    # Sensor configurations
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
        
        # Binary sensors
        'dhw_state': {
            'name': 'DHW State',
            'device_class': 'running',
            'payload_on': 'true',
            'payload_off': 'false'
        },
        'heating_state': {
            'name': 'Heating State',
            'device_class': 'heat',
            'payload_on': 'true',
            'payload_off': 'false'
        },
        'cooling_state': {
            'name': 'Cooling State',
            'device_class': 'cold',
            'payload_on': 'true',
            'payload_off': 'false'
        },
        'defrost_state': {
            'name': 'Defrost State',
            'device_class': 'running',
            'payload_on': 'true',
            'payload_off': 'false'
        },
        # Set temperature sensors (added)
        'dhw_set_temp': {
            'name': 'DHW Set Temperature',
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
        'cooling_set_temp': {
            'name': 'Cooling Set Temperature',
            'unit': 'Â°C',
            'device_class': 'temperature',
            'state_class': 'measurement'
        },
        
        # Unit mode sensor
        'outdoor_unit_mode': {
            'name': 'Outdoor Unit Mode',
            'state_class': 'measurement'
        }
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
        if OFFSETS[sensor_id] is None:
            continue
            
        topic = f"{MQTT_TOPIC_PREFIX}/{sensor_id}/config"
        
        if 'device_class' in config and config['device_class'] in ['running', 'heat', 'cold']:
            # Binary sensor
            payload = {
                "name": config['name'],
                "device_class": config['device_class'],
                "state_topic": f"{MQTT_TOPIC_PREFIX}/{sensor_id}/state",
                "availability_topic": MQTT_AVAILABILITY_TOPIC,
                "payload_on": config['payload_on'],
                "payload_off": config['payload_off'],
                "device": device_info,
                "unique_id": f"{DEVICE_ID}_{sensor_id}"
            }
        else:
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
        time.sleep(0.1)  # Small delay to avoid overwhelming the broker

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

def analyze_0143_packet(parameters):
    """Analyze 0143 packet with all known offsets"""
    log("=== 0143 Packet Analysis ===")
    
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
    
    # Status flags
    log("Status Flags:")
    dhw_state = decode_uint8(parameters[OFFSETS['dhw_state']]) if OFFSETS['dhw_state'] < len(parameters) else None #antes decode_bool
    heat_state = decode_bool(parameters[OFFSETS['heating_state']]) if OFFSETS['heating_state'] < len(parameters) else None
    cool_state = decode_bool(parameters[OFFSETS['cooling_state']]) if OFFSETS['cooling_state'] < len(parameters) else None
    defrost_state = decode_uint8(parameters[OFFSETS['defrost_state']]) if OFFSETS['defrost_state'] < len(parameters) else None #antes era decode_bool
    unit_mode = decode_uint8(parameters[OFFSETS['outdoor_unit_mode']]) if OFFSETS['outdoor_unit_mode'] < len(parameters) else None
    
    if dhw_state is not None:
        log(f"  DHW State: {'ON' if dhw_state else 'OFF'}")
        publish_mqtt_state('dhw_state', str(dhw_state).lower())
    if heat_state is not None:
        log(f"  Heating State: {'ON' if heat_state else 'OFF'}")
        publish_mqtt_state('heating_state', str(heat_state).lower())
    if cool_state is not None:
        log(f"  Cooling State: {'ON' if cool_state else 'OFF'}")
        publish_mqtt_state('cooling_state', str(cool_state).lower())
    if defrost_state is not None:
        log(f"  Defrost State: {'ON' if defrost_state else 'OFF'}")
        publish_mqtt_state('defrost_state', str(defrost_state).lower())
    if unit_mode is not None:
        log(f"  Unit Mode: {unit_mode}")
        publish_mqtt_state('outdoor_unit_mode', unit_mode)

def analyze_01b3_packet(parameters):
    """Analyze 01B3 packet to find set temperatures"""
    log("=== 01B3 Packet Analysis ===")
    
    # Read set temperatures from known offsets
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
#def analyze_01b3_packet(parameters):
    """Analyze 01B3 packet to find set temperatures"""
#    log("=== 01B3 Packet Analysis ===")
#    log("Searching for set temperatures (fixed values around 48, 55, 12Â°C):")
    
    # Look for the set temperatures in 01B3 packets
#    set_temp_candidates = []
 #   for i in range(0, len(parameters) - 3):
#       value = decode_float(parameters[i:i+4])
#        if value is not None and value in [12.0, 48.0, 55.0]:
#            set_temp_candidates.append((i, value))
#    
#    if set_temp_candidates:
#        for offset, value in set_temp_candidates:
#            log(f"  Set temp candidate at {offset}: {value}Â°C")
            
            # Try to identify which set temperature this is
#            if value == 47.0:
#                OFFSETS['dhw_set_temp'] = offset
#                log(f"    â†’ Likely DHW Set Temperature")
#            elif value == 55.0:
#                OFFSETS['heating_set_temp'] = offset
#                log(f"    â†’ Likely Heating Set Temperature")
#            elif value == 12.0:
#                OFFSETS['cooling_set_temp'] = offset
#                log(f"    â†’ Likely Cooling Set Temperature")
#    else:
#        log("  No set temperature values found")

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
            mqtt_client.publish(MQTT_AVAILABILITY_TOPIC, "offline", retain=True)
    finally:
        if sock:
            sock.close()

def capture_specific_packet(packet_type):
    """Capture a specific packet type"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((HEATPUMP_IP, HEATPUMP_PORT))
        
        target_command = 0x01 if packet_type == "0143" else 0x02
        
        log(f"Waiting for {packet_type} packet...")
        while True:
            data = sock.recv(1024)
            if data and len(data) >= 13 and data[12] == target_command:
                log(f"Received {packet_type} packet: {len(data)} bytes")
                parameters = data[13:]
                
                if packet_type == "0143":
                    analyze_0143_packet(parameters)
                else:
                    analyze_01b3_packet(parameters)
                
                break
                
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
            log("Capturing 01B3 packet to find set temperatures...")
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
