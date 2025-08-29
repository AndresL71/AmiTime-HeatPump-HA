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



