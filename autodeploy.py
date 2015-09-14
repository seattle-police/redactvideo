import os
import time
# This script helps with auto deploy of new code by
# initializing database and killing current instance of app.py
os.system('git pull --no-edit')    
    
# setup rethinkdb
os.system('python scripts/setup_rethinkdb.py')
    
# kill current instance of app.py
#os.system("sudo ps -ef | grep app.py | grep -v grep | awk '{print $2}' | sudo xargs kill -9")
os.system("sudo fuser -k 80/tcp")
#time.sleep(20)
import datetime
dt = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
os.system("sudo python app.py > /home/ubuntu/app_log_%s.txt 2>&1 &" % (dt))
