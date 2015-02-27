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
	
    def __init__(self, config_file):

        # Load Config
        print('\tLoading config file: %s' % config_file)
        self.config = json.loads(open(config_file).read())
        for key in self.config:
            try:
                getattr(self, key)
            except AttributeError as error:
                setattr(self, key, self.config[key])

        # Display
        if self.VERBOSE: print('[Initializing Display] %s' % datetime.strftime(datetime.now(), self.TIME_FORMAT))
        if self.DISPLAY_ON:
            thread.start_new_thread(self.update_display, ())
                
    ## Displays 
    """
    1. Draw lines on RGB images
    2. Draw lines on EGI images (the masks)
    3. Output GUI display
    """
    def update_display(self):
		while True:
            if self.VERBOSE: print('[Displaying Images] %s' % datetime.strftime(datetime.now(), self.TIME_FORMAT))
            try:
                average = self.average + self.PIXEL_CENTER
                pwm = self.pwm
                masks = self.masks
                images = self.images
                output_images = []
                for img,mask in zip(images, masks):
                    cv2.line(img, (self.PIXEL_MIN, 0), (self.PIXEL_MIN, self.PIXEL_HEIGHT), (0,0,255), 1)
                    cv2.line(img, (self.PIXEL_MAX, 0), (self.PIXEL_MAX, self.PIXEL_HEIGHT), (0,0,255), 1)
                    cv2.line(img, (average, 0), (average, self.PIXEL_HEIGHT), (0,255,0), 2)
                    cv2.line(img, (self.PIXEL_CENTER, 0), (self.PIXEL_CENTER, self.PIXEL_HEIGHT), (255,255,255), 1)
                    output_images.append(numpy.vstack([img, numpy.zeros((20, self.PIXEL_WIDTH, 3), numpy.uint8)]))
                output_small = numpy.hstack(output_images)
                output_large = cv2.resize(output_small, (1024, 768))
                if average - self.PIXEL_CENTER >= 0:
                    average_str = str("+%2.2f cm" % ((average - self.PIXEL_CENTER) / float(self.PIXEL_PER_CM)))
                elif average - self.PIXEL_CENTER < 0:
                    average_str = str("%2.2f cm" % ((average - self.PIXEL_CENTER) / float(self.PIXEL_PER_CM)))
                cv2.putText(output_large, average_str, (340,735), cv2.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 5)
                cv2.namedWindow('AutoTill', cv2.WINDOW_NORMAL)
                if self.FULLSCREEN: cv2.setWindowProperty('AutoTill', cv2.WND_PROP_FULLSCREEN, cv2.cv.CV_WINDOW_FULLSCREEN)
                cv2.imshow('AutoTill', output_large)
                if cv2.waitKey(5) == 3:
                    pass
            except Exception as error:
                print('\tERROR in display(): %s' % str(error))
    
    ## Close
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
    session = Cultivator(CONFIG_FILE)
    session.run()
