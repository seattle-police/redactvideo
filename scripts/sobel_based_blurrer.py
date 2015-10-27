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
ap = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
#ap = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter)

ap.add_argument("-i", "--input", help="path to the video file")
ap.add_argument("-o", "--output", help="path to the video file")
ap.add_argument("-t", "--threshold", type=int, default=10, help="threshold")
ap.add_argument("-c", "--iterations", type=int, default=10, help="iterations")
ap.add_argument("-a", "--min-area", type=int, default=200, help="minimum area size")
ap.add_argument("-k", "--type", default='fixed', help="type of camera")
ap.add_argument("-s", "--stop_count", type=int, default=60, help="stop count")
ap.add_argument("-q", "--temp_folder", default='', help="temp folder")
ap.add_argument("-f", "--ffmpeg_path", default='./', help="path to ffmpeg")
ap.add_argument("-b", "--blur_what", default='bounding_box', help="path to ffmpeg")

args = vars(ap.parse_args())
tf = args["temp_folder"]
if tf and not tf.endswith('/'):
    tf = tf + '/'
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
os.system('mkdir %s/' % (frames_folder))
# loop over the frames of the video
while True:
    print i, 'gray'
    i += 1
    (grabbed, frame) = camera.read()
    filename = '%08d.jpg' % (i)
    im_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    #(thresh, im_bw) = cv2.threshold(im_gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    #gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    #cv2.imwrite('%s%s/%s' % (tf, frames_folder, filename), cv2.Sobel(im_bw,cv2.CV_64F,0,1,ksize=5))

    #contours, hierarchy = cv2.findContours(im_bw.copy(), cv2.RETR_EXTERNAL,
    #    cv2.CHAIN_APPROX_SIMPLE)
    #cv2.drawContours(frame, contours, -1, (0,255,0), 3)
    #inverse = 255 - im_bw
    #contours, hierarchy = cv2.findContours(inverse.copy(), cv2.RETR_EXTERNAL,
    #    cv2.CHAIN_APPROX_SIMPLE)
    #cv2.drawContours(frame, contours, -1, (255,0,0), 3)
    sift = cv2.xfeatures2d.SIFT_create()
    kp = sift.detect(im_gray,None)

    img=cv2.drawKeypoints(frame,kp)
    cv2.imwrite('%s%s/%s' % (tf, frames_folder, filename), img)
    try:
        (grabbed, frame) = camera.read()
        filename = '%08d.jpg' % (i)
        im_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        #(thresh, im_bw) = cv2.threshold(im_gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        #gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        #cv2.imwrite('%s%s/%s' % (tf, frames_folder, filename), cv2.Sobel(im_bw,cv2.CV_64F,0,1,ksize=5))

        #contours, hierarchy = cv2.findContours(im_bw.copy(), cv2.RETR_EXTERNAL,
	    #    cv2.CHAIN_APPROX_SIMPLE)
        #cv2.drawContours(frame, contours, -1, (0,255,0), 3)
        #inverse = 255 - im_bw
        #contours, hierarchy = cv2.findContours(inverse.copy(), cv2.RETR_EXTERNAL,
	    #    cv2.CHAIN_APPROX_SIMPLE)
        #cv2.drawContours(frame, contours, -1, (255,0,0), 3)
        sift = cv2.xfeatures2d.SIFT_create()
        kp = sift.detect(im_gray,None)
        
        img=cv2.drawKeypoints(frame,kp)
        cv2.imwrite('%s%s/%s' % (tf, frames_folder, filename), img)
        
    except:
        break
ffmpeg_cmd = '%sffmpeg -i %s/%%08d.jpg -y -r 24 -vcodec libx264 -preset ultrafast -b:a 32k -strict -2 %s' % (args["ffmpeg_path"], frames_folder, args["output"])
print ffmpeg_cmd
os.system(ffmpeg_cmd)
print ffmpeg_cmd
os.system('rm -rf %s%s' % (tf, frames_folder))
# cleanup the camera and close any open windows
camera.release()
#cv2.destroyAllWindows()
#print number_of_detections_per_frame
