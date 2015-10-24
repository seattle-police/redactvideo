from flask import Flask, Response, request, redirect, render_template, make_response
from flask.ext.socketio import SocketIO, emit
import gevent
import rethinkdb as r
import re
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['PROPAGATE_EXCEPTIONS'] = True
socketio = SocketIO(app)
import json
import string
import random
import sendgrid
import hashlib
from flask.ext.socketio import session as socket_session
conn = r.connect( "localhost", 28015).repl()
db = r.db('redactvideodotorg')
conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
print conn
import boto
import boto.awslambda

from boto.s3.connection import S3Connection
from boto.s3.key import Key
import os,sys
import requests
import dlib
import glob
from skimage import io
from utils.video import put_folder_on_s3
import thread

import boto3
import random
import string

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    return ''.join(random.choice(chars) for _ in range(size))

# Let's use Amazon S3
s3 = boto3.resource('s3')

# get settings
buckets = list(s3.buckets.all())
settings_buckets = [bucket for bucket in buckets if bucket.startswith('redactvideo_settings_')]

if settings_buckets:
    settings_bucket = settings_buckets[0]
else:
    bucket_name = 'redactvideo_settings_' + id_generator()
    s3.create_bucket(Bucket=bucket_name)
def get_setting(setting):
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    try:
        return db.table('settings').get(setting).run(conn)['value']   
    except:
        return ''    

# Need to wait for RethinkDB to be running
# in rc.local there's no wait between starting rethinkdb and
# starting this script
while True:
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    try:
        s3conn = S3Connection(get_setting('access_key_id'), get_setting('secret_access_key'))
        bucket = s3conn.get_bucket(get_setting('bucket_name'))
        break
    except:
        pass

from upload import upload_to_youtube


def is_logged_in(request):
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    if request.cookies.get('session'):
        if Response(db.table('sessions').get(request.cookies.get('session')).run(conn)['userid']):
            return True
        else:
            return False
    else:
        return False
 
def get_users_random_id(userid):
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    results = list(db.table('random_ids_for_users').filter({'userid': userid}).run(conn))
    if results:
        return results[0]['id']
    else:
        random_id = id_generator()
        db.table('random_ids_for_users').insert({'id': random_id, 'userid': userid}).run(conn)
        return random_id
 
@app.route('/')
def index():
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    context = {}
    context['google_analytics_tracking_id'] = get_setting('google_analytics_tracking_id')
    if is_logged_in(request):
        
        user_id = db.table('sessions').get(request.cookies.get('session')).run(conn)['userid']
        context['userid'] = user_id
        context['users_random_id'] = get_users_random_id(user_id)
        #print user_id
        user_data = db.table('users').get(user_id).run(conn)
        import base64
        import hmac, hashlib
        import random, string
        policy_document = """{"expiration": "2020-01-01T00:00:00Z",
  "conditions": [ 
    {"bucket": "%s"}, 
    ["starts-with", "$key", "%s/"],
    {"acl": "public-read"}
  ]
}""" % (get_setting('bucket_name'), user_id)
        context['upload'] = {} 
        context['upload']['bucket_name'] = get_setting('bucket_name')
        context['upload']['policy'] = base64.b64encode(policy_document)
        context['upload']['access_key_id'] = get_setting('access_key_id')
        context['upload']['signature'] = base64.b64encode(hmac.new(str(get_setting('secret_access_key')), context['upload']['policy'], hashlib.sha1).digest())
        

        rs = bucket.list(user_id)
       
        context['videos'] = [{'name': key.name[key.name.index('/')+1:], 'hash': get_md5(key.name)} for key in rs]
        context['has_authed_with_youtube'] = True if user_data.get('youtube_refresh_token') else False
        context['is_admin'] = user_data['is_admin']
        context['google_client_id'] = get_setting('google_client_id')
        if user_data['is_admin']:
            context['site_settings'] = dict([(item['id'],item['value']) for item in db.table('settings').run(conn)])
        if user_data.get('settings'):
            context['user_settings'] = user_data['settings']
        else:
            context['user_settings'] = {'access_key_id': '', 'secret_access_key': ''}
        return render_template('main.html', **context)
        
    elif db.table('users').count().run(conn) == 0:
        return render_template('setup.html')
    else:
        return render_template('index.html', **context)

@app.route('/convert_every_video_to_h264/', methods=['GET'])         
def convert_every_video_to_h264():
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    userid = db.table('sessions').get(request.cookies.get('session')).run(conn)['userid']
    for video in bucket.list(userid):
        
        #print video, video.name
        filename = video.name[video.name.index('/')+1:]
        if not '@' in filename and filename.endswith('.MPG'):
            continue
        if not filename:
            continue
        video.get_contents_to_filename('/home/ubuntu/temp_videos/%s' % (filename))
        os.system('ffmpeg -i "/home/ubuntu/temp_videos/%s" -y -r 24 -vcodec libx264 -preset ultrafast -b:a 32k -strict -2 "/home/ubuntu/temp_videos/converted_%s.mp4"' % (filename, filename[:-4]))
        os.system('rm "/home/ubuntu/temp_videos/%s"' % (filename))
        os.system('mv "/home/ubuntu/temp_videos/converted_%s.mp4" "/home/ubuntu/temp_videos/%s.mp4"' % (filename[:-4], filename[:-4]))
        
        upload_to_s3('/home/ubuntu/temp_videos/%s.mp4' % (filename[:-4]), userid)
        os.system('rm "/home/ubuntu/temp_videos/%s.mp4"' % (filename[:-4]))
    return Response('')

def get_md5(thestr):
    import hashlib
    m = hashlib.md5()
    m.update(thestr)
    return m.hexdigest()    
    
@app.route('/generate_thumbs_for_every_video/', methods=['GET'])         
def generate_thumbs_for_every_video():
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    from utils.video import put_folder_on_s3
    userid = db.table('sessions').get(request.cookies.get('session')).run(conn)['userid']
    for video in bucket.list(userid):
        
        #print video, video.name
        filename = video.name[video.name.index('/')+1:]
        if not filename:
            continue
        video.get_contents_to_filename('/home/ubuntu/temp_videos/%s' % (filename))
        hash = get_md5(video.name)
        os.system('mkdir /home/ubuntu/temp_videos/%s/' % (hash))
        os.system('ffmpeg -i "/home/ubuntu/temp_videos/%s" -vf fps=1/30 /home/ubuntu/temp_videos/%s/%%03d.jpg' % (filename, hash))
        put_folder_on_s3('/home/ubuntu/temp_videos/%s/' % (hash), hash, get_setting('bucket_name'), get_setting('access_key_id'), get_setting('secret_access_key'))
        os.system('rm -rf /home/ubuntu/temp_videos/%s/' % (hash))
    return Response('')
    
