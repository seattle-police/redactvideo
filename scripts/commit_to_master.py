import os
msg = raw_input("Commit message: \n")
os.system('cd /home/ubuntu/redactvideodotorg/; git add .; git commit -a -m "%s"; git push origin master' % (msg))