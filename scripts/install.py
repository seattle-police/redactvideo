# curl https://raw.githubusercontent.com/seattle-police/redactvideo/master/scripts/install.py | sudo python
import os
import time
print 'Install Git'
os.system('sudo apt-get -y install git')
print 'Remove RedactVideo'
os.system('rm -rf redactvideo')
print 'Clone RedactVideo'
os.system('git clone https://github.com/seattle-police/redactvideo.git')
print 'Install Python Dev stuff'
os.system('sudo apt-get -y install python-pip')
os.system('sudo apt-get -y install python-dev libxml2-dev libxslt-dev')
print 'Install RethinkDB'
os.system('. /etc/lsb-release && echo "deb http://download.rethinkdb.com/apt $DISTRIB_CODENAME main" | sudo tee /etc/apt/sources.list.d/rethinkdb.list')
os.system('wget -qO- http://download.rethinkdb.com/apt/pubkey.gpg | sudo apt-key add -')
os.system("sudo sed -i 's;us-west-2.ec2.archive.ubuntu.com;us.archive.ubuntu.com;' /etc/apt/sources.list")
os.system('sudo apt-get clean;cd /var/lib/apt;sudo mv lists lists.old;sudo mkdir -p lists/partial;sudo apt-get clean;sudo apt-get update')
os.system('sudo apt-get -y install rethinkdb')
os.system('sudo pip install rethinkdb')
os.system('rethinkdb &')
time.sleep(5) # give rethinkdb 5 seconds to start up
print 'Setup DB'
os.system('python redactvideo/scripts/setup_rethinkdb.py')
print 'Install Flask'
os.system('sudo pip install flask-socketio')
print 'Install Dlib'
os.system('sudo apt-get -y install libboost-python-dev cmake')
os.system('cd /usr/lib/x86_64-linux-gnu; sudo ln -s libboost_python-py27.so.1.55.0 libboost_python.so.1.55.0')
os.system('sudo cp redactvideo/binaries/dlib.so /usr/local/lib/python2.7/dist-packages/')
print 'Install FFMPEG'
os.system('wget http://johnvansickle.com/ffmpeg/builds/ffmpeg-git-64bit-static.tar.xz')
os.system('tar -xvf ffmpeg-git-64bit-static.tar.xz')
os.system('sudo cp  ffmpeg-git-*-64bit-static/ffmpeg /usr/bin/ffmpeg')
os.system('rm -rf ./ffmpeg*')
print 'Install pip requirements'
os.system('sudo pip install -r redactvideo/requirements.txt')
print 'Create logs folder'
os.system('mkdir redactvideo_logs')
print 'Create rc.local'
os.system('sudo cp redactvideo/scripts/rc.local /etc/rc.local')
os.system('cat /etc/rc.local')
print "sudo perl -pi -e 's/replace_with_path/'$(pwd | sed 's_/_\\\\/_g')'/g' /etc/rc.local"
os.system("sudo perl -pi -e 's/replace_with_path/'$(pwd | sed 's_/_\\\\/_g')'/g' /etc/rc.local")
os.system('cat /etc/rc.local')
print 'Install Various Python packages'
os.system('sudo apt-get -y install python-numpy python-scipy python-matplotlib ipython ipython-notebook python-pandas python-sympy python-nose')
os.system('sudo apt-get -y install libopencv-dev python-opencv')