@app.route('/youtube_oauth_callback/', methods=['GET']) 
def youtube_oauth_callback():
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    code = request.args['code']
    t = requests.post(
    'https://accounts.google.com/o/oauth2/token',
    data={'code': code, 'client_id': get_setting('google_client_id'), 'client_secret': get_setting('google_client_secret'), 'redirect_uri': 'http://redactvideo.org/youtube_oauth_callback/', 'grant_type': 'authorization_code'})
    data = t.json()
    user_id = db.table('sessions').get(request.cookies.get('session')).run(conn)['userid']
    db.table('users').get(user_id).update({'youtube_token': data['access_token'], 'youtube_refresh_token': data['refresh_token']}).run(conn)

    
    return render_template("youtube_callback.html")        

def get_users_youtube_token(user_id):    
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    youtube_refresh_token = db.table('users').get(user_id).run(conn)['youtube_refresh_token']
    t = requests.post(
    'https://accounts.google.com/o/oauth2/token',
    data={'client_id': get_setting('google_client_id'), 'client_secret': get_setting('google_client_secret'), 'refresh_token': youtube_refresh_token, 'grant_type': 'refresh_token'})
    data = t.json()
    return data['access_token']
    
@app.route('/overblur_and_publish_all_videos/')
def overblur_and_publish_all_videos():
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    user_id = db.table('sessions').get(request.cookies.get('session')).run(conn)['userid']
    youtube_token = get_users_youtube_token(user_id)
    for key in bucket.list(user_id):
        random_filename = id_generator()+'.mp4'
        key.get_contents_to_filename('/home/ubuntu/temp_videos/%s' % (random_filename))
        os.system('ffmpeg -threads 0 -i "/home/ubuntu/temp_videos/%s" -preset ultrafast -vf scale=320:240,"boxblur=6:4:cr=2:ar=2",format=yuv422p  -an "/home/ubuntu/temp_videos/overredacted_%s"' % (random_filename, random_filename))
        upload_to_youtube('/home/ubuntu/temp_videos/overredacted_%s' % (random_filename), youtube_token)
        os.remove('/home/ubuntu/temp_videos/%s' % (random_filename))
        os.remove('/home/ubuntu/temp_videos/overredacted_%s' % (random_filename))
    return Response('done')
    
@app.route('/change_site_settings/', methods=['POST'])
def change_site_settings():
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    if is_logged_in(request):
        user_id = db.table('sessions').get(request.cookies.get('session')).run(conn)['userid']
        user_data = db.table('users').get(user_id).run(conn)
        if user_data['is_admin']: 
            settings = [{'id': item[0], 'value': item[1]} for item in request.form.items()]
            db.table('settings').insert(settings, conflict='update').run(conn)
            return Response(json.dumps({'success': True}))

@app.route('/change_user_settings/', methods=['POST'])
def change_user_settings():
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    #print 'runns'
    if is_logged_in(request):
        user_id = db.table('sessions').get(request.cookies.get('session')).run(conn)['userid']
        user_data = db.table('users').get(user_id).run(conn) 
        if user_data.get('settings'):
            settings = user_data['settings']
        else:
            settings = {}
        #print 'request data', dict(request.form)
        # sometimes request.form is in the form of {'x': ['value']} instead of
        # {'x': 'value'} so need to convert to
        #  {'x': 'value'}
        form = dict([(item[0], item[1] if isinstance(item[1], basestring) else item[1][0]) for item in request.form.items()])
        settings.update(form)
        #print 'settings', settings
        db.table('users').get(user_id).update({'settings': settings}).run(conn)
        #print db.table('users').get(user_id).run(conn)
        return Response(json.dumps({'success': True}))            

@app.route('/get_users_s3_buckets/', methods=['GET'])
def get_users_s3_buckets():
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    #print 'runns'
    if is_logged_in(request):
        user_id = db.table('sessions').get(request.cookies.get('session')).run(conn)['userid']
        user_data = db.table('users').get(user_id).run(conn) 
        settings = user_data.get('settings')
        s3conn_for_user = S3Connection(settings['access_key_id'], settings['secret_access_key'])
        #s3conn_for_user.get_all_buckets()
        return Response(json.dumps({'buckets': s3conn_for_user.get_all_buckets()}))   

        
@app.route('/logout/')        
def logout():
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    resp = make_response(redirect('/'))
    resp.set_cookie('session', '', expires=0)
    return resp
        
@app.route('/create_first_user/', methods=['POST'])
def create_first_user():
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    if db.table('users').count().run(conn) == 0:
        email = request.form['email']
        password = request.form['password']
        salt = id_generator()
        import hashlib
        m = hashlib.sha512()
        m.update(salt+password)
        hash = m.hexdigest()
        session_id = id_generator(30)
        db.table('sessions').insert({'id': session_id, 'userid': email}).run(conn)
        resp = make_response(redirect('/'))
        resp.set_cookie('session', session_id)
        db.table('users').insert({'id': email, 'salt': salt, 'hash': hash, 'is_admin': True}).run(conn)    
        return resp
    return redirect('/')

@app.route('/login/', methods=['POST'])    
def login():
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    # it's assumed that a username is an email address
    if not is_already_account(request.form['username']):
        return Response(json.dumps({'msg': '<strong>Error:</strong> Either email or password is incorrect'}), mimetype="application/json")
    user_data = db.table('users').get(request.form['username']).run(conn)
    m = hashlib.sha512()
    salt = user_data['salt']
    password = request.form['password']
    m.update(salt+password)
    hash = m.hexdigest()
    
    if user_data['hash'] != hash:
        return Response(json.dumps({'msg': '<strong>Error:</strong> Either email or password is incorrect'}), mimetype="application/json")
    if not (user_data.get('is_approved') or user_data.get('is_admin')):
        return Response(json.dumps({'msg': "<strong>Error:</strong> Your account hasn't been approved"}), mimetype="application/json")
    two_factor_code = id_generator(60)
    db.table('two_factor_codes').insert({'id': two_factor_code, 'userid': request.form['username']}).run(conn)
    message = sendgrid.Mail()
    message.add_to(request.form['username'])
    message.set_subject('RedactVideo two factor authentication')
    message.set_html('<a href="http://redactvideo.org/confirm_two_factor/?two_factor_code=%s">Click here</a> to confirm two factor code.' % (two_factor_code))
    message.set_from('no-reply@redactvideo.org')
    sg = sendgrid.SendGridClient(get_setting('sendgrid_username'), get_setting('sendgrid_password'))
    status, msg = sg.send(message)
    return Response(json.dumps({'msg': 'Two factor authentication email sent'}), mimetype="application/json")


