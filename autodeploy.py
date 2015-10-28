import os
import time
# This script helps with auto deploy of new code by 
# initializing database, installing new pip requirements,
# and killing current instance of app.py
#os.system('sudo python scripts/install.py')
os.system("sudo fuser -k 80/tcp")
import datetime
dt = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
os.system("sudo python app.py")