"""
CV Drive (working  title)
McGill University, Department of Bioresource Engineering
"""

__author__ = 'Trevor Stanhope'
__version__ = '0.0.1'
__license__ = 'All Rights Reserved'

## Libraries
from base import control, gps, db, cvm
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
        self.logger = db.Logger()
        self.row_finder = cvm.RowFinder()
    
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
            self.row_finder.close()
        except Exception as error:
            print('ERROR in close()\t%s' % str(error))
        
    """
    Function for Run-time loop
    """     
    def run(self):
        while True:
            try:
                cams = range(1)
                imgs = [self.row_finder.capture_image(c) for c in cams]
                masks = [self.row_finder.plant_filter(i) for i in imgs]
                offsets = [self.row_finder.find_offset(m) for m in masks]
                for m in imgs:
                    self.row_finder.display(m)
            except KeyboardInterrupt as error:
                self.close()
            except Exception as error:
                print str(error)
    
## Main
if __name__ == '__main__':
    session = Vehicle(CONFIG_FILE)
    session.run()
