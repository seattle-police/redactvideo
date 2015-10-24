RedactVideo is a free open source web app developed by the Seattle Police Department. It allows police departments to automatically publish large quantities of dash and body camera videos while obscuring the identities of citizens.

# Installation

## On Amazon Web Services

1. Create an account 
  1. Go to https://portal.aws.amazon.com/gp/aws/developer/registration/index.html
  2. Enter your email address, select "I am new user", and click "Signin using our secure server"
  3. Fill out the form and click "Create account"
  4. Fill out the contact form and click "Create Account and Continue"
  5. Fill out the payment information and click "Continue"
  6. Follow the on screen identify verification instructions and then click "Continue to select your Support Plan"
  7. On next screen select basic support plan and click "Continue"
  8. On "Welcome to Amazon Web Services" click "Sign into the Console"
2. Signin
3. Setup a role
  1. Click on your name in the top right, click "Security Credentials", and then click "Get Started With IAM Users"
  2. Click "Roles"
  2. Click "Create New Role"
  3. Enter "fullAccess"
  4. Click "Select" next to "Amazon EC2", then click the checkbox next to "Administrator Access", and then click "Next Step"
  5. Clikc "Create Role"
4. Create an EC2 Instance
  1. Click on the orange box and the top left
  2. Click on "EC2"
  3. Click "AMIs"
  4. Click "Owned by me" and then click "Public images"
  5. Click the search box, then click "Name" under "Tag Keys", and then enter "RedactVideo", and hit enter
  6. When the search has completed select the checkbox for "RedactVideo redact_video_main_10_10_15 ami-a84fa89b 141623682332/redact_video_main_10_10_15 141623682332 Public"
  7. Click "Launch"
  8. Select the top item "t2.micro" (free tier)
  9. Click "Configure Instance Details"
  10. Click "None" to the right of "IAM role" and then click "fullAccess"
  11. Click "Next: Add Storage"
  12. Click "Next: Tag Instance"
  13. Enter "RedactVideo primary"
  14. Click "Next: Continue Security Group"
  15. Click "Add Rule", then change 0 to 80, and then click "Custom IP" and change it to "Anywhere"
  16. Click "Review and Launch"
  17. Click "Launch"
  18. Click "Choose an existing key pair" and then click "Proceed without a key pair"
  19. Click the checkbox next to "I acknowledge" and then click "Launch Instances"
  20. Click "View Instances" and wait about ten minutes for it to boot up
  
  
  

# Capabilities

## Over-redaction

* Remove audio and blur all frames
* Remove audio and turn all frames to just outlines of what's in them (AHA effect)
* Remove audio and detect when camera stops moving, make that frame a reference, and redact what's not in the reference frame (doesn't work with body cam footage but does work with in-car video)

## Precise redaction

* Redact audio as listen
* Draw rectangle and do one of following
  * Redact for all frames (e.g. officer serial number for officer involved shooting)
  * Redact for some frames
  * Track forwards and backwards
  * Track forwards
  * Track backwards
* Run detectors
  * Group them 