@app.route('/confirm_two_factor/')            
def confirm_two_factor():
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    userid = db.table('two_factor_codes').get(request.args['two_factor_code']).run(conn)['userid']
    user_data = db.table('users').get(userid).run(conn)
    
    session_id = id_generator(30)
    username = userid
    #print db.table('sessions').insert({'id': session_id, 'userid': username}).run(conn)
    resp = make_response(redirect('/'))
    resp.set_cookie('session', session_id)
    return resp
    
def is_already_account(email):
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    if list(db.table('users').filter({'id': email}).run(conn)):
        return True
    return False
    
    
@app.route('/submit_request_for_account/', methods=['POST'])
def submit_request_for_account():
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    from validate_email import validate_email
    if validate_email(request.form['agency_email'], check_mx=True): # verify=True didn't work
        if is_already_account(request.form['agency_email']):
            return Response(json.dumps({'success': False, 'msg': '<strong class="error">Error:</strong> That email is already in the system'}), mimetype="application/json")
        else:
            agency_email = request.form['agency_email']
            message = sendgrid.Mail()
            for admin in db.table('users').filter({'is_admin': True}).run(conn):
                if '@' in admin['id']:
                    message.add_to(admin['id'])
            message.set_subject('%s requests RedactVideo account' % (agency_email))
            message.set_html('%s is requesting an account' % (agency_email))
            message.set_from('no-reply@redactvideo.org')
            sg = sendgrid.SendGridClient(get_setting('sendgrid_username'), get_setting('sendgrid_password'))
            status, msg = sg.send(message)
            #print status, msg
            secret_code = id_generator(60)
            if agency_email.endswith('.gov'):
                approved = True
            else:
                approved = None # None instead of False so we can tell when admin has made decision
            db.table('accounts_to_verify').insert({'id': secret_code, 'userid': agency_email}, conflict='update').run(conn)
            message = sendgrid.Mail()
            message.add_to(agency_email)
            message.set_subject('Confirm account for RedactVideo')
            message.set_html('<a href="http://redactvideo.org/confirm_account/?code=%s">Click here</a> to confirm your account.' % (secret_code))
            message.set_from('no-reply@redactvideo.org')
            sg = sendgrid.SendGridClient(get_setting('sendgrid_username'), get_setting('sendgrid_password'))
            status, msg = sg.send(message)
            db.table('users').insert({'id': agency_email, 'is_admin': False, 'verified': False, 'approved': approved}).run(conn)    
            return Response(json.dumps({'success': True, 'msg': "An email has been sent. Please click on the link in it to confirm your email."}), mimetype="application/json")
    else:
        return Response(json.dumps({'success': False, 'msg': 'Invalid email address'}), mimetype="application/json")

@app.route('/confirm_account/')
def confirm_account():
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    userid = db.table('accounts_to_verify').get(request.args['code']).run(conn)['userid']
    db.table('users').get(userid).update({'verified': True}).run(conn)  
    session_id = id_generator(30)
    username = userid
    #print {'id': session_id, 'userid': username}
    #print db.table('sessions').insert({'id': session_id, 'userid': username}).run(conn)
    resp = make_response(render_template('create_password.html'))
    resp.set_cookie('session', session_id)
    return resp

@app.route('/create_password/', methods=['POST'])    
def create_password():
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    #print request.form['retyped_password']
    if request.form['password'] == request.form['retyped_password']:
        user_id = db.table('sessions').get(request.cookies.get('session')).run(conn)['userid']
        user_data = db.table('users').get(user_id).run(conn)
        import hashlib
        m = hashlib.sha512()
        salt = id_generator()
        m.update(salt+request.form['password'])
        hash = m.hexdigest() 
        
        
        db.table('users').get(user_id).update({'salt': salt, 'hash': hash}).run(conn)  
        return redirect('/')
    else:
        return redirect('/create_password/')

@app.route('/autoupdate/', methods=['POST'])
def autoupdate():
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    github_signature = request.headers.get('X-Hub-Signature')
    secret = get_setting('github_auto_update_secret')
    import hmac
    from hashlib import sha1
    #print request.get_json()
    #print secret
    hmac_object = hmac.new(str(secret), request.data, digestmod=sha1)
    if hmac.compare_digest(str(github_signature), 'sha1='+hmac_object.hexdigest()):
        os.system('python autodeploy.py &')
    return Response('')

def upload_to_s3(filepath, userid):
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    import math, os
    import boto
    from filechunkio import FileChunkIO

    b = bucket

    # Get file info
    source_path = filepath
    source_size = os.stat(source_path).st_size

    # Create a multipart upload request
    mp = b.initiate_multipart_upload(userid+'/'+os.path.basename(source_path))

    # Use a chunk size of 50 MiB (feel free to change this)
    chunk_size = 52428800
    chunk_count = int(math.ceil(source_size / float(chunk_size)))

    # Send the file parts, using FileChunkIO to create a file-like object
    # that points to a certain byte range within the original file. We
    # set bytes to never exceed the original file size.
    for i in range(chunk_count):
        offset = chunk_size * i
        bytes = min(chunk_size, source_size - offset)
        with FileChunkIO(source_path, 'r', offset=offset,
                             bytes=bytes) as fp:
            mp.upload_part_from_file(fp, part_num=i + 1)

    # Finish the upload
    mp.complete_upload()
    key = bucket.get_key(userid+'/'+os.path.basename(source_path))
    key.set_acl('public-read')

