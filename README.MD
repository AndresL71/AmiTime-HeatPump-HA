Home Assistant Heat Pump Bridge (AppDaemon)

An AppDaemon app that:

Reads local TCP packets from an AmiTime/compatible Wi-Fi adapter (0x0143 realtime & 0x01B3 setpoints).

Publishes MQTT Discovery sensors & controls to Home Assistant.

Sends write commands to the vendor cloud API (optional) using your session cookie.

Calculates thermal power and COP (heating/cooling) from measured temps, estimated/real electrical power, and configurable water flow.

Tested on Home Assistant OS (Supervised) with the AppDaemon add-on.

⚠️ Disclaimer
You are responsible for your own account/cookie usage and equipment. Use at your own risk. This project is not affiliated with any manufacturer.

Features

MQTT Discovery for:

Temperatures, pressures, electrical readings, compressor frequency

Binary states (heating/cooling/DHW/defrost)

Heating curve points

Working mode + derived working_state (heating / cooling / dhw / idle)

Controls (MQTT → cloud API):

Power (par1), Mode (par2), setpoints, delta-T, low-noise, heating curve points

COP & power:

electrical_power_w (from V × A × PF or external sensor later)

thermal_power_heating_w, thermal_power_cooling_w

cop_heating, cop_cooling

Resilient socket loop with backoff; retained availability topic.

Requirements

Home Assistant with the AppDaemon add-on

MQTT broker (e.g., Mosquitto)

Network access to the heat pump adapter (default IP/port are configurable)

A valid raw session cookie string for the cloud website if you want remote writes

Install

Copy files (recommended structure):

Put the contents of this repo into your HA config. If you cloned to your PC first, copy appdaemon/* into the HA /config share so that:






For AmiTime Heatpump HeatLITE, Monoblock, R32
such as: PAVH15/19 -- mutiple vendors, HeatThermo Hoffmann, Recal --  

reading most sensors, and set temperatures locally, directly from the Pumps Wifi using the serial port provided in the usr-c210 configuration page as socket A, TCP server.
Without having to go to  www.myheatpump.com.

# heatpump_bridge.py
reads valued fron local usr-c210 in controller, and writes to myheatpump.com using API. You need to enable Remember Me en the webpage and retrive raw cookien in your browser(F12/network POST)

Configure apps.yaml and secrets.yaml and use it in AppDaemon in HomeAssistant

#  heatpump.py


# modify in script :

your MAC address

Your usr-c210 ip

your usr-c210 open port (TCP server)

MQTT address and name/password


# Configuration
	HEATPUMP_IP = "10.0.0.73"
	HEATPUMP_PORT = 8899
	HEATPUMP_MAC = "xx xx xx xx xx xx"

# MQTT Configuration
	MQTT_BROKER = "localhost"
	MQTT_PORT = 1883
	MQTT_USER = "addons"
	MQTT_PASSWORD = ""

#Offsets
	
01b3

	Unit ON OFF：at 2 (1=on 0=off)
	Working Mode: at 6 -- (1=DHW, 2=heating, 3=cooling)
	Delta T to start compressor speed regulation：at 18
	Low noise mode ON/OFF：at 66 (1=on 0=off)

	Heating set Temp: 246 
	Delta of Heating: 250

	Heating Curve: 330 (1=on 0=off)
	Heating curve ambient temp. 1 at 338
	Heating curve water temp. 1 at 342
	Heating curve ambient temp. 2 at 346
	Heating curve water temp. 2 at 350
	Heating curve ambient temp. 3 at 354
	Heating curve water temp. 3 at 358
	Heating curve ambient temp. 3 at 362
	Heating curve water temp. 3 at 366
	Heating curve ambient temp. 2 at 346
	Heating curve water temp. 2 at 350

	DHW set temp.：at 166
	Delta T of DHW：at 170
	Shifting priority DHW Min. working time：190
	Shifting priority ambient start temp.：at 306
	Shifting priority delta T of heating：314
	Shifting priority heating working time：318

	Cooling set temp.：at 378
	Delta T of cooling：at 382

Package 0143

	Outdoor ambient temp. (Ta)：10
	DHW Temp.(TW)：14
	Cooling water temp：18
	Water outlet temp.：22
	Water inlet temp.：26
	room temperature：54

	AC input voltage：214
	AC input current：218
	Compressor frequency limit at current time：222
	Compressor frequency：226
	Low pressure：278
	High pressure：282
	Outdoor Ambient Temp (2da):254
	Outdoor Coil temp.: 258
	Outdoor gas discharge temp：262
	Outdoor gas suction temp.266

	Outdoor unit operating mode: 210
	DHW working state：174 (on/off)  
	Heating working state：178 (on/off) 
	Cooling working state：182 (on/off) ??
	Defrosting State : 286 (on/off) ??



