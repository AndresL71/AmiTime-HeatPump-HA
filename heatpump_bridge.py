# /config/apps/heatpump_bridge.py
import appdaemon.plugins.hass.hassapi as hass
import paho.mqtt.client as mqtt
import socket, struct, time, json, threading, re
import requests
from datetime import datetime

class HeatpumpBridge(hass.Hass):
    #
    # ---------------------- AppDaemon lifecycle ----------------------
    #
    def initialize(self):
        # ---- Config ----
        self.mqtt_broker = self.args.get("mqtt_broker", "127.0.0.1")
        self.mqtt_port   = int(self.args.get("mqtt_port", 1883))
        self.mqtt_user   = self.args.get("mqtt_user", "")
        self.mqtt_pass   = self.args.get("mqtt_pass", "")

        self.device_id   = self.args.get("device_id", "heatpump_001")
        self.device_name = self.args.get("device_name", "Heat Pump")
        self.manufacturer= self.args.get("manufacturer", "Unknown")
        self.model       = self.args.get("model", "Unknown")

        self.hp_ip       = self.args.get("heatpump_ip")
        self.hp_port     = int(self.args.get("heatpump_port"))
        self.cookie_raw  = self.args.get("cookie_raw", "")
        self.mn          = self.args.get("mn")
        self.devid       = self.args.get("devid")
        self.cloud_url   = self.args.get("cloud_url", "https://www.myheatpump.com/a/amt/setdata/update")

        # Logging level
        self.log_level = str(self.args.get("log_level", "INFO")).upper()
        # Use AppDaemon logger, but gate noisy messages manually
        self.debug_enabled = self.log_level in ("DEBUG", "TRACE")
        self.info_enabled  = self.log_level in ("INFO", "DEBUG", "TRACE")

        self.log("HeatpumpBridge starting...", level="INFO")
        # ---- Topics ----
        self.discovery_prefix = "homeassistant"
        self.base_sensor_prefix = f"{self.discovery_prefix}/sensor/{self.device_id}"
        self.avail_topic = f"{self.base_sensor_prefix}/availability"

        # ---- Cookies ----
        self.cookies = self._parse_cookie(self.cookie_raw)

        # ---- MQTT ----
        self.mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"{self.device_id}_bridge")
        if self.mqtt_user:
            self.mqttc.username_pw_set(self.mqtt_user, self.mqtt_pass)

        self.mqttc.will_set(self.avail_topic, "offline", retain=True)
        self.mqttc.on_connect = self._on_mqtt_connect
        self.mqttc.on_message = self._on_mqtt_message
        self.mqttc.enable_logger(logger=None)  # prevent paho from spamming HA logs

        # Connect & loop in background
        try:
            self.mqttc.connect(self.mqtt_broker, self.mqtt_port, keepalive=60)
            self.mqttc.loop_start()
            self.log(f"MQTT connected to {self.mqtt_broker}:{self.mqtt_port}", level="INFO")
        except Exception as e:
            self.log(f"MQTT connect error: {e}", level="ERROR")

        # Publish discovery now (retain)
        self._publish_discovery_controls()
        self._publish_discovery_sensors()
        self._pub(self.avail_topic, "online", retain=True)
        if self.info_enabled:
            self.log("Published MQTT discovery (controls)")
            self.log("Published MQTT discovery (sensors)")

        # ---- Packet decode offsets (same as your working script) ----
        self.OFF = {
            # Temperatures
            'outdoor_temp': 10, 'dhw_temp': 14, 'cooling_water_temp': 18,
            'outlet_temp': 22,  'inlet_temp': 26, 'room_temp': 54,
            'outdoor_ambient_2': 254, 'outdoor_coil_temp': 258,
            'gas_discharge_temp': 262, 'gas_suction_temp': 266,
            # Electrical
            'voltage': 214, 'current': 218, 'compressor_freq_limit': 222, 'compressor_freq': 226,
            # Pressure
            'low_pressure': 278, 'high_pressure': 282,
            # Status (0143)
            'outdoor_unit_mode': 186, 'dhw_state': 174, 'heating_state': 178,
            'cooling_state': 182, 'defrost_state': 286,
            # Set temps (01B3)
            'dhw_set_temp': 166, 'heating_set_temp': 246, 'cooling_set_temp': 378,
            # 01B3
            'unit_on_off': 2, 'working_mode': 6, 'delta_t_compressor_speed': 18,
            'low_noise_mode': 66, 'heating_delta_t': 250, 'heating_curve_enabled': 330,
            'heating_curve_ambient_temp_1': 338, 'heating_curve_water_temp_1': 342,
            'heating_curve_ambient_temp_2': 346, 'heating_curve_water_temp_2': 350,
            'heating_curve_ambient_temp_3': 354, 'heating_curve_water_temp_3': 358,
            'heating_curve_ambient_temp_4': 362, 'heating_curve_water_temp_4': 366,
            'dhw_delta_t': 170, 'cooling_delta_t': 382,
            'dhw_priority_min_time': 190, 'priority_ambient_start_temp': 306,
            'priority_heating_delta_t': 314, 'priority_heating_working_time': 318,
        }

        # ---- Start TCP reader thread ----
        self._stop_event = threading.Event()
        self.sock_thread = threading.Thread(target=self._socket_loop, name="hp_socket", daemon=True)
        self.sock_thread.start()

        self.log("HeatpumpBridge launched", level="INFO")

    def terminate(self):
        # Graceful shutdown
        try:
            self._stop_event.set()
        except Exception:
            pass
        try:
            self._pub(self.avail_topic, "offline", retain=True)
        except Exception:
            pass
        try:
            self.mqttc.loop_stop()
            self.mqttc.disconnect()
        except Exception:
            pass
        self.log("HeatpumpBridge terminated", level="INFO")

    #
    # ---------------------- MQTT helpers ----------------------
    #
    def _on_mqtt_connect(self, client, userdata, flags, reason_code, properties):
        if self.info_enabled:
            self.log(f"MQTT on_connect rc={reason_code}")
        client.subscribe("heatpump/set/#")

    def _on_mqtt_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode().strip()
            if not topic.startswith("heatpump/set/"):
                return
            par = topic.split("/")[-1]
            # Normalize expected values for select "mode"
            if par == "par2" and payload in ("Heating", "DHW", "Cooling"):
                payload = {"Cooling": "0", "DHW": "1", "Heating": "2"}[payload]

            self.log(f"CMD {par}={payload}", level="INFO")

            data = {"id": "", "mn": self.mn, "devid": self.devid,
                    par: payload, "fieldName": par, "fieldValue": payload}

            r = requests.post(self.cloud_url, data=data, cookies=self.cookies, timeout=10)
            res = r.json() if r.headers.get("content-type","").startswith("application/json") else {}
            if str(res.get("result")).lower() == "true":
                self.log(f"Cloud OK: {par}={payload}", level="INFO")
                # publish state echo (so HA UI reflects immediately)
                self._pub(f"heatpump/state/{par}", payload, retain=True)
            else:
                self.log(f"Cloud ERROR for {par}: HTTP {r.status_code} {res}", level="ERROR")

        except Exception as e:
            self.log(f"on_message error: {e}", level="ERROR")

    def _pub(self, topic, payload, retain=False):
        try:
            self.mqttc.publish(topic, payload, retain=retain)
        except Exception as e:
            self.log(f"MQTT publish error to {topic}: {e}", level="ERROR")

    #
    # ---------------------- Discovery ----------------------
    #
    def _device_info(self):
        return {
            "identifiers": [self.device_id],
            "name": self.device_name,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "sw_version": "1.0",
        }

    def _pub_disc(self, comp, uid, payload):
        payload["device"] = self._device_info()
        self._pub(f"{self.discovery_prefix}/{comp}/{uid}/config",
                  json.dumps(payload), retain=True)

    def _publish_discovery_controls(self):
        # LWT
        self._pub(self.avail_topic, "online", retain=True)

        # Power switch (par1)
        self._pub_disc("switch", "heatpump_power", {
            "name": "Heatpump Power",
            "unique_id": f"{self.device_id}_power",
            "state_topic": "heatpump/state/par1",
            "command_topic": "heatpump/set/par1",
            "payload_on": "1", "payload_off": "0",
            "state_on": "1", "state_off": "0",
            "availability_topic": self.avail_topic
        })

        # Mode select (par2)
        self._pub_disc("select", "heatpump_mode", {
            "name": "Heatpump Mode",
            "unique_id": f"{self.device_id}_mode",
            "state_topic": "heatpump/state/par2",
            "command_topic": "heatpump/set/par2",
            "options": ["Cooling", "DHW", "Heating"],
            "command_template": "{% if value == 'Heating' %}2{% elif value == 'DHW' %}1{% else %}0{% endif %}",
            "availability_topic": self.avail_topic
        })

        # Numbers helper
        def num(uid, name, par, vmin, vmax, step, unit):
            self._pub_disc("number", uid, {
                "name": name,
                "unique_id": f"{self.device_id}_{uid}",
                "state_topic": f"heatpump/state/{par}",
                "command_topic": f"heatpump/set/{par}",
                "min": vmin, "max": vmax, "step": step,
                "unit_of_measurement": unit,
                "availability_topic": self.avail_topic
            })

        # Setpoints & deltas (control)
        num("heating_temp", "Heating Temperature", "par62", 20, 60, 1, "°C")
        num("cooling_temp", "Cooling Temperature", "par95", 10, 30, 1, "°C")
        num("dhw_temp",     "DHW Temperature",     "par42", 30, 70, 1, "°C")
        num("heating_delta_t", "Heating Delta T",   "par63", 1, 10, 1, "K")
        num("cooling_delta_t", "Cooling Delta T",   "par96", 1, 10, 1, "K")

        # Low noise (par17)
        self._pub_disc("switch", "low_noise_mode", {
            "name": "Low Noise Mode",
            "unique_id": f"{self.device_id}_low_noise_mode_control",
            "state_topic": "heatpump/state/par17",
            "command_topic": "heatpump/set/par17",
            "payload_on": "1", "payload_off": "0",
            "state_on": "1", "state_off": "0",
            "availability_topic": self.avail_topic
        })

        # Heating curve points (par85–94) – control
        for i in range(1, 6):
            # Ambient
            self._pub_disc("number", f"heating_curve_t{i}", {
                "name": f"Heating Curve Ambient Temp {i}",
                "unique_id": f"{self.device_id}_curve_t{i}",
                "state_topic": f"heatpump/state/par{84+i}",
                "command_topic": f"heatpump/set/par{84+i}",
                "min": -20, "max": 20, "step": 1, "unit_of_measurement": "°C",
                "availability_topic": self.avail_topic
            })
            # Water
            self._pub_disc("number", f"heating_curve_wt{i}", {
                "name": f"Heating Curve Water Temp {i}",
                "unique_id": f"{self.device_id}_curve_wt{i}",
                "state_topic": f"heatpump/state/par{85+i}",
                "command_topic": f"heatpump/set/par{85+i}",
                "min": 20, "max": 70, "step": 1, "unit_of_measurement": "°C",
                "availability_topic": self.avail_topic
            })

    def _publish_discovery_sensors(self):
        device = self._device_info()

        def sensor_cfg(sid, name, unit=None, dclass=None, sclass=None):
            payload = {
                "name": name,
                "state_topic": f"{self.base_sensor_prefix}/{sid}/state",
                "availability_topic": self.avail_topic,
                "device": device,
                "unique_id": f"{self.device_id}_{sid}"
            }
            if unit:   payload["unit_of_measurement"] = unit
            if dclass: payload["device_class"] = dclass
            if sclass: payload["state_class"]  = sclass
            self._pub(f"{self.base_sensor_prefix}/{sid}/config", json.dumps(payload), retain=True)

        def bin_cfg(sid, name, dclass, pon="true", poff="false"):
            payload = {
                "name": name,
                "device_class": dclass,
                "state_topic": f"{self.base_sensor_prefix}/{sid}/state",
                "availability_topic": self.avail_topic,
                "payload_on": pon, "payload_off": poff,
                "device": device,
                "unique_id": f"{self.device_id}_{sid}_binary"
            }
            self._pub(f"homeassistant/binary_sensor/{self.device_id}/{sid}/config", json.dumps(payload), retain=True)

        # Temperatures
        temp_sensors = {
            'outdoor_temp': 'Outdoor Temperature',
            'dhw_temp': 'DHW Temperature',
            'cooling_water_temp': 'Cooling Water Temperature',
            'outlet_temp': 'Outlet Temperature',
            'inlet_temp': 'Inlet Temperature',
            'room_temp': 'Room Temperature',
            'outdoor_ambient_2': 'Outdoor Ambient 2',
            'outdoor_coil_temp': 'Outdoor Coil Temperature',
            'gas_discharge_temp': 'Gas Discharge Temperature',
            'gas_suction_temp': 'Gas Suction Temperature',
        }
        for sid, name in temp_sensors.items():
            sensor_cfg(sid, name, "°C", "temperature", "measurement")

        # Electrical
        sensor_cfg('voltage', "Voltage", "V", "voltage", "measurement")
        sensor_cfg('current', "Current", "A", "current", "measurement")
        sensor_cfg('compressor_freq_limit', "Compressor Frequency Limit", "Hz", None, "measurement")
        sensor_cfg('compressor_freq', "Compressor Frequency", "Hz", None, "measurement")

        # Pressure
        sensor_cfg('low_pressure', "Low Pressure", "bar", None, "measurement")
        sensor_cfg('high_pressure', "High Pressure", "bar", None, "measurement")

        # Set temps (01B3 only)
        sensor_cfg('dhw_set_temp', "DHW Set Temperature", "°C", "temperature", "measurement")
        sensor_cfg('heating_set_temp', "Heating Set Temperature", "°C", "temperature", "measurement")
        sensor_cfg('cooling_set_temp', "Cooling Set Temperature", "°C", "temperature", "measurement")

        # Deltas (01B3 only)
        sensor_cfg('dhw_delta_temp', "DHW Delta Temperature", "°C", "temperature", "measurement")
        sensor_cfg('heating_delta_temp', "Heating Delta Temperature", "°C", "temperature", "measurement")
        sensor_cfg('cooling_delta_temp', "Cooling Delta Temperature", "°C", "temperature", "measurement")
        sensor_cfg('delta_t_compressor_speed', "Delta T Compressor Speed", "°C", "temperature", "measurement")

        # Heating curve (01B3 only)
        curve = {
            'heating_curve_ambient_temp_1': "Heating Curve Ambient Temp 1",
            'heating_curve_water_temp_1'  : "Heating Curve Water Temp 1",
            'heating_curve_ambient_temp_2': "Heating Curve Ambient Temp 2",
            'heating_curve_water_temp_2'  : "Heating Curve Water Temp 2",
            'heating_curve_ambient_temp_3': "Heating Curve Ambient Temp 3",
            'heating_curve_water_temp_3'  : "Heating Curve Water Temp 3",
            'heating_curve_ambient_temp_4': "Heating Curve Ambient Temp 4",
            'heating_curve_water_temp_4'  : "Heating Curve Water Temp 4",
        }
        for sid, name in curve.items():
            sensor_cfg(sid, name, "°C", "temperature", "measurement")

        # Priority (01B3 only)
        sensor_cfg('shifting_priority_ambient_start_temp', "Priority Ambient Start Temp", "°C", "temperature", "measurement")
        sensor_cfg('shifting_priority_heating_delta_temp', "Priority Heating Delta Temp", "°C", "temperature", "measurement")
        sensor_cfg('shifting_priority_dhw_min_time', "DHW Minimum Working Time", "min", None, "measurement")
        sensor_cfg('priority_heating_working_time', "Heating Working Time", "min", None, "measurement")

        # Binary sensors (0143)
        bin_cfg('dhw_state', "DHW Working State", "heat")
        bin_cfg('heating_state', "Heating Working State", "heat")
        bin_cfg('cooling_state', "Cooling Working State", "cold")
        bin_cfg('defrost_state', "Defrost State", "running")
        # Binary from 01B3
        bin_cfg('unit_on_off', "Unit On/Off", "power", "1", "0")
        bin_cfg('low_noise_mode', "Low Noise Mode", "battery", "1", "0")
        bin_cfg('heating_curve_enabled', "Heating Curve Enabled", None, "1", "0")

    #
    # ---------------------- Socket reader ----------------------
    #
    def _socket_loop(self):
        backoff = 2
        while not self._stop_event.is_set():
            s = None
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(30)
                s.connect((self.hp_ip, self.hp_port))
                self._pub(self.avail_topic, "online", retain=True)
                self.log("Socket connected, monitoring packets...", level="INFO")
                backoff = 2

                while not self._stop_event.is_set():
                    data = s.recv(1024)
                    if not data:
                        raise ConnectionError("socket recv returned no data")
                    if len(data) < 13:
                        continue
                    cmd = data[12]
                    parameters = data[13:]

                    if cmd == 0x01:
                        self._handle_0143(parameters)
                    elif cmd == 0x02:
                        self._handle_01B3(parameters)
                    else:
                        # 0x05 appears benign; keep quiet unless debug
                        if self.debug_enabled or cmd not in (0x05,):
                            self.log(f"Unknown packet: 0x{cmd:02X}", level="DEBUG")

            except Exception as e:
                self._pub(self.avail_topic, "offline", retain=True)
                self.log(f"Socket error: {e}", level="WARNING")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)  # exponential backoff up to 60s
            finally:
                if s:
                    try:
                        s.close()
                    except Exception:
                        pass

    #
    # ---------------------- Packet decoders ----------------------
    #
    def _f32(self, b, off):
        try:
            if off + 4 <= len(b):
                return struct.unpack("<f", b[off:off+4])[0]
        except Exception:
            pass
        return None

    def _u8(self, b, off):
        try:
            if off < len(b):
                return b[off]
        except Exception:
            pass
        return None

    def _handle_0143(self, p):
        # Temps
        for name in ("outdoor_temp","dhw_temp","cooling_water_temp","outlet_temp","inlet_temp",
                     "room_temp","outdoor_ambient_2","outdoor_coil_temp","gas_discharge_temp","gas_suction_temp"):
            off = self.OFF[name]
            v = self._f32(p, off)
            if v is not None:
                self._state(name, v)

        # Electrical
        for name in ("voltage","current","compressor_freq","compressor_freq_limit"):
            v = self._f32(p, self.OFF[name])
            if v is not None:
                self._state(name, v)

        # Pressure
        for name in ("low_pressure","high_pressure"):
            v = self._f32(p, self.OFF[name])
            if v is not None:
                self._state(name, v)

        # Binary flags read as float(1.0/0.0)
        flags = (("dhw_state","heat"),("heating_state","heat"),
                 ("cooling_state","cold"),("defrost_state","running"))
        for name,_dc in flags:
            v = self._f32(p, self.OFF[name])
            if v is not None:
                self._state(name, "true" if v == 1.0 else "false")

        # Outdoor unit mode as byte
        unit_mode = self._u8(p, self.OFF['outdoor_unit_mode'])
        if unit_mode is not None:
            self._state('outdoor_unit_mode', unit_mode)

    def _handle_01B3(self, p):
        # Set temperatures
        for name in ("dhw_set_temp","heating_set_temp","cooling_set_temp"):
            v = self._f32(p, self.OFF[name])
            if v is not None:
                self._state(name, v)

        # Unit status
        u_on = self._f32(p, self.OFF['unit_on_off'])
        if u_on is not None:
            self._state('unit_on_off', 1 if u_on == 1.0 else 0)

        mode = self._f32(p, self.OFF['working_mode'])
        if mode is not None:
            self._state('working_mode', int(mode))

        low_noise = self._f32(p, self.OFF['low_noise_mode'])
        if low_noise is not None:
            self._state('low_noise_mode', 1 if low_noise == 1.0 else 0)

        hc_enabled = self._f32(p, self.OFF['heating_curve_enabled'])
        if hc_enabled is not None:
            self._state('heating_curve_enabled', 1 if hc_enabled == 1.0 else 0)

        # Deltas
        pairs = (("delta_t_compressor_speed","delta_t_compressor_speed"),
                 ("heating_delta_t","heating_delta_temp"),
                 ("dhw_delta_t","dhw_delta_temp"),
                 ("cooling_delta_t","cooling_delta_temp"))
        for raw, alias in pairs:
            v = self._f32(p, self.OFF[raw])
            if v is not None:
                self._state(raw, v)
                if alias != raw:
                    self._state(alias, v)

        # Heating curve (first 4 points)
        curve = ("heating_curve_ambient_temp_1","heating_curve_water_temp_1",
                 "heating_curve_ambient_temp_2","heating_curve_water_temp_2",
                 "heating_curve_ambient_temp_3","heating_curve_water_temp_3",
                 "heating_curve_ambient_temp_4","heating_curve_water_temp_4")
        for name in curve:
            v = self._f32(p, self.OFF[name])
            if v is not None:
                self._state(name, v)

        # Priority (floats)
        v = self._f32(p, self.OFF['dhw_priority_min_time'])
        if v is not None:
            self._state('dhw_priority_min_time', v)
            self._state('shifting_priority_dhw_min_time', v)

        v = self._f32(p, self.OFF['priority_ambient_start_temp'])
        if v is not None:
            self._state('priority_ambient_start_temp', v)
            self._state('shifting_priority_ambient_start_temp', v)

        v = self._f32(p, self.OFF['priority_heating_delta_t'])
        if v is not None:
            self._state('priority_heating_delta_t', v)
            self._state('shifting_priority_heating_delta_temp', v)

        v = self._f32(p, self.OFF['priority_heating_working_time'])
        if v is not None:
            self._state('priority_heating_working_time', v)
            self._state('shifting_priority_heating_working_time', v)

    #
    # ---------------------- State helper ----------------------
    #
    def _state(self, sid, value):
        topic = f"{self.base_sensor_prefix}/{sid}/state"
        self._pub(topic, str(value))
        # keep availability fresh
        self._pub(self.avail_topic, "online", retain=True)

    #
    # ---------------------- Utils ----------------------
    #
    def _parse_cookie(self, cookie_str):
        d = {}
        if not cookie_str:
            return d
        # Split by semicolon, trim, accept key=value
        for kv in cookie_str.split(";"):
            kv = kv.strip()
            if not kv or "=" not in kv:
                continue
            k, v = kv.split("=", 1)
            d[k.strip()] = v.strip()
        return d
