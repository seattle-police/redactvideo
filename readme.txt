RedactVideo.org is a free open source web application developed by the Seattle Police Department. The lead developer is 
Tim Clemans (timothy.clemans@seattle.gov). The purpose of RedactVideo is to empower law enforcement agencies to automatically publish as much dash and body camera videos as possible while obsuring the identities of citizens. Additionally the site allows agencies to do manual redaction efficiently. 

Over-redaction

* Blur all frames
* Turn all frames to just outlines of what's in them (AHA effect)
* Detect when camera stops  moving, make that frame a refrence, and redact what's not in the reference frame (doesn't work with body cam footage but does work with in-car video)

Precise redaction

* Redact audio as listen
* Draw rectangle and do one of following
  * Redact for all frames (e.g. officer serial number for officer involved shooting)
  * Redact for some frames
  * Track forwards and backwards
  * Track forwards
  * Track backwards
* Run detectors
  * Group them 

  

