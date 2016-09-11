import sqlite3

sqlname = "/home/pi/sensors/internetofshed.db"
	


#  CREATE TABLE sensordata (id integer primary key autoincrement, timet datetime default current_timestamp, door int, rooflight int, temperature float, outdoor float, humidity int, lightlevel int);
def cleanDB():
	conn = sqlite3.connect(sqlname)
	cur = conn.cursor()
	cur.execute("delete from sensordata where timet  < datetime('now','-7 day')")
	conn.commit()
	cur.close() 
	conn.close()
	return


# Delete sensor data more than a week old (Raspi has limited memory!)
cleanDB()


