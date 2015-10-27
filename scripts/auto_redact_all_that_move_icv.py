
import argparse
import datetime
import imutils
import time
import cv2
import numpy as np
import string, random
import os
# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--input", help="path to the video file")
ap.add_argument("-o", "--output", help="path to the video file")
args = vars(ap.parse_args())

camera = cv2.VideoCapture(args["input"])
frames_folder = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))
os.system('mkdir %s/' % (frames_folder))
grays = []
# initialize the first frame in the video stream
firstFrame = None
avg = None
i = 0
detections = []
number_of_detections_per_frame = []
stopped_count = 0
started_count = 0
confirmed_stopped = False
# loop over the frames of the video
while True:
    print i, confirmed_stopped
    i += 1
    # grab the current frame and initialize the occupied/unoccupied
    # text
    (grabbed, frame) = camera.read()
    text = "Unoccupied"

    # if the frame could not be grabbed, then we have reached the end
    # of the video
    if not grabbed:
        break

    # resize the frame, convert it to grayscale, and blur it
    #frame = imutils.resize(frame, width=500)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
    blurred = cv2.GaussianBlur(frame, (35, 35), 0)
    for j in range(2):
        blurred = cv2.GaussianBlur(blurred, (35, 35), 0)
    # if the first frame is None, initialize it
    grays.append(gray)
    if firstFrame is None:
        firstFrame = gray
    #    continue
    elif (i > 30 and not confirmed_stopped):
        firstFrame = grays[i - 30]

    # compute the absolute difference between the current frame and
    # first frame
    frameDelta = cv2.absdiff(firstFrame, gray)
    thresh = cv2.threshold(frameDelta, 10, 255, cv2.THRESH_BINARY)[1]

    # dilate the thresholded image to fill in holes, then find contours
    # on thresholded image
    thresh = cv2.dilate(thresh, None, iterations=10)
    (cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE)
    areas = []
    for c in cnts:
        (x, y, w, h) = cv2.boundingRect(c)
        areas.append((w*h, w, h))
        detections.append(((x, y, w, h), i))
        temp = np.zeros(frame.shape,np.uint8)
        cv2.drawContours(temp,[c],0,255,-1)
        x = np.where(temp != 0)
        frame[x[:2]] = blurred[x[:2]]
    if areas:
        largest = sorted(areas, key=lambda x: x[0], reverse=True)[0]
        print frame.shape
        if not (largest[1] > frame.shape[1]-120 or largest[2] > frame.shape[0]-120):
            stopped_count += 1
            if stopped_count == 480:
                started_count = 0
                confirmed_stopped = True
                firstFrame = saved_gray
            if stopped_count == 1:
                saved_gray = gray
        else:
            started_count += 1
            if started_count == 480:
                print 'started', largest
                stopped_count = 0
                confirmed_stopped = False


    filename = '%08d.jpg' % (i)
    if confirmed_stopped:
        cv2.imwrite('%s/%s' % (frames_folder, filename), frame)
    else:
        cv2.imwrite('%s/%s' % (frames_folder, filename), blurred)
ffmpeg_cmd = '%sffmpeg -i %s/%%08d.jpg -y -r 24 -vcodec libx264 -preset ultrafast -b:a 32k -strict -2 %s' % ('./', frames_folder, args["output"])
print ffmpeg_cmd
os.system(ffmpeg_cmd)
camera.release()