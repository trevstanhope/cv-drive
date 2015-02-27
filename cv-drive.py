"""
cv-drive.py
McGill University, Department of Bioresource Engineering
"""

__author__ = 'Trevor Stanhope'
__version__ = '0.0.1'
__license__ = 'All Rights Reserved'

## Libraries
from base import control, gps, db, cv
import json
import numpy # Curve
from matplotlib import pyplot as plt # Display
import time 
import sys
from datetime import datetime

## Settings file to use
try:
    CONFIG_FILE = sys.argv[1]
except Exception as err:
    CONFIG_FILE = 'settings.json'

## Class
class Vehicle:

    def __init__(self, config):
        self.config = json.loads(open(config, 'rb').read())
        self.control = control.Arduino()
        self.gps = gps.GPS()
        self.db = db.Logger()
    
    """
    Function to shutdown application safely
    1. Close windows
    2. Disable arduino
    3. Release capture interfaces 
    """
    def close(self):
        try:
            self.control.close()
        except Exception as error:
            print('\tERROR in close()\t%s' % str(error))
        try:
            self.cv.close()
        except Exception as error:
            print('ERROR in close()\t%s' % str(error))
        
    """
    Function for Run-time loop
    """     
    def run(self):
        while True:
            try:
                pass
            except KeyboardInterrupt as error:
                self.close()    
    
## Main
if __name__ == '__main__':
    session = Vehicle(CONFIG_FILE)
    session.run()
