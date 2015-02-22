import cv, cv2
from matplotlib import pyplot as plt
import numpy
CAMERA_INDEX = 0
HUE_MIN = 30
HUE_MAX = 120
PIXEL_WIDTH = 640
PIXEL_HEIGHT = 480
THRESHOLD_PERCENTILE = 95
camera = cv2.VideoCapture(CAMERA_INDEX)
camera.set(cv.CV_CAP_PROP_FRAME_WIDTH, PIXEL_WIDTH)
camera.set(cv.CV_CAP_PROP_FRAME_HEIGHT, PIXEL_HEIGHT)
while True:
    try:
        (s, bgr) = camera.read()
        if s:
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            hue_min = HUE_MIN
            hue_max = HUE_MAX
            sat_min = hsv[:,:,1].mean()
            sat_max = 255
            val_min = hsv[:,:,2].mean()
            val_max = 255
            threshold_min = numpy.array([hue_min, sat_min, val_min], numpy.uint8)
            threshold_max = numpy.array([hue_max, sat_max, val_max], numpy.uint8)
            mask = cv2.inRange(hsv, threshold_min, threshold_max)
            column_sum = mask.sum(axis=0) # vertical summation
            threshold = numpy.percentile(column_sum, THRESHOLD_PERCENTILE)
            probable = numpy.nonzero(column_sum >= threshold) # returns 1 length tuble
            num_probable = len(probable[0])
            centroid = int(numpy.median(probable[0]))
            egi = numpy.dstack((mask, mask, mask))
            bgr[:,centroid,:] = 255
            egi[:,centroid,:] = 255
            hsv[:,centroid,:] = 255
            output = numpy.hstack((bgr, hsv, egi))
            cv2.imshow('', output)
            if cv2.waitKey(5) == 27:
                pass
            print(centroid)
    except Exception as error:
        print('ERROR: %s' % str(error))
        break