@app.route('/save_upperbody_detection_coordinates/', methods=['POST'])
def save_upperbody():
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    import json
    #print request.form
    conn = r.connect( "localhost", 28015).repl()
    db.table('upperbody_detections').insert({'id': request.form['filename'], 'coordinates': json.loads(request.form['detected_regions'])}, conflict='update').run(conn)
    #print request.form
    return Response('')

def send_short_email(userid, mes):    
    message = sendgrid.Mail()
    message.add_to(userid)
    message.set_subject(mes)
    message.set_html(mes)
    message.set_from('no-reply@redactvideo.org')
    sg = sendgrid.SendGridClient(get_setting('sendgrid_username'), get_setting('sendgrid_password'))
    status, msg = sg.send(message)

def incoming_email_thread(form):
    import rethinkdb as r
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    # parse the to email address
    #print 'to', form['to']
    if form['to'].endswith('>'):
        m = re.search('"(?P<email>.*)"', form['to'])
        email = m.group('email')
    else:
        email = form['to'].strip('">')
    if not email.endswith('@redactvideo.org'):
        return Response('error')
    userto = email.split('@')[0]
    #print 'userto', userto
    users_random_id = userto[:userto.index('_')].upper()
    userid = db.table('random_ids_for_users').get(users_random_id).run(conn)['userid']
    #print 'userid', userid
    # download the evidence.com html with the url to download the zip file
    #print 'txt is next'
    #print form
    body = form['html'] if 'html' in form else form['text']
    m = re.search('(?P<base>https://(.*)\.evidence\.com)/1/uix/public/download/\?package_id=(.*)ver=v2', body)
    if not m:
        #print 'something wrong with email parsing'
        send_short_email(userid, 'Something wrong with the authenticated share make sure your share is unauthenticated')
        #return Response('')
    else:
        print 'M', m
    
    r = requests.get(m.group(0))
    
    #print 'mgroup0', m.group(0)
    base_url = m.group('base')
    download_html = r.text
    #print download_html
    m = re.search('download_url="(?P<url>.*ver=v2)', download_html)
    zip_download_url = base_url+m.group('url').replace('&amp;', '&')
    
    #print zip_download_url
    # save the zip file
    zips_id = id_generator()
    with open('/home/ubuntu/temp_videos/'+zips_id+'.zip', 'wb') as handle:
        response = requests.get(zip_download_url, stream=True)

        if not response.ok:
            pass

        for block in response.iter_content(1024):
            handle.write(block)
    # unzip the file
    #send_short_email(userid, 'Videos received from E.com now unpacking')
    os.system('cd /home/ubuntu/temp_videos/; mkdir zips_id; unzip -d %s -j %s.zip' % (zips_id, zips_id))
    #send_short_email(userid, 'Videos from E.com unpacked')
    # now need to know what to do with the files
    # e.g. put on S3 or on Youtube
    if '_just_copy_over' in email:
        for video in os.listdir('/home/ubuntu/temp_videos/'+zips_id):
            if not video.endswith('pdf'):
                upload_to_s3('/home/ubuntu/temp_videos/'+zips_id+'/'+video, userid)
    elif 'as_is_to_' in email:
        youtube_refresh_token = db.table('users').get(userid).run(conn)['youtube_refresh_token']
        t = requests.post(
        'https://accounts.google.com/o/oauth2/token',
        data={'client_id': get_setting('google_client_id'), 'client_secret': get_setting('google_client_secret'), 'grant_type': 'refresh_token'})
        data = t.json()
        youtube_token = get_users_youtube_token(userid)
        for video in os.listdir('/home/ubuntu/temp_videos/'+zips_id):
            if not video.endswith('pdf'):
                upload_to_youtube('/home/ubuntu/temp_videos/'+zips_id+'/'+video, youtube_token)
    #elif 'overblur_to_youtube' in email:
    else:    
        youtube_refresh_token = db.table('users').get(userid).run(conn)['youtube_refresh_token']
        t = requests.post(
        'https://accounts.google.com/o/oauth2/token',
        data={'client_id': get_setting('google_client_id'), 'client_secret': get_setting('google_client_secret'), 'grant_type': 'refresh_token'})
        data = t.json()
        youtube_token = get_users_youtube_token(userid)
        for video in os.listdir('/home/ubuntu/temp_videos/'+zips_id):
            if not video.endswith('pdf'): 
                os.system('ffmpeg -threads 0 -i "/home/ubuntu/temp_videos/%s/%s" -preset ultrafast -vf scale=320:240,"boxblur=6:4:cr=2:ar=2",format=yuv422p  -an "/home/ubuntu/temp_videos/%s/overredacted_%s"' % (zips_id, video, zips_id, video))
                
                upload_to_youtube('/home/ubuntu/temp_videos/'+zips_id+'/overredacted_'+video, youtube_token)
                os.system('rm "/home/ubuntu/temp_videos/'+zips_id+'/'+video+'"')
                os.system('rm "/home/ubuntu/temp_videos/'+zips_id+'/overredacted_'+video+'"')
                
                #send_short_email(userid, '%s overblured and uploaded to Youtube' % (video))
                
    os.system('rm -rf /home/ubuntu/temp_videos/'+zips_id)
    #print 'from', form['from']
    #return Response('')

    
@app.route('/incoming_email/', methods=['POST'])
def incoming_email():
    thread.start_new_thread(incoming_email_thread, (request.form,))    
    return Response('')
    
@socketio.on('message')
def handle_message(message):
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    #print message
    send(message)

@socketio.on('connect', namespace='/test')
def test_connect():
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    emit('my response', {'data': 'Connected'})

@socketio.on('framize', namespace='/test')
def framize(message):
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    #print message['data']
    video = message['data']
    emit('framization_status', {'data': 'Downloading the video to framize'})
    random_filename = get_md5(video)
    emit('redaction_video_id', {'data': random_filename})
    video_path = '/home/ubuntu/temp_videos/%s.mp4' % (random_filename)
    target_dir = '/home/ubuntu/temp_videos/%s' % (random_filename)
    if os.path.isdir(target_dir):
        emit('framization_status', {'data': 'Already framized. Ready to redact.'})
        
        return
    os.system('mkdir "%s"' % (target_dir))
    bucket.get_key(video).get_contents_to_filename(video_path)
    emit('framization_status', {'data': 'Starting framization'})
    os.system('ffmpeg -i "%s" -y "%s/%%08d.jpg" 1>&- 2>&-  &' % (video_path, target_dir))
    os.system('mkdir %s_contour' % (target_dir))
    os.system('ffmpeg -i "%s" -y -preset ultrafast -vf "edgedetect=low=0.25:high=0.5",format=yuv422p -an %s' % (video_path, video_path[:-4]+'_contour.mp4'))
    os.system('ffmpeg -i "%s" -y "%s_contour/%%08d.jpg"' % (video_path[:-4]+'_contour.mp4', target_dir))
    #os.system('ffmpeg -i "%s" -y "%s/%%08d.jpg" &' % (video_path, target_dir))
    
    number_of_frames = os.popen("ffprobe -select_streams v -show_streams /home/ubuntu/temp_videos/%s.mp4 2>/dev/null | grep nb_frames | sed -e 's/nb_frames=//'" % (random_filename)).read()
    #print number_of_frames
    number_of_frames = int(number_of_frames)
    import time
    while True:
        number_of_files = len(os.listdir(target_dir))
        percentage = '{0:.0%}'.format( float(number_of_files) / float(number_of_frames))
        #print number_of_files, number_of_frames
        #print 'Framizing. %s done' % (percentage) 
        emit('framization_status', {'data': 'Framizing. %s done' % (percentage)})
        gevent.sleep(1) # see http://stackoverflow.com/questions/18941420/loop-seems-to-break-emit-events-inside-namespace-methods-gevent-socketio
        if number_of_files >= number_of_frames:
            break
    
    put_folder_on_s3(target_dir, random_filename+'_frames', get_setting('bucket_name'), get_setting('access_key_id'), get_setting('secret_access_key'))
     
    
def track_object(namespace, frames, start_rectangle, frame, box_id, direction, handle_head_to_side=True, throw_out_weirdness=True):
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    conn = r.connect( "localhost", 28015).repl()
    db.table('track_status').insert({'id': box_id, 'stop': False}, conflict='update').run(conn) # this allows us to stop tracking from web interface 
    tracker = dlib.correlation_tracker()
    positions = []
    number_of_frames = len(frames)
    last = None
    
    history = [[int(start_rectangle.left()), int(start_rectangle.top()), int(start_rectangle.width()), int(start_rectangle.height())]]
    for k, f in enumerate(frames):
        if db.table('track_status').get(box_id).run(conn)['stop']:
            return
        #print "Processing Frame %s (%s)" % (k, f)
        #print f
        img = io.imread(f)
        
        # We need to initialize the tracker on the first frame
        if k == 0:
            # Start a track on the juice box. If you look at the first frame you
            # will see that the juice box is contained within the bounding
            # box (74, 67, 112, 153).
            if False:
                left = start_rectangle.left() - 10
                top =  start_rectangle.top() - 10
                right = start_rectangle.right() + 10
                bottom = start_rectangle.bottom() + 10
                #print left, top, right, bottom
                start_rectangle = dlib.rectangle(left, top, right, bottom)
                #print [int(start_rectangle.left())-10, int(start_rectangle.top())-10, int(start_rectangle.width())+20, int(start_rectangle.height())+20]
                #start_rectangle = dlib.rectangle(int(start_rectangle.left())-10, int(start_rectangle.top())-10, int(start_rectangle.width())+20, int(start_rectangle.height())+20)
            tracker.start_track(img, start_rectangle)
            percentage = r'0%'
            namespace.emit('track_result', {'frame': frame + k, 'coordinates': history[0], 'box_id': box_id, 'percentage': percentage, 'direction': direction})
        else:
            # Else we just attempt to track from the previous frame
            tracker.update(img)
            position = tracker.get_position()
            position = [int(position.left()), int(position.top()), int(position.width()), int(position.height())]
            #position = [int(position.left())+10, int(position.top())+10, int(position.width())-20, int(position.height())-20]
            #print 'last', last
            how_far = 20
            anomaly = 30
            if handle_head_to_side:
                if len(history) > (how_far + 2):
                    #for i in range(0,2): # both horizontal (0) and vertical (1)
                    for i in range(0,1): # just horizontal 
                        if (abs(position[i] - history[k-how_far][i])) > anomaly: # detect that box has moved significantly to the right 
                            if position[i] > history[k-how_far][i]:
                                d = position[0 + i] - history[k-how_far][0 + i] + history[k-how_far][2] 
                            else:
                                d = history[k-how_far][0 + i] - position[0 + i] + history[k-how_far][2] 
                            position = history[k-how_far]
                            position[2 + i] = d
                            for i in range(how_far):
                                
                                #print {'frame': frame + k - i, 'coordinates': position, 'box_id': box_id, 'percentage': percentage, 'direction': direction}
                                namespace.emit('track_result', {'frame': frame + k - i, 'coordinates': position, 'box_id': box_id, 'percentage': percentage, 'direction': direction})
                            left = int(position[0])
                            top =  int(position[1])
                            right = left + int(position[2])
                            bottom = top + int(position[3])
                            #print left, top, right, bottom
                            if right > left and bottom > top:
                                start_rectangle = dlib.rectangle(left, top, right, bottom)
                                #print start_rectangle
                                
                                tracker = dlib.correlation_tracker()
                                tracker.start_track(img, start_rectangle)
                            
            if throw_out_weirdness:
                if last:
                    throw_out = False
                    for i, value in enumerate(last):
                        #print 'abs', abs(value - position[i])
                        if abs(value - position[i]) > 10: # helps ensure we don't go way off track have seen tracker go completely right of head when head goes to side
                            position = last
                            throw_out = True
                            left = int(position[0])
                            top =  int(position[1])
                            right = left + int(position[2])
                            bottom = top + int(position[3])
                            start_rectangle = dlib.rectangle(left, top, right, bottom)
                            tracker = dlib.correlation_tracker()
                            tracker.start_track(img, start_rectangle)
                            break
                    if not throw_out:
                        last = position                 
                            
                else:
                    last = position
            #last = position
            #if k % 2 == 99:
            if False:
                left = int(position[0])-10
                top =  int(position[1])-10
                right = int(position[0]) + int(position[2]) + 10
                bottom = int(position[1]) + int(position[3]) + 10
                #print [left, top, right, bottom]
                start_rectangle = dlib.rectangle(left, top, right, bottom)
                tracker = dlib.correlation_tracker()
                tracker.start_track(img, start_rectangle)
                padding = 10*k
                position = [position[0]+padding, position[1]+padding, position[2]-(2*padding), position[3]-(2*padding)]
                #print 'MODIFIED POSITION', position
            percentage = '{0:.0%}'.format( float(k) / float(number_of_frames))
            if direction == 'backwards':
                k = -1 * k
            history.append(position)
            
            namespace.emit('track_result', {'frame': frame + k, 'coordinates': position, 'box_id': box_id, 'percentage': percentage, 'direction': direction})
            #print position
            #print dir(position)
