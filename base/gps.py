import gps # GPS
"""
gps.py
"""

import thread # GPS

class GPS:

    def __init__(self):
        try:
            self.gpsd = gps.gps()
            self.gpsd.stream(gps.WATCH_ENABLE)
            thread.start_new_thread(self.update_gps, ())
        except TypeError as err:
            print('ERROR in __init__(): GPS failed to initialize.')
        except Exception as err:
            print('ERROR in __init__(): GPS not available! %s' % str(err))
            self.latitude = 0
            self.longitude = 0
            self.speed = 0

    def update_gps(self):
        while True:
            self.gpsd.next()
            self.latitude = self.gpsd.fix.latitude
            self.longitude = self.gpsd.fix.longitude
            self.speed = self.gpsd.fix.speed
