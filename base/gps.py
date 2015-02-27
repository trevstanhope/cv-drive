import gps # GPS
"""
gps.py
"""

import thread # GPS

class GPS:
	
	def __init__(self):
        if self.GPS_ENABLED:
            try:
                self.gpsd = gps.gps()
                self.gpsd.stream(gps.WATCH_ENABLE)
                thread.start_new_thread(self.update_gps, ())
            except Exception as err:
                print('ERROR in __init__(): GPS not available! %s' % str(err))
                self.latitude = 0
                self.longitude = 0
                self.speed = 0
        else:
            print('\tWARNING: GPS Disabled')
            self.latitude = 0
            self.longitude = 0
            self.speed = 0

    ## Update GPS
    """
    1. Get the most recent GPS data
    2. Set global variables for lat, long and speed
    """
    def update_gps(self):  
        while True:
            self.gpsd.next()
            self.latitude = self.gpsd.fix.latitude
            self.longitude = self.gpsd.fix.longitude
            self.speed = self.gpsd.fix.speed
