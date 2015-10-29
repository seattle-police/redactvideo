# curl https://raw.githubusercontent.com/seattle-police/redactvideo/master/scripts/make_safe_for_public_ami.py | sudo python
import os
os.system('curl https://raw.githubusercontent.com/seattle-police/redactvideo/master/scripts/install.py | sudo python')
os.system('sudo shred -u /etc/ssh/*_key /etc/ssh/*_key.pub')
os.system('rm -rf rethinkdb_data; rm -rf redactvideo_logs')
