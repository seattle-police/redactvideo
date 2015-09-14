import sendgrid
import socket
import time
import sys
import os
from os import path
sys.path.append( path.dirname( path.dirname( path.abspath(__file__) ) ) )

from app import get_setting
import rethinkdb as r
conn = r.connect( "localhost", 28015).repl()
db = r.db('redactvideodotorg')
# get everything from DB ahead of time in case db goes down
sg = sendgrid.SendGridClient(get_setting('sendgrid_username'), get_setting('sendgrid_password'))
admins = [admin['id'] for admin in db.table('users').filter({'is_admin': True}).run(conn)]
def is_port_80_down():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1',80))
    if result == 0:
       return False
    else:
       return True

def send_email():
    message = sendgrid.Mail()
    for admin in admins:
        message.add_to(admin)
    message.set_subject('RedactVideo went down')
    message.set_html('Restart attempted')
    message.set_from('no-reply@redactvideo.org')
    status, msg = sg.send(message)
       
while True:
    if is_port_80_down():
        time.sleep(30) # give 30 seconds in case auto update is going on
        if is_port_80_down():
            send_email()
            os.system('cd /home/ubuntu/redactvideodotorg/; python autodeploy.py &') # attempt to autodeploy