@socketio.on('track_forwards_and_backwards', namespace='/test')            
def track_forwards_and_backwards(message):
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    #print message 
    video_hash = get_md5(message['video_id'])
    box_id = message['box_id']
    #return
    #video = message['data']
    # Path to the video frames
    video_folder = 'frames'

    # Create the correlation tracker - the object needs to be initialized
    # before it can be used
    tracker = dlib.correlation_tracker()
    positions = []
    
    # We will track the frames as we load them off of disk
    frame = message['frame'] + 1
    #if frame == 0:
    #    frame = 1
    total_frames = len(os.listdir('/home/ubuntu/temp_videos/%s/' % (video_hash)))
    plusminusframes = 24 * 60 * 10 # ten minutes
    if frame + plusminusframes < total_frames:
        end = frame + plusminusframes
    else:
        end = total_frames
    # remove later 
    end = total_frames
    forward_frames = ['/home/ubuntu/temp_videos/%s_contour/%08d.jpg' % (video_hash, i) for i in range(frame, end)]
    if frame - plusminusframes > 0:
        end = frame - plusminusframes
    else:
        end = 0
    end = 0 
    backward_frames = ['/home/ubuntu/temp_videos/%s_contour/%08d.jpg' % (video_hash, i) for i in range(frame, end, -1) if i > 0]
    #print forward_frames
    #print frames
    forward_positions = []
    backward_positions = []
    #print map(int,message['coordinates'])
    c = message['coordinates']
    start_rectangle = dlib.rectangle(c['left'], c['top'], c['right'], c['bottom'])
    #print start_rectangle
    import thread
    #bbox = '%s,%s,%s,%s' % (c['left'], c['top'], c['right'] - c['left'], c['bottom'] - c['top'])
    #print 'python ../CMT/run.py --quiet --no-preview --skip %s --bbox %s ../temp_videos/aba2eafda7e4e086fcab262c792e757e/{:08d}.jpg' % (frame, bbox)
    #os.system('python ../CMT/run.py --quiet --no-preview --skip %s --bbox %s ../temp_videos/aba2eafda7e4e086fcab262c792e757e/{:08d}.jpg' % (frame, bbox))    
    thread.start_new_thread(track_object, (request.namespace, forward_frames, start_rectangle, frame, box_id, 'forwards'))
    thread.start_new_thread(track_object, (request.namespace, backward_frames, start_rectangle, frame, box_id, 'backwards'))
    
    #return HttpResponse(json.dumps({'backward_positions': backward_positions, 'forward_positions': forward_positions, 'max_width': max_width, 'max_height': max_height}), content_type='application/json')            

@socketio.on('track_forwards', namespace='/test')            
def track_forwards(message):
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    #print message 
    video_hash = get_md5(message['video_id'])
    box_id = message['box_id']
    #return
    #video = message['data']
    # Path to the video frames
    video_folder = 'frames'

    # Create the correlation tracker - the object needs to be initialized
    # before it can be used
    tracker = dlib.correlation_tracker()
    positions = []
    
    # We will track the frames as we load them off of disk
    frame = message['frame']
    if frame == 0:
        frame = 1
    total_frames = len(os.listdir('/home/ubuntu/temp_videos/%s/' % (video_hash)))
    plusminusframes = 1800
    if frame + plusminusframes < total_frames:
        end = frame + plusminusframes
    
    else:
        end = total_frames
    end = total_frames-100
    forward_frames = ['/home/ubuntu/temp_videos/%s/%08d.jpg' % (video_hash, i) for i in range(frame, end)]
    
    #print forward_frames
    #print frames
    forward_positions = []
    backward_positions = []
    #print map(int,message['coordinates'])
    c = message['coordinates']
    start_rectangle = dlib.rectangle(c['left'], c['top'], c['right'], c['bottom'])
    #print start_rectangle
    import thread
     
    thread.start_new_thread(track_object, (request.namespace, forward_frames, start_rectangle, frame, box_id, 'forwards'))

@socketio.on('track_backwards', namespace='/test')            
def track_backwards(message):
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    #print message 
    video_hash = get_md5(message['video_id'])
    box_id = message['box_id']
    #return
    #video = message['data']
    # Path to the video frames
    video_folder = 'frames'

    # Create the correlation tracker - the object needs to be initialized
    # before it can be used
    tracker = dlib.correlation_tracker()
    positions = []
    
    # We will track the frames as we load them off of disk
    frame = message['frame']
    if frame == 0:
        frame = 1
    total_frames = len(os.listdir('/home/ubuntu/temp_videos/%s/' % (video_hash)))
    plusminusframes = 1800
    
    if frame - plusminusframes > 0:
        end = frame - plusminusframes
    else:
        end = 0
    end = 0
    backward_frames = ['/home/ubuntu/temp_videos/%s/%08d.jpg' % (video_hash, i) for i in range(frame, end, -1) if i > 0]
    
    #print frames
    forward_positions = []
    backward_positions = []
    #print map(int,message['coordinates'])
    c = message['coordinates']
    start_rectangle = dlib.rectangle(c['left'], c['top'], c['right'], c['bottom'])
    #print start_rectangle
    
    thread.start_new_thread(track_object, (request.namespace, backward_frames, start_rectangle, frame, box_id, 'forwards'))

