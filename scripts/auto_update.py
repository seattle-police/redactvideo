import os
os.system('git stash save --keep-index')
git_pull_request = os.popen('cd /home/ubuntu/redactvideodotorg; git pull --no-edit').read()