For AmiTime Heatpump, Monoblock, R32
such as: PAVH15/19 -- mutiple vendors, HeatThermo Hoffmann, Recal --  

reading most sensors, and set temperatures locally, directly from the Pumps Wifi using the serial port provided in the usr-c210 configuration page as socket A, TCP server.
Without having to go to  www.myheatpump.com.
Not able to write values still

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
	
	Offsets 01b3

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


