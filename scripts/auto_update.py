# cron is hard to set up programmatically so lets just run this file at boot
# run git pull every five minutes 

import os
while True:
    os.system('cd ../; git stash save --keep-index')
    git_pull_request = os.popen('cd ../; git pull --no-edit').read()
    if not 'Already up-to-date.' in git_pull_request:
        os.system('cd ../; python auto_deploy.py &')
    time.sleep(60*5)