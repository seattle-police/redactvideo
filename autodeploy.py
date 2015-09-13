import os
import time
# This script helps with auto deploy of new code by
# initializing database and killing current instance of app.py
os.system('git pull --no-edit')    
    
# setup rethinkdb
os.system('python scripts/setup_rethinkdb.py')
    
# kill current instance of app.py
os.system("sudo ps -ef | grep app.py | grep -v grep | awk '{print $2}' | sudo xargs kill -9")
time.sleep(5)
os.system("sudo python app.py > /home/ubuntu/app_log.txt 2>&1 &")
