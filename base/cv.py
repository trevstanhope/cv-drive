"""
cv.py
"""

#import cv2, cv

class Cam:
	
	def __init__(self):
        if self.VERBOSE: print('[Initialing Cameras] %s' % datetime.strftime(datetime.now(), self.TIME_FORMAT))
        print('\tImage Width: %d px' % self.PIXEL_WIDTH)
        print('\tImage Height: %d px' % self.PIXEL_HEIGHT)
        print('\tCamera Height: %d cm' % self.CAMERA_HEIGHT)
        print('\tCamera FOV: %f rad' % self.CAMERA_FOV)
        self.PIXEL_CENTER = self.PIXEL_WIDTH / 2
        if self.VERBOSE: print('\tImage Center: %d px' % self.PIXEL_CENTER)
        self.GROUND_WIDTH = 2 * self.CAMERA_HEIGHT * numpy.tan(self.CAMERA_FOV / 2.0)
        print('\tGround Width: %d cm' % self.GROUND_WIDTH)
        print('\tBrush Range: +/- %d cm' % self.BRUSH_RANGE)
        self.PIXEL_PER_CM = self.PIXEL_WIDTH / self.GROUND_WIDTH
        print('\tPixel-per-cm: %d px/cm' % self.PIXEL_PER_CM)
        self.PIXEL_RANGE = int(self.PIXEL_PER_CM * self.BRUSH_RANGE)
        print('\tPixel Range: %d' % self.PIXEL_RANGE)
        self.PIXEL_MIN = self.PIXEL_CENTER - self.PIXEL_RANGE
        self.PIXEL_MAX = self.PIXEL_CENTER + self.PIXEL_RANGE
        self.PWM_PER_PIXEL = 255 / (2 * self.PIXEL_RANGE)
        self.PWM_CENTER = 255 / 2
        print('\tPWM-per-pixel: %f pwm/px' % self.PWM_PER_PIXEL)
        time.sleep(1)
        self.cameras = []
        for i in self.CAMERAS:
            if self.VERBOSE: print('\tInitializing Camera: %d' % i)
            cam = cv2.VideoCapture(i)
            cam.set(cv.CV_CAP_PROP_FRAME_WIDTH, self.PIXEL_WIDTH)
            cam.set(cv.CV_CAP_PROP_FRAME_HEIGHT, self.PIXEL_HEIGHT)
            self.cameras.append(cam)
		
    ## Capture Images
    """
    1. Attempt to capture an image
    2. Repeat for each capture interface
    """
    def capture_images(self):
        if self.VERBOSE: print('[Capturing Images] %s' % datetime.strftime(datetime.now(), self.TIME_FORMAT))
        images = []
        for cam in self.cameras:
            if self.VERBOSE: print('\tCamera ID: %s' % str(cam))
            (s, bgr) = cam.read() 
            if s:
                images.append(bgr)
        if self.VERBOSE: print('\tImages captured: %d' % len(images))
        return images

    ## Green Filter
    """
    1. RBG --> HSV
    2. Set minimum saturation equal to the mean saturation
    3. Set minimum value equal to the mean value
    4. Take hues within range from green-yellow to green-blue
    """
    def plant_filter(self, images):
        if self.VERBOSE: print('[Filtering for Plants] %s' % datetime.strftime(datetime.now(), self.TIME_FORMAT))
        masks = []
        for bgr in images:
            try:
                hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
                hue_min = self.HUE_MIN # yellowish
                hue_max = self.HUE_MAX # bluish
                sat_min = hsv[:,:,1].mean() # cutoff for how saturated the color must be
                sat_max = self.SAT_MAX
                val_min = hsv[:,:,2].mean()
                val_max = self.VAL_MAX
                threshold_min = numpy.array([hue_min, sat_min, val_min], numpy.uint8)
                threshold_max = numpy.array([hue_max, sat_max, val_max], numpy.uint8)
                mask = cv2.inRange(hsv, threshold_min, threshold_max)
                masks.append(mask) 
            except Exception as error:
                print('\tERROR in plant_filter(): %s' % str(error))        
        if self.VERBOSE: print('\tNumber of Masks: %d mask(s) ' % len(masks))
        return masks
        
    ## Find Offsets
    """
    1. Calculates the column summation of the mask
    2. Calculates the 95th percentile threshold of the column sum array
    3. Finds indicies which are greater than or equal to the threshold
    4. Finds the median of this array of indices
    5. Repeat for each mask
    """
    def find_offsets(self, masks):
        if self.VERBOSE: print('[Finding Offsets] %s' % datetime.strftime(datetime.now(), self.TIME_FORMAT))
        offsets = []
        for mask in masks:
            try:
                column_sum = mask.sum(axis=0) # vertical summation
                threshold = numpy.percentile(column_sum, self.THRESHOLD_PERCENTILE)
                probable = numpy.nonzero(column_sum >= threshold) # returns 1 length tuple
                num_probable = len(probable[0])
                centroid = int(numpy.median(probable[0])) - self.PIXEL_CENTER
                offsets.append(centroid)
            except Exception as error:
                print('\tERROR in find_indices(): %s' % str(error))
        if self.VERBOSE: print('\tDetected Offsets: %s' % str(offsets))
        return offsets
        
    ## Best guess for row based on calculated offsets of multiple cameras
    """
    1. If outside bounds, default to edges
    2. If inside, use mean of detected indices from both cameras
    """
    def estimate_row(self, offsets):
        if self.VERBOSE: print('[Making Best Guess of Crop Row] %s' % datetime.strftime(datetime.now(), self.TIME_FORMAT))
        try:
            estimated =  int(numpy.mean(offsets))
        except Exception as error:
            print('\tERROR in estimate_row(): %s' % str(error))
            estimated = 0
        print('\tEstimated Offset: %s' % str(estimated))
        return estimated
