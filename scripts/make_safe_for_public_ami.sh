# curl https://raw.githubusercontent.com/seattle-police/redactvideo/master/scripts/make_safe_for_public_ami.sh | sudo bash
curl https://raw.githubusercontent.com/seattle-police/redactvideo/master/scripts/install.sh | sudo bash
sudo shred -u /etc/ssh/*_key /etc/ssh/*_key.pub