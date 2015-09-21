# This is for Ubuntu 15.04
sudo apt-get -y install git
sudo apt-get -y install python-pip
sudo apt-get -y install python-dev libxml2-dev libxslt-dev
. /etc/lsb-release && echo "deb http://download.rethinkdb.com/apt $DISTRIB_CODENAME main" | sudo tee /etc/apt/sources.list.d/rethinkdb.list
wget -qO- http://download.rethinkdb.com/apt/pubkey.gpg | sudo apt-key add -
sudo apt-get update
sudo apt-get -y install rethinkdb
sudo pip install rethinkdb
python /home/ubuntu/redactvideodotorg/scripts/setup_rethinkdb.py
sudo pip install flask-socketio
sudo apt-get -y install ffmpeg

# For Dlib
sudo apt-get -y install libboost-python-dev cmake
mkdir /home/ubuntu/dlib
git clone https://github.com/davisking/dlib.git /home/ubuntu/dlib
cd /home/ubuntu/dlib/python_examples
mkdir build
cd build
cmake -DUSE_SSE2_INSTRUCTIONS=ON ../../tools/python
cmake --build . --config Release --target install
cd ..
sudo cp dlib.so /usr/local/lib/python2.7/dist-packages/
sudo apt-get install python-numpy python-scipy python-matplotlib ipython ipython-notebook python-pandas python-sympy python-nose
sudo pip install -r ../requirements.txt
