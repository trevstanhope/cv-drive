"""
Computer Vision Module
"""

import cv2, cv
from datetime import datetime
import numpy as np

class RowFinder:

    def __init__(self, cams=1, verbose=True, width=640, height=480, depth=1.0, fov=0.7, date_format="%Y-%m-%d %H:%M:%S"):
        self.DATE_FORMAT = date_format
        self.VERBOSE = verbose
        self.NUM_CAMERAS = cams
        self.CAMERA_WIDTH = width
        self.CAMERA_HEIGHT = height
        self.CAMERA_DEPTH = depth
        self.CAMERA_FOV = fov
        self.CAMERA_CENTER = self.CAMERA_WIDTH / 2
        self.GROUND_WIDTH = 2 * self.CAMERA_DEPTH * np.tan(self.CAMERA_FOV / 2.0)
        self.PIXEL_PER_CM = self.CAMERA_WIDTH / self.GROUND_WIDTH
        if self.VERBOSE:
            print('[Initialing Cameras] %s' % datetime.strftime(datetime.now(), self.DATE_FORMAT))
            print('\tImage Width: %d px' % self.CAMERA_WIDTH)
            print('\tImage Height: %d px' % self.CAMERA_HEIGHT)
            print('\tCamera Height: %d cm' % self.CAMERA_DEPTH)
            print('\tCamera FOV: %f rad' % self.CAMERA_FOV)
            print('\tImage Center: %d px' % self.CAMERA_CENTER)
            print('\tGround Width: %d cm' % self.GROUND_WIDTH)
            print('\tPixel-per-cm: %d px/cm' % self.PIXEL_PER_CM)
        self.cameras = []
        for i in range(self.NUM_CAMERAS):
            if self.VERBOSE: print('\tInitializing Camera: %d' % i)
            cam = cv2.VideoCapture(i)
            print cam
            print i, cv.CV_CAP_PROP_FRAME_WIDTH, cv.CV_CAP_PROP_FRAME_HEIGHT
            cam.set(cv.CV_CAP_PROP_FRAME_WIDTH, self.CAMERA_WIDTH)
            cam.set(cv.CV_CAP_PROP_FRAME_HEIGHT, self.CAMERA_HEIGHT)
            self.cameras.append(cam)
        
    ## Capture Images
    """
    1. Attempt to capture an image
    2. Repeat for each capture interface
    """
    def capture_image(self, cam_num):
        if self.VERBOSE: print('[Capturing Images] %s' % datetime.strftime(datetime.now(), self.DATE_FORMAT))
        try:
            cam = self.cameras[cam_num]
            (s, bgr) = cam.read() 
            if s:
                return bgr
        except Exception as error:
            print str(error)

    ## Green Filter
    """
    1. RBG --> HSV
    2. Set minimum saturation equal to the mean saturation
    3. Set minimum value equal to the mean value
    4. Take hues within range from green-yellow to green-blue
    """
    def plant_filter(self, bgr, hue_min=20, hue_max=60, sat_max=255, val_max=0):
        if self.VERBOSE: print('[Filtering for Plants] %s' % datetime.strftime(datetime.now(), self.DATE_FORMAT))
        try:
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            sat_min = hsv[:,:,1].mean() # cutoff for how saturated the color must be
            val_min = hsv[:,:,2].mean()
            threshold_min = np.array([hue_min, sat_min, val_min], np.uint8)
            threshold_max = np.array([hue_max, sat_max, val_max], np.uint8)
            mask = cv2.inRange(hsv, threshold_min, threshold_max)
            return mask
        except Exception as error:
            print('\tERROR in plant_filter(): %s' % str(error))        
        
    ## Find Offset
    """
    1. Calculates the column summation of the mask
    2. Calculates the 95th percentile threshold of the column sum array
    3. Finds indicies which are greater than or equal to the threshold
    4. Finds the median of this array of indices
    5. Repeat for each mask
    """
    def find_offset(self, mask, threshold_percentile=0.95):
        if self.VERBOSE: print('[Finding Offsets] %s' % datetime.strftime(datetime.now(), self.DATE_FORMAT))
        try:
            if mask:
                (h, w) = mask.shape
                column_sum = mask.sum(axis=0) # vertical summation
                threshold = np.percentile(column_sum, threshold_percentile)
                probable = np.nonzero(column_sum >= threshold) # returns 1 length tuple
                num_probable = len(probable[0])
                centroid = int(np.median(probable[0])) - w / 2.0
                return centroid
        except Exception as error:
            print('\tERROR in find_indices(): %s' % str(error))
        
    ## Best guess for row based on calculated offsets of multiple cameras
    """
    1. If outside bounds, default to edges
    2. If inside, use mean of detected indices from both cameras
    """
    def estimate_row(self, offsets):
        if self.VERBOSE: print('[Making Best Guess of Crop Row] %s' % datetime.strftime(datetime.now(), self.DATE_FORMAT))
        try:
            estimated =  int(np.mean(offsets))
            return estimated
        except Exception as error:
            print('\tERROR in estimate_row(): %s' % str(error))
    
    # Display
    def display(self, img):
        if self.VERBOSE: print('[Displaying Image] %s' % datetime.strftime(datetime.now(), self.DATE_FORMAT))
        cv2.imshow('', img)
        cv2.waitKey(5)
        
    # Get FPS function to read a video camera and estimate the frames-per-second (fps)
    def get_fps(self, cam_num, frames=10):
        camera = self.cameras[cam_num]
        t_n = []
        for i in range(frames):
            (s, bgr) = camera.read()
            if s:
                t = time.time()
                t_n.append(t)
        t_i = np.array(t_n)
        t_f = np.append(t_n[1:], t_i[-1])
        dt = t_f - t_i
        fps = np.reciprocal(np.mean(dt[:-1]))
        return int(fps)

    # Get Frame Size
    def get_frame_size(self, cam_num):
        camera = self.cameras[cam_num]
        (s, bgr) = camera.read()
        if s:
            (h, w, b) = bgr.shape
            frame_size = (w, h)
            return frame_size
    
    # Close
    def close(self):
        for c in self.cameras:
            c.release()
