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
os.system('mkdir /home/ubuntu/grouping_test/')
os.system('rm /home/ubuntu/grouping_test/*')
# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-v", "--video", help="path to the video file")
ap.add_argument("-a", "--min-area", type=int, default=500, help="minimum area size")
args = vars(ap.parse_args())

# if the video argument is None, then we are reading from webcam
if args.get("video", None) is None:
    camera = cv2.VideoCapture(0)
    time.sleep(0.25)

# otherwise, we are reading from a video file
else:
    camera = cv2.VideoCapture(args["video"])

# initialize the first frame in the video stream
firstFrame = None
detections = [[]]
def auto_canny(image, sigma=0.33):
    # compute the median of the single channel pixel intensities
    v = np.median(image)
 
    # apply automatic Canny edge detection using the computed median
    lower = int(max(0, (1.0 - sigma) * v))
    upper = int(min(255, (1.0 + sigma) * v))
    edged = cv2.Canny(image, lower, upper)
 
    # return the edged image
    return edged

# loop over the frames of the video
i = -1
grays = []
groups = {}
centers_to_groups = {}
group_i = 0
saved_frames = []
while True:
    i += 1
    # grab the current frame and initialize the occupied/unoccupied
    # text
    (grabbed, frame) = camera.read()
    text = "Unoccupied"
    #saved_frames.append(frame.copy())
    last_frame = frame.copy()
    # if the frame could not be grabbed, then we have reached the end
    # of the video
    if not grabbed:
        break
    # 411, 363, 228, 66
    for_gray_frame = frame.copy()
    cv2.rectangle(for_gray_frame, (411, 363), (411 + 228, 363 + 66), (0, 0, 0), -1)
    # resize the frame, convert it to grayscale, and blur it
    #frame = imutils.resize(frame, width=500)
    raw_frame = frame.copy()
    
    gray = cv2.cvtColor(for_gray_frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (35, 35), 0)
    #for j in range(1):
    #    gray = cv2.GaussianBlur(gray, (35, 35), 0)
    grays.append(gray)
    # if the first frame is None, initialize it
    if firstFrame is None:
        firstFrame = gray
        continue
    #elif (i > 1):
    #    firstFrame = grays[i - 1]
    
    # compute the absolute difference between the current frame and
    # first frame
    frameDelta = cv2.absdiff(firstFrame, gray)
    thresh = cv2.threshold(frameDelta, 25, 255, cv2.THRESH_BINARY)[1]

    # dilate the thresholded image to fill in holes, then find contours
    # on thresholded image
    thresh = cv2.dilate(thresh, None, iterations=20)
    (cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE)
    frames_detections = []
    # loop over the contours
    new_centers_to_groups = {}
    for c in cnts:
        # if the contour is too small, ignore it
        #if cv2.contourArea(c) < args["min_area"]:
        #    continue

        # compute the bounding box for the contour, draw it on the frame,
        # and update the text
        (x, y, w, h) = cv2.boundingRect(c)
        center = (x + int(float(w)/2), y + int(float(h)/2))
        frames_detections.append({'rect': (x, y, w, h), 'center': center})
        
        #print centers_to_groups
        if i > 0:
            for detection in detections[i-1]:
                (x2, y2, w2, h2) = detection['rect']
                center2 = detection['center']
                #center2 = (x + int(float(w)/2), y + int(float(h)/2))
                centers_close = abs(center2[0] - center[0]) < 50 and abs(center2[1] - center[1]) < 50
                corners_close = abs(x2 - x) < 20 or abs(y2 - y) < 20 or abs((x2 + w2) - (x + w)) < 20 or abs((y2 + h2) - (y + h)) < 20 
                area_close = abs((w2 * h2) - (w * h)) < 150
                size_close = True
                if w2 > w:
                    if w / float(w2) < 0.33:
                    
                        size_close = False
                else:
                    if w2 / float(w) < 0.33:
                        size_close = False
                if h2 > h:
                    if h / float(h2) < 0.33:
                    
                        size_close = False
                else:
                    if h2 / float(h) < 0.33:
                        size_close = False
                #if (centers_close or corners_close) and not size_close:
                #    print "size not close"
                #if (centers_close or corners_close) and size_close:
                if centers_close:
                #if (centers_close or corners_close):
                    #print 'true'
                    #print i, (x, y, w, h), center, (x2, y2, w2, h2), center2
                    if (x2, y2, w2, h2) in centers_to_groups:
                        print True, centers_to_groups[(x2, y2, w2, h2)]
                        groups[centers_to_groups[(x2, y2, w2, h2)]].append(((x, y, w, h), center, i))
                        roi = saved_frames[i][y:y+h, x:x+w].copy()
                        cv2.putText(roi, "Frame: %s %s" % (i, str((x, y, w, h))), (10, 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                        cv2.imwrite("/home/ubuntu/grouping_test/%08d_%08d.png" % (centers_to_groups[(x2, y2, w2, h2)], len(groups[centers_to_groups[(x2, y2, w2, h2)]])-1), roi)
                        
                        new_centers_to_groups[(x, y, w, h)] = centers_to_groups[(x2, y2, w2, h2)]
                    else:
                        groups[group_i] = [((x2, y2, w2, h2), center2, i-1), ((x, y, w, h), center, i)]
                        import os
                        
                        roi = saved_frames[i-1][y2:y2+h2, x2:x2+w2].copy()
                        cv2.putText(roi, "Frame: %s %s" % (i - 1, str((x2, y2, w2, h2))), (10, 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                        cv2.imwrite("/home/ubuntu/grouping_test/%08d_%08d.png" % (group_i, 0), roi)
                        roi = saved_frames[i][y:y+h, x:x+w].copy()
                        cv2.putText(roi, "Frame: %s %s" % (i, str((x, y, w, h))), (10, 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                        cv2.imwrite("/home/ubuntu/grouping_test/%08d_%08d.png" % (group_i, 1), roi)
                        new_centers_to_groups[(x, y, w, h)] = group_i
                        group_i += 1
        
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.drawContours(frame,[c],0,0,-1)
        img = cv2.circle(frame,(x+int(float(w)/2), y+int(float(h)/2)), 5, (0,0,255), -1)
        text = "Occupied"
    text = 'Frame: '+ str(i) + '    ' + str(len(cnts)) + ' detections'
    detections.append(frames_detections)
    centers_to_groups = new_centers_to_groups.copy()
    # draw the text and timestamp on the frame
    cv2.putText(frame, "Room Status: {}".format(text), (10, 20),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    cv2.putText(frame, datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p"),
        (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

    # show the frame and record if the user presses a key
    cv2.imshow("Security Feed", frame)
    #cv2.imshow("Thresh", thresh)
    #cv2.imshow("Frame Delta", frameDelta)
    #(cnts, _) = cv2.findContours(auto_canny(raw_frame).copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    #cnts = sorted(cnts, key = cv2.contourArea, reverse = True)
    #temp = np.zeros(frame.shape,np.uint8)
    #for c in cnts:
        #cv2.drawContours(temp,[c],0,(0,255,0),-1) 
    #cv2.drawContours(temp,cnts,0,(0,0,255),-1)    
    #cv2.imshow("Canny", auto_canny(raw_frame))
    #cv2.imshow("Canny contours", temp)
    
    key = cv2.waitKey(1) & 0xFF
 
    # if the `q` key is pressed, break from the lop
    if key == ord("q"):
        break
for i, d in enumerate(detections):
    print i, d
import json
f = open('/home/ubuntu/analysis.txt', 'w')
f.write(json.dumps(detections))
# cleanup the camera and close any open windows
camera.release()

cv2.destroyAllWindows()