def generate_redacted_video_thread(namespace, message):
    namespace.emit('framization_status', {'data': 'Generating redacted video'})
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    import cv2
    coords = message['coordinates'] # coordinates are a dictionary of frame -> dictionary of box id -> coordinates
    #print coords
    video_hash = get_md5(message['video_id'])
    os.system('rm -rf /home/ubuntu/temp_videos/redacted_%s' % (video_hash))
    os.system('cp -r /home/ubuntu/temp_videos/%s /home/ubuntu/temp_videos/redacted_%s' % (video_hash, video_hash)) # we'll modify frames in the redacted folder
    sorted(os.listdir('/home/ubuntu/temp_videos/redacted_%s' % (video_hash)))
    frames = sorted(os.listdir('/home/ubuntu/temp_videos/redacted_%s' % (video_hash)))
    number_of_frames = len(frames)
    for i, frame in enumerate(frames):
    #for i, frame in enumerate([]):
        i += 1
        percentage = '{0:.0%}'.format( float(i) / float(number_of_frames))
        #print 'Framizing. %s done' % (percentage) 
        namespace.emit('framization_status', {'data': 'Applying redactions to each frame %s done' % (percentage)})
        if not frame.endswith('.jpg'):
            continue
        frame = str(int(frame[:-4]))
        #print frame
        if frame in coords:
            
            filename = '/home/ubuntu/temp_videos/redacted_%s/%08d.jpg' % (video_hash, int(frame))
            #print filename
            img = cv2.imread(filename)
            for c in coords[frame].values():
                # c is left, top, width, height
                x1 = c[0]
                if x1 < 0:
                    x1 = 0
                if x1 > 720:
                    x1 = 718
                    
                y1 = c[1] 
                if y1 < 0:
                    y1 = 0
                if y1 > 600:
                    y1 = 558
                x2 = x1 + c[2]
                if x2 < 0:
                    x2 = 0
                if x2 > 720:
                    x2 = 718
                y2 = y1 + c[3]
                if y2 < 0:
                    y2 = 0
                if y2 > 600:
                    y2 = 558
                cv2.rectangle(img, (x1, y1), (x2, y2), (0,0,0), -1) # -1 means fill
            cv2.imwrite(filename,img)
    namespace.emit('framization_status', {'data': 'Now merging the redacted frames into a video'})
    os.system('ffmpeg -start_number 1 -i /home/ubuntu/temp_videos/redacted_%s/%%08d.jpg -y -r 24 -vcodec libx264 -preset ultrafast -b:a 32k -strict -2 /home/ubuntu/temp_videos/redacted_%s.mp4' % (video_hash, video_hash))
    namespace.emit('framization_status', {'data': 'Video created'})
    userid = message['video_id'][:message['video_id'].index('/')]
    os.system('ffmpeg -i "/home/ubuntu/temp_videos/%s.mp4" -y -vn -acodec copy -b:a 32k -strict -2 /home/ubuntu/temp_videos/%s.aac' % (video_hash, video_hash))
    audio_redactions = message['audio_redactions']
    audio_redactions = ','.join(["volume=enable='between(t,%s,%s)':volume=0" % (ar['start'], ar['stop']) for ar in audio_redactions])
    #print 'ffmpeg -i /home/ubuntu/temp_videos/%s.aac -y -af "%s" -b:a 32k -strict -2 /home/ubuntu/temp_videos/redacted_%s.aac' % (video_hash, audio_redactions, video_hash)
    os.system('ffmpeg -i /home/ubuntu/temp_videos/%s.aac -y -af "%s" -b:a 32k -strict -2 /home/ubuntu/temp_videos/redacted_%s.aac' % (video_hash, audio_redactions, video_hash))
    os.system('ffmpeg -i /home/ubuntu/temp_videos/redacted_%s.mp4 -i /home/ubuntu/temp_videos/redacted_%s.aac -y -r 24 -vcodec libx264 -preset ultrafast -b:a 32k -strict -2 /home/ubuntu/temp_videos/redacted_with_audio_%s.mp4' % (video_hash, video_hash, video_hash))
    upload_to_s3('/home/ubuntu/temp_videos/redacted_with_audio_%s.mp4' % (video_hash), userid)
    youtube_token = get_users_youtube_token(userid)
    namespace.emit('framization_status', {'data': 'Uploaded', 'filename': '%s/redacted_with_audio_%s.mp4' % (userid, video_hash)})
    upload_to_youtube('/home/ubuntu/temp_videos/redacted_with_audio_%s.mp4' % (video_hash), youtube_token)
    namespace.emit('framization_status', {'data': 'Uploaded to Youtube'})    
    
@socketio.on('generate_redacted_video', namespace='/test') 
def generate_redacted_video(message):
    #print 'generate_redacted_video'     
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    thread.start_new_thread(generate_redacted_video_thread, (request.namespace, message))          
    
@socketio.on('stop_tracking', namespace='/test')
def stop_tracking(message):
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    db.table('track_status').get(message['box_id']).update({'stop': True}).run(conn)

def do_detect_upper_body(namespace, video_id, start_frame):
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    # video_id should be userid/filename
    video_hash = get_md5(video_id)
    s3_prefix = get_md5(video_id)+'_frames'
    total_frames = len(os.listdir('/home/ubuntu/temp_videos/%s/' % (video_hash)))
    for i, frame in enumerate(range(start_frame, total_frames)):
        
        #if i > 10:
        #    return
        if i % 1800 == 0: # My AWS account is allotted 1,800 lambda functions running at one time running time is about 40 seconds to be safe wait 60 seconds
            gevent.sleep(60)
        # To ensure don't rack up huge bill because someone clicked over and over and over
        filename = '%s_frames/%08d.jpg' % (video_hash, frame)
        if db.table('upperbody_detections').get(filename).run(conn):
            print 'already did upper body detection'
            continue
        lambdaConn = boto.connect_awslambda(get_setting('access_key_id'), get_setting('secret_access_key'), region=boto.awslambda.get_regions('awslambda')[0])
        #print i, frame, lambdaConn.invoke_async('detectUpperBody', json.dumps({'filename': filename}))
        
    return 

@socketio.on('get_upper_body_detections', namespace='/test')
def get_upper_body_detections(message):
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    detections = db.table('upperbody_detections').run(conn)
    detections = [(int(item['id'][item['id'].find('/')+1:item['id'].find('.')]), item['coordinates']) for item in detections if item['id'].startswith(message['video'])]
    #print detections
    for item in detections:
        emit('upper_body_detections', {'frame': item[0], 'detections': item[1]})
     
    
@socketio.on('detect_upper_body', namespace='/test')     
def detect_upper_body(message): 
    conn = r.connect( "localhost", 28015).repl(); db = r.db('redactvideodotorg');
    #print 'facilitate_detect_upper_body'
    #print message 
    thread.start_new_thread(do_detect_upper_body, (request.namespace, message['video_id'], message['start_frame']))

