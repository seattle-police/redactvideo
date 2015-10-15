# USAGE
# python motion_detector.py
# python motion_detector.py --video videos/example_01.mp4

# import the necessary packages
import argparse
import datetime
import imutils
import time
import cv2
import numpy as np
import os
# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--input", help="path to the video file")
ap.add_argument("-o", "--output", help="path to the video file")
ap.add_argument("-t", "--threshold", type=int, default=20, help="threshold")
ap.add_argument("-c", "--iterations", type=int, default=10, help="iterations")
ap.add_argument("-a", "--min-area", type=int, default=200, help="minimum area size")
ap.add_argument("-k", "--type", default='fixed', help="type of camera")
ap.add_argument("-s", "--stop_count", type=int, default=60, help="stop count")
args = vars(ap.parse_args())

# if the video argument is None, then we are reading from webcam
if args.get("input", None) is None:
    camera = cv2.VideoCapture(0)
    time.sleep(0.25)

# otherwise, we are reading from a video file
else:
    camera = cv2.VideoCapture(args["input"])
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
import random
import string
frames_folder = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))
os.system('mkdir /home/ubuntu/temp_videos/%s/' % (frames_folder))
# loop over the frames of the video
while True:
    #print i
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
    gray = cv2.GaussianBlur(gray, (25, 25), 0)
    
    blurred = cv2.GaussianBlur(frame, (35, 35), 0)
    
    for j in range(2):
        blurred = cv2.GaussianBlur(blurred, (35, 35), 0)
    # if the first frame is None, initialize it
    grays.append(gray)
    if firstFrame is None:
        firstFrame = gray
    #    continue
    #elif (i > 2 and not confirmed_stopped):
    #    firstFrame = grays[i - 2]

    # compute the absolute difference between the current frame and
    # first frame
    frameDelta = cv2.absdiff(firstFrame, gray)
    #if avg is None:
    #    print "[INFO] starting background model..."
    #    avg = gray.copy().astype("float")
    #    continue
    #cv2.accumulateWeighted(gray, avg, 0.5)
    #frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))
    thresh = cv2.threshold(frameDelta, args.get("threshold"), 255, cv2.THRESH_BINARY)[1]

    # dilate the thresholded image to fill in holes, then find contours
    # on thresholded image
    thresh = cv2.dilate(thresh, None, iterations=args.get('iterations'))
    (cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE)

    # loop over the contours
    areas = []
    for c in cnts:
    #    # if the contour is too small, ignore it
    #    (x, y, w, h) = cv2.boundingRect(c)
    #    if (cv2.contourArea(c) < args["min_area"]) or ((float(w)/2) > h and h < 40):
    #        continue

        # compute the bounding box for the contour, draw it on the frame,
        # and update the text
        (x, y, w, h) = cv2.boundingRect(c)
        #print w, h
        areas.append((w*h, w, h))
        detections.append(((x, y, w, h), i))
        #cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 1)
    #    cv2.drawContours(frame, [c], -1, (0,0,0), -1)
    #    cv2.drawContours(frame, [c], -1, (255,255,255), 1)
        temp = np.zeros(frame.shape,np.uint8)
        cv2.drawContours(temp,[c],0,255,-1)
        x = np.where(temp != 0)
        #print x[1:]
        frame[x[:2]] = blurred[x[:2]]
        #pp = np.transpose(np.nonzero(temp))   #all pixelpoints in contour
        #for k in range(0, len(pp)):
        #    frame[ pp[k,0],pp[k,1] ] = blurred[ pp[k,0],pp[k,1] ]
    if areas:
        #print stopped_count
        largest = sorted(areas, key=lambda x: x[0], reverse=True)[0]
        print largest[1], frame.shape[1]-120, largest[2], frame.shape[0]-120
        if (largest[1] > frame.shape[1]-120 and largest[2] > frame.shape[0]-120):
            print 'yes'
            firstFrame = gray
        #print largest[1], frame.shape[0]-100, largest[2], frame.shape[1]-100
        #if not (largest[1] > frame.shape[0]-100 and largest[2] > frame.shape[1]-100):
        #    #print 'stopped', i, sorted(areas, key=lambda x: x[0], reverse=True)[0]
        #    stopped_count += 1
        #    if stopped_count == args.get('stop_count'):
        #        started_count = 0
        #        confirmed_stopped = True
        #        print 'confirmed stopped', i - 60
        #        firstFrame = saved_gray
        #    if stopped_count == 1:
        #        saved_gray = gray
        #else:
        #    firstFrame = gray
        #    started_count += 1
        #    if started_count == args.get('stop_count'):
        #        print 'started', largest
        #        stopped_count = 0
        #        confirmed_stopped = False
        #print i, sorted(areas, key=lambda x: x[0], reverse=True)[0]
    #number_of_detections_per_frame.append(len(cnts))
    #cv2.drawContours(frame, cnts, -1, (0,0,0), -1)
    #cv2.drawContours(frame, cnts, -1, (255,255,255), 1)
    #text = "Occupied"
    #for c in detections:
    #    if (i - c[1]) < 60:
    #        (x, y, w, h) = c[0]
    #        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), -1)
            
            

    # show the frame and record if the user presses a key
    #cv2.imshow("Thresh", thresh)
    #cv2.imshow("Frame Delta", frameDelta)
    #cv2.imshow("Blurred", blurred)
    cv2.imshow("Security Feed", frame)
    
    key = cv2.waitKey(1) & 0xFF

    # if the `q` key is pressed, break from the lop
    #if key == ord("q"):
    #    break
    #if i % 60 == 0:
    #    firstFrame = gray
    #firstFrame = gray
    filename = '%08d.jpg' % (i)
    cv2.imwrite('/home/ubuntu/temp_videos/%s/%s' % (frames_folder, filename), frame)
os.system('ffmpeg -i /home/ubuntu/temp_videos/%s/%%08d.jpg -y -r 24 -vcodec libx264 -preset ultrafast -b:a 32k -strict -2 %s' % (frames_folder, args["output"]))
os.system('rm -rf /home/ubuntu/temp_video/%s' % (frames_folder))
# cleanup the camera and close any open windows
camera.release()
cv2.destroyAllWindows()
#print number_of_detections_per_frame
