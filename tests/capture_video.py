"""
Capture video stream and generate text log of exact frame time
Trevor Stanhope
"""

import cv, cv2
import numpy as np
import time
from datetime import datetime
import os

# Constants
index = 0
file_dir = "results"
test_name = ""
vid_type = ".avi"
vid_date = datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")
vid_file = "%s_%s%s" % (vid_date, test_name, vid_type)
vid_path = os.path.join(file_dir, vid_file)
log_type = '.csv'
log_file = "%s %s%s" % (vid_date, test_name, log_type)
log_path = os.path.join(file_dir, log_file)

# Get FPS
# Function to read a video camera and estimate the frames-per-second (fps)
def get_fps(camera, frames=10):
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
def get_frame_size(camera):
    (s, bgr) = camera.read()
    if s:
        (h, w, b) = bgr.shape
        frame_size = (w, h)
        return frame_size
    
# Initialize Video Capture
camera = cv2.VideoCapture(index)
fps = get_fps(camera)
frame_size = get_frame_size(camera)
print fps
print frame_size

# Initialize Video Writer
vid_writer = cv2.VideoWriter(vid_path, cv.CV_FOURCC('M', 'J', 'P', 'G'), fps, frame_size, True)

# Loop until keyboard interrupt
try:
    with open(log_path, 'w') as csvfile:
        while vid_writer.isOpened():
            (s, bgr) = camera.read()
            if s:
                t = time.time()
                csvfile.write(str(t) + '\n')
                vid_writer.write(bgr)
                cv2.imshow('', bgr)
                cv2.waitKey(5)
except Exception as e:
    print str(e)