def gd(namespace, message):
    import argparse
    import datetime
    import imutils
    import time
    import cv2
    import numpy as np
    import os
         
    firstFrame = None
    detections = [[]]

    # loop over the frames of the video
    i = -1
    grays = []
    groups = {}
    centers_to_groups = {}
    group_i = 0
    saved_frames = []
    #print message['data']
    video = message['data']
    random_filename = get_md5(video)
    video_path = '/home/ubuntu/temp_videos/%s.mp4' % (random_filename)
    bucket.get_key(video).get_contents_to_filename(video_path)
    camera = cv2.VideoCapture(video_path)
    grays = []
    # initialize the first frame in the video stream
    firstFrame = None
    avg = None
    detections = [[]]
    number_of_detections_per_frame = []
    stopped_count = 0
    started_count = 0
    confirmed_stopped = False
    import random
    import string
    #frames_folder = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))
    #os.system('mkdir /home/ubuntu/temp_videos/%s/' % (frames_folder))
    # loop over the frames of the video
    while True:
        #print i
        i += 1
        # grab the current frame and initialize the occupied/unoccupied
        # text
        (grabbed, frame) = camera.read()
        text = "Unoccupied"

        # if the frame could not be grabbed, then we have reached the end
        # of the video
        if not grabbed:
            break

        # resize the frame, convert it to grayscale, and blur it
        #frame = imutils.resize(frame, width=500)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (25, 25), 0)
        
        blurred = cv2.GaussianBlur(frame, (35, 35), 0)
        
        for j in range(2):
            blurred = cv2.GaussianBlur(blurred, (35, 35), 0)
        # if the first frame is None, initialize it
        grays.append(gray)
        if firstFrame is None:
            firstFrame = gray
        #    continue
        #elif (i > 2 and not confirmed_stopped):
        #    firstFrame = grays[i - 2]

        # compute the absolute difference between the current frame and
        # first frame
        frameDelta = cv2.absdiff(firstFrame, gray)
        #if avg is None:
        #    #print "[INFO] starting background model..."
        #    avg = gray.copy().astype("float")
        #    continue
        #cv2.accumulateWeighted(gray, avg, 0.5)
        #frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))
        thresh = cv2.threshold(frameDelta, 25, 255, cv2.THRESH_BINARY)[1]

        # dilate the thresholded image to fill in holes, then find contours
        # on thresholded image
        thresh = cv2.dilate(thresh, None, iterations=10)
        (cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE)
        frames_detections = []
        # loop over the contours
        areas = []
        new_centers_to_groups = {}
        for c in cnts:
            # compute the bounding box for the contour, draw it on the frame,
            # and update the text
            (x, y, w, h) = cv2.boundingRect(c)
            #print w, h
            #areas.append((w*h, w, h))
            #detections.append(((x, y, w, h), i))
            (x, y, w, h) = cv2.boundingRect(c)
            center = (x + int(float(w)/2), y + int(float(h)/2))
            frames_detections.append({'rect': (x, y, w, h), 'center': center})
            
            #print centers_to_groups
            if i > 0:
                for detection in detections[i-1]:
                    (x2, y2, w2, h2) = detection['rect']
                    center2 = detection['center']
                    #center2 = (x + int(float(w)/2), y + int(float(h)/2))
                    centers_close = abs(center2[0] - center[0]) < 50 and abs(center2[1] - center[1]) < 50
                    corners_close = abs(x2 - x) < 20 or abs(y2 - y) < 20 or abs((x2 + w2) - (x + w)) < 20 or abs((y2 + h2) - (y + h)) < 20 
                    area_close = abs((w2 * h2) - (w * h)) < 150
                    size_close = True
                    if w2 > w:
                        if w / float(w2) < 0.33:
                        
                            size_close = False
                    else:
                        if w2 / float(w) < 0.33:
                            size_close = False
                    if h2 > h:
                        if h / float(h2) < 0.33:
                        
                            size_close = False
                    else:
                        if h2 / float(h) < 0.33:
                            size_close = False
                    #if (centers_close or corners_close) and not size_close:
                    #    #print "size not close"
                    if (centers_close or corners_close) and size_close:
                    #if centers_close:
                    #if (centers_close or corners_close):
                        #print 'true'
                        #print i, (x, y, w, h), center, (x2, y2, w2, h2), center2
                        if (x2, y2, w2, h2) in centers_to_groups:
                            #print True, centers_to_groups[(x2, y2, w2, h2)]
                            groups[centers_to_groups[(x2, y2, w2, h2)]].append(((x, y, w, h), center, i))
                            #namespace.emit('background_subtraction_detection_group', {'group': centers_to_groups[(x2, y2, w2, h2)], 'coords': (x2, y2, w2, h2), 'frame': i})
                            new_centers_to_groups[(x, y, w, h)] = centers_to_groups[(x2, y2, w2, h2)]
                        else:
                            groups[group_i] = [((x2, y2, w2, h2), center2, i-1), ((x, y, w, h), center, i)]
                            namespace.emit('background_subtraction_detection_group', {'group': group_i, 'coordinates': (x2, y2, w2, h2), 'frame': i-1})
                            #namespace.emit('background_subtraction_detection_group', {'group': group_i, 'coords': (x, y, w, h), 'frame': i})
                            new_centers_to_groups[(x, y, w, h)] = group_i
                            group_i += 1
        if areas:
            #print stopped_count
            largest = sorted(areas, key=lambda x: x[0], reverse=True)[0]
            #print largest[1], frame.shape[1]-120, largest[2], frame.shape[0]-120
            if (largest[1] > frame.shape[1]-120 and largest[2] > frame.shape[0]-120):
                #print 'yes'
                firstFrame = gray
        detections.append(frames_detections)
        centers_to_groups = new_centers_to_groups.copy()    
    
@socketio.on('group_detections', namespace='/test')     
def group_detections(message):
    thread.start_new_thread(gd, (request.namespace, message))

            
                
                
        
@socketio.on('broadcast', namespace='/broadcast_everything')     
def broadcast(message):    
    emit('broadcast', message, broadcast=True)

@app.route('/broadcast_everything/', methods=['GET'])         
def broadcast_everything():
    
    return render_template('broadcast_everything.html')
    
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=80)