# curl https://raw.githubusercontent.com/seattle-police/redactvideo/master/scripts/install.sh | sudo bash
echo "Install Git"
sudo apt-get -y install git
echo "Remove RedactVideo"
rm -rf redactvideo
echo "Clone RedactVideo"
git clone https://github.com/seattle-police/redactvideo.git
sudo apt-get -y install python-pip
sudo apt-get -y install python-dev libxml2-dev libxslt-dev
echo "Install RethinkDB"
. /etc/lsb-release && echo "deb http://download.rethinkdb.com/apt $DISTRIB_CODENAME main" | sudo tee /etc/apt/sources.list.d/rethinkdb.list
wget -qO- http://download.rethinkdb.com/apt/pubkey.gpg | sudo apt-key add -
sudo apt-get update
sudo apt-get -y install rethinkdb
sudo pip install rethinkdb
python redactvideo/scripts/setup_rethinkdb.py
sudo pip install flask-socketio
sudo cp redactvideo/binaries/dlib.so /usr/local/lib/python2.7/dist-packages/
sudo apt-get -y install python-numpy python-scipy python-matplotlib ipython ipython-notebook python-pandas python-sympy python-nose
sudo apt-get -y install libopencv-dev python-opencv
wget http://johnvansickle.com/ffmpeg/builds/ffmpeg-git-64bit-static.tar.xz 
tar -xvf ffmpeg-git-64bit-static.tar.xz
sudo cp  ffmpeg-git-*-64bit-static/ffmpeg /usr/bin/ffmpeg
sudo pip install -r redactvideo/requirements.txt
mkdir redactvideo_logs
sudo cp redactvideo/scripts/rc.local /etc/rc.local
BASE_PATH=$(pwd | sed 's_/_\\/_g')
echo "path", $BASE_PATH
sudo perl -pi -e 's/replace_with_path/'$BASE_PATH'/g' /etc/rc.local