import RPi.GPIO as GPIO
import Adafruit_DHT
import urllib2
import urllib
import json
import os
import re
import time
from smbus import SMBus
import logging
import sqlite3
import readPressure

sqlname = "/home/pi/sensors/internetofshed.db"
	

#  CREATE TABLE authentication (id integer primary key autoincrement, servicename text, auth_info text );
def readAuth():
	conn = sqlite3.connect(sqlname)
	cur = conn.cursor()
	cur.execute("select * from authentication where servicename = 'thingspeak'");
	thingspeak = cur.fetchone()
	cur.close()
	conn.close()
	return thingspeak[2] 


#  CREATE TABLE sensordata (id integer primary key autoincrement, timet datetime default current_timestamp, door int, rooflight int, temperature float, outdoor float, humidity int, lightlevel int, raining int, pressure float);
def writeDB(door,rooflight,temperature,outdoor,humidity,pressure,lightlevel,raining):
	conn = sqlite3.connect(sqlname)
	cur = conn.cursor()
	cur.execute("INSERT INTO sensordata (door,rooflight,temperature,outdoor,humidity,pressure,lightlevel,raining) VALUES (?,?,?,?,?,?,?,?)", 
		(door,rooflight,temperature,outdoor,humidity,pressure,lightLevel,raining))
	conn.commit()
	cur.close() 
	conn.close()
	return


# Check if DS18b20 temperature sensor can be seen and return its path
def sensorNameDs1820():
	name = ''
	tempSensorPath = '/sys/bus/w1/devices/'
	files = os.listdir(tempSensorPath)
	for fnm in files:
		if "28-" in fnm:
			name = tempSensorPath + fnm + "/w1_slave"
	return name


# Send data packet to thingspeak site
def sendValues(api_key,door,window,temp,humid,pressure,light,outdoor,raining):
	timeString = time.strftime("%Y-%m-%d %H:%M:%S") 
	url = 'https://api.thingspeak.com/update.json'
	status = 'Generated at: '+timeString
	data = {'field1':temp, 'field2':outdoor, 'field3':humid, 'field4':light, 'field5':door,  'field6':window, 'field7':raining, 'field8':pressure, 'api_key':api_key, 'status':status } 
	upload = json.dumps( data )
	data['api_key'] = 'XXXX'
	dump = json.dumps( data ) 
	#logger.info('Send data: '+dump)
	f = open('/tmp/lastrecord.txt','w')
	f.write(dump+'\n')
	f.close()

	request = urllib2.Request(url=url, data=upload)
	request.add_header('Content-Type', 'application/json')
 	response = urllib2.urlopen(request)
	return


# Read PCF8591 to get light value from LDR
def read_analog(i):
	global bus
	bus.write_byte(0x48,0x40+i)
	bus.read_byte(0x48)
	return bus.read_byte(0x48)	


# Read LDR and change to range 0..200 (200 = light)
def read_light():
	val = read_analog(0)
	lightLevel = 255-val
	if lightLevel>200:
		lightLevel=200
	return lightLevel
 

# Read 1-wire sensor (outdoor temp)  DS18B20
def read_temp(sensorName):
	temp = 0.0
	f = open(sensorName,'r')
	header = f.readline()	
	body = f.readline()
	f.close()

	if 'YES' in header: 
		m = re.search( '(-?\d+)$', body )
		if m:
			temp = float(m.group(1))/1000.0

	return temp


# Get API logon information
thingspeakKey = readAuth()

# Logger setup
logger = logging.getLogger('sensors')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('/var/log/sensors.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s  [%(levelname)s] %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


# Setup GPIOs for switches
GPIO.setmode(GPIO.BCM)
GPIO.setup(20,GPIO.IN)
GPIO.setup(21,GPIO.IN)
# Rain sensor (TTL)
GPIO.setup(27,GPIO.IN)

# Settings for DHT11 temp/humidty sensor
sensor = Adafruit_DHT.DHT11
DHTpin = 17

# Initialize I2C bus (for PCF8591)
bus = SMBus(1)
bus.write_byte(0x48,0)

# Initialize 1-wire
os.system('modprobe w1-gpio');
os.system('modprobe w1-therm');

# Outdoor temp
sensorName = sensorNameDs1820()
if sensorName:
	outdoor = read_temp(sensorName)
else:
	logging.error('DS18b20 not reading back correctly')
	outdoor = 0


# Read DHT11 values
humidity, temperature = Adafruit_DHT.read_retry(sensor, DHTpin)

# Read light value
lightLevel = read_light() 

# Read switches	
door =  GPIO.input(20)
rooflight = 1 - GPIO.input(21)

# Read rain sensor
rain =  GPIO.input(27)

# Read BMP 280 for atmospheric pressure
pressure = round( readPressure.readPressure(), 2 )

#print('Outdoor={0:0.1f} C'.format(outdoor))
#print('Temp={0:0.1f} C  Humidity={1:0.1f}%'.format(temperature, humidity))
#print('Light  = '+str(lightLevel))
#print("Door = "+str(door))
#print("Rooflight = "+str(rooflight))
#print("Rain = "+str(rain))

sendValues(thingspeakKey,door,rooflight,temperature,humidity,pressure,lightLevel,outdoor,rain)

writeDB(door,rooflight,temperature,outdoor,humidity,pressure,lightLevel,rain)

