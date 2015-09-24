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
print conn
from boto.s3.connection import S3Connection
from boto.s3.key import Key
import os,sys
import requests
import dlib
import glob
from skimage import io
from utils.video import put_folder_on_s3
import thread

def get_setting(setting):
    try:
        return db.table('settings').get(setting).run(conn)['value']   
    except:
        return ''    

# Need to wait for RethinkDB to be running
# in rc.local there's no wait between starting rethinkdb and
# starting this script
while True:
    try:
        s3conn = S3Connection(get_setting('access_key_id'), get_setting('secret_access_key'))
        bucket = s3conn.get_bucket(get_setting('bucket_name'))
        break
    except:
        pass

from upload import upload_to_youtube
def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def is_logged_in(request):
    if request.cookies.get('session'):
        if Response(db.table('sessions').get(request.cookies.get('session')).run(conn)['userid']):
            return True
        else:
            return False
    else:
        return False
 
def get_users_random_id(userid):
    results = list(db.table('random_ids_for_users').filter({'userid': userid}).run(conn))
    if results:
        return results[0]['id']
    else:
        random_id = id_generator()
        db.table('random_ids_for_users').insert({'id': random_id, 'userid': userid}).run(conn)
        return random_id
 
@app.route('/')
def index():
    context = {}
    context['google_analytics_tracking_id'] = get_setting('google_analytics_tracking_id')
    if is_logged_in(request):
        
        user_id = db.table('sessions').get(request.cookies.get('session')).run(conn)['userid']
        context['userid'] = user_id
        context['users_random_id'] = get_users_random_id(user_id)
        print user_id
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
    userid = db.table('sessions').get(request.cookies.get('session')).run(conn)['userid']
    for video in bucket.list(userid):
        
        print video, video.name
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
    from utils.video import put_folder_on_s3
    userid = db.table('sessions').get(request.cookies.get('session')).run(conn)['userid']
    for video in bucket.list(userid):
        
        print video, video.name
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
    code = request.args['code']
    t = requests.post(
    'https://accounts.google.com/o/oauth2/token',
    data={'code': code, 'client_id': get_setting('google_client_id'), 'client_secret': get_setting('google_client_secret'), 'redirect_uri': 'http://redactvideo.org/youtube_oauth_callback/', 'grant_type': 'authorization_code'})
    data = t.json()
    user_id = db.table('sessions').get(request.cookies.get('session')).run(conn)['userid']
    db.table('users').get(user_id).update({'youtube_token': data['access_token'], 'youtube_refresh_token': data['refresh_token']}).run(conn)

    
    return render_template("youtube_callback.html")        

def get_users_youtube_token(user_id):    
    youtube_refresh_token = db.table('users').get(user_id).run(conn)['youtube_refresh_token']
    t = requests.post(
    'https://accounts.google.com/o/oauth2/token',
    data={'client_id': get_setting('google_client_id'), 'client_secret': get_setting('google_client_secret'), 'refresh_token': youtube_refresh_token, 'grant_type': 'refresh_token'})
    data = t.json()
    print data['access_token']
    return data['access_token']
    
@app.route('/overblur_and_publish_all_videos/')
def overblur_and_publish_all_videos():
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
    if is_logged_in(request):
        user_id = db.table('sessions').get(request.cookies.get('session')).run(conn)['userid']
        user_data = db.table('users').get(user_id).run(conn)
        if user_data['is_admin']: 
            settings = [{'id': item[0], 'value': item[1]} for item in request.form.items()]
            db.table('settings').insert(settings, conflict='update').run(conn)
            return Response(json.dumps({'success': True}))

@app.route('/change_user_settings/', methods=['POST'])
def change_user_settings():
    print 'runns'
    if is_logged_in(request):
        user_id = db.table('sessions').get(request.cookies.get('session')).run(conn)['userid']
        user_data = db.table('users').get(user_id).run(conn) 
        if user_data.get('settings'):
            settings = user_data['settings']
        else:
            settings = {}
        print 'request data', dict(request.form)
        # sometimes request.form is in the form of {'x': ['value']} instead of
        # {'x': 'value'} so need to convert to
        #  {'x': 'value'}
        form = dict([(item[0], item[1] if isinstance(item[1], basestring) else item[1][0]) for item in request.form.items()])
        settings.update(form)
        print 'settings', settings
        db.table('users').get(user_id).update({'settings': settings}).run(conn)
        print db.table('users').get(user_id).run(conn)
        return Response(json.dumps({'success': True}))            

@app.route('/get_users_s3_buckets/', methods=['GET'])
def get_users_s3_buckets():
    print 'runns'
    if is_logged_in(request):
        user_id = db.table('sessions').get(request.cookies.get('session')).run(conn)['userid']
        user_data = db.table('users').get(user_id).run(conn) 
        settings = user_data.get('settings')
        s3conn_for_user = S3Connection(settings['access_key_id'], settings['secret_access_key'])
        #s3conn_for_user.get_all_buckets()
        return Response(json.dumps({'buckets': s3conn_for_user.get_all_buckets()}))   

        
@app.route('/logout/')        
def logout():
    resp = make_response(redirect('/'))
    resp.set_cookie('session', '', expires=0)
    return resp
        
@app.route('/create_first_user/', methods=['POST'])
def create_first_user():
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
    userid = db.table('two_factor_codes').get(request.args['two_factor_code']).run(conn)['userid']
    user_data = db.table('users').get(userid).run(conn)
    
    session_id = id_generator(30)
    username = userid
    print db.table('sessions').insert({'id': session_id, 'userid': username}).run(conn)
    resp = make_response(redirect('/'))
    resp.set_cookie('session', session_id)
    return resp
    
def is_already_account(email):
    if list(db.table('users').filter({'id': email}).run(conn)):
        return True
    return False
    
    
@app.route('/submit_request_for_account/', methods=['POST'])
def submit_request_for_account():
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
            print status, msg
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
    
    userid = db.table('accounts_to_verify').get(request.args['code']).run(conn)['userid']
    db.table('users').get(userid).update({'verified': True}).run(conn)  
    session_id = id_generator(30)
    username = userid
    print {'id': session_id, 'userid': username}
    print db.table('sessions').insert({'id': session_id, 'userid': username}).run(conn)
    resp = make_response(render_template('create_password.html'))
    resp.set_cookie('session', session_id)
    return resp

@app.route('/create_password/', methods=['POST'])    
def create_password():
    print request.form['retyped_password']
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
    github_signature = request.headers.get('X-Hub-Signature')
    secret = get_setting('github_auto_update_secret')
    import hmac
    from hashlib import sha1
    print request.get_json()
    print secret
    hmac_object = hmac.new(str(secret), request.data, digestmod=sha1)
    if hmac.compare_digest(str(github_signature), 'sha1='+hmac_object.hexdigest()):
        os.system('python autodeploy.py &')
    return Response('')

def upload_to_s3(filepath, userid):
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
    
@app.route('/incoming_email/', methods=['POST'])
def incoming_email():
    # parse the to email address
    m = re.search('"(?P<email>.*)"', request.form['to'])
    email = m.group('email')
    if not email.endswith('@redactvideo.org'):
        return Response('error')
    userto = email.split('@')[0]
    users_random_id = userto[:userto.index('_')]
    userid = db.table('random_ids_for_users').get(users_random_id).run(conn)['userid']
    
    # download the evidence.com html with the url to download the zip file
    m = re.search('(?P<base>https://(.*)\.evidence\.com)/1/uix/public/download/\?package_id=(.*)ver=v2', request.form['text'])
    r = requests.get(m.group(0))
    base_url = m.group('base')
    download_html = r.text
    m = re.search('download_url="(?P<url>.*ver=v2)', download_html)
    zip_download_url = base_url+m.group('url').replace('&amp;', '&')
    print zip_download_url
    # save the zip file
    zips_id = id_generator()
    with open('/home/ubuntu/temp_videos/'+zips_id+'.zip', 'wb') as handle:
        response = requests.get(zip_download_url, stream=True)

        if not response.ok:
            pass

        for block in response.iter_content(1024):
            handle.write(block)
    # unzip the file
    os.system('cd /home/ubuntu/temp_videos/; mkdir zips_id; unzip -d %s -j %s.zip' % (zips_id, zips_id))
    # now need to know what to do with the files
    # e.g. put on S3 or on Youtube
    if '_just_copy_over' in email:
        for video in os.listdir('/home/ubuntu/temp_videos/'+zips_id):
            if not video.endswith('pdf'):
                upload_to_s3('/home/ubuntu/temp_videos/'+zips_id+'/'+video, userid)
    else:
        youtube_refresh_token = db.table('users').get(userid).run(conn)['youtube_refresh_token']
        t = requests.post(
        'https://accounts.google.com/o/oauth2/token',
        data={'client_id': get_setting('google_client_id'), 'client_secret': get_setting('google_client_secret'), 'grant_type': 'refresh_token'})
        data = t.json()
        youtube_token = get_users_youtube_token(userid)
        for video in os.listdir('/home/ubuntu/temp_videos/'+zips_id):
            if not video.endswith('pdf'):
                upload_to_youtube('/home/ubuntu/temp_videos/'+zips_id+'/'+video, youtube_token)
    os.system('rm -rf /home/ubuntu/temp_videos/'+zips_id)
    return Response('')
    
@socketio.on('message')
def handle_message(message):
    print message
    send(message)

@socketio.on('connect', namespace='/test')
def test_connect():
    emit('my response', {'data': 'Connected'})

@socketio.on('framize', namespace='/test')
def test_message(message):
    print message['data']
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
    #os.system('ffmpeg -i "%s" -y "%s/%%08d.jpg" &' % (video_path, target_dir))
    
    number_of_frames = os.popen("ffprobe -select_streams v -show_streams /home/ubuntu/temp_videos/%s.mp4 2>/dev/null | grep nb_frames | sed -e 's/nb_frames=//'" % (random_filename)).read()
    print number_of_frames
    number_of_frames = int(number_of_frames)
    import time
    while True:
        number_of_files = len(os.listdir(target_dir))
        percentage = '{0:.0%}'.format( float(number_of_files) / float(number_of_frames))
        print number_of_files, number_of_frames
        print 'Framizing. %s done' % (percentage) 
        emit('framization_status', {'data': 'Framizing. %s done' % (percentage)})
        gevent.sleep(1) # see http://stackoverflow.com/questions/18941420/loop-seems-to-break-emit-events-inside-namespace-methods-gevent-socketio
        if number_of_files >= number_of_frames:
            break
    
    put_folder_on_s3(target_dir, random_filename+'_frames', get_setting('bucket_name'), get_setting('access_key_id'), get_setting('secret_access_key'))
     
    
def track_object(namespace, frames, start_rectangle, frame, box_id, direction):
    tracker = dlib.correlation_tracker()
    positions = []
    number_of_frames = len(frames)
    last = None
    
    history = [[int(start_rectangle.left()), int(start_rectangle.top()), int(start_rectangle.width()), int(start_rectangle.height())]]
    for k, f in enumerate(frames):
        print "Processing Frame %s (%s)" % (k, f)
        print f
        img = io.imread(f)
        
        # We need to initialize the tracker on the first frame
        if k == 0:
            # Start a track on the juice box. If you look at the first frame you
            # will see that the juice box is contained within the bounding
            # box (74, 67, 112, 153).
            left = start_rectangle.left() - 10
            top =  start_rectangle.top() - 10
            right = start_rectangle.right() + 10
            bottom = start_rectangle.bottom() + 10
            print left, top, right, bottom
            start_rectangle = dlib.rectangle(left, top, right, bottom)
            print [int(start_rectangle.left())-10, int(start_rectangle.top())-10, int(start_rectangle.width())+20, int(start_rectangle.height())+20]
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
            print 'last', last
            how_far = 50
            if False:
                if len(history) > (how_far + 2):
                    for i in range(0,2):
                        if (abs(position[i] - history[k-how_far][i])) > 30: # detect that box has moved significantly to the right 
                            #gevent.sleep(60)
                            if i == 0:
                                width = position[0] - history[k-how_far][0] + history[k-how_far][2] 
                                position = history[k-how_far]
                                position[2] = width
                            else:
                                height = position[1] - history[k-how_far][1] + history[k-how_far][3] 
                                position = history[k-how_far]
                                position[2] = height
                            for i in range(how_far):
                                
                                print {'frame': frame + k - i, 'coordinates': position, 'box_id': box_id, 'percentage': percentage, 'direction': direction}
                                namespace.emit('track_result', {'frame': frame + k - i, 'coordinates': position, 'box_id': box_id, 'percentage': percentage, 'direction': direction})
                            left = int(position[0])
                            top =  int(position[1])
                            right = left + int(position[2])
                            bottom = top + int(position[3])
                            print left, top, right, bottom
                            if right > left and bottom > top:
                                start_rectangle = dlib.rectangle(left, top, right, bottom)
                                print start_rectangle
                                
                                tracker = dlib.correlation_tracker()
                                tracker.start_track(img, start_rectangle)
                            
            if False:
                if last:
                    throw_out = False
                    for i, value in enumerate(last):
                        print 'abs', abs(value - position[i])
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
            if True:
                left = int(position[0])-10
                top =  int(position[1])-10
                right = int(position[0]) + int(position[2]) + 10
                bottom = int(position[1]) + int(position[3]) + 10
                print [left, top, right, bottom]
                start_rectangle = dlib.rectangle(left, top, right, bottom)
                tracker = dlib.correlation_tracker()
                tracker.start_track(img, start_rectangle)
            padding = 10*k
            position = [position[0]+padding, position[1]+padding, position[2]-(2*padding), position[3]-(2*padding)]
            print 'MODIFIED POSITION', position
            percentage = '{0:.0%}'.format( float(k) / float(number_of_frames))
            if direction == 'backwards':
                k = -1 * k
            history.append(position)
            
            namespace.emit('track_result', {'frame': frame + k, 'coordinates': position, 'box_id': box_id, 'percentage': percentage, 'direction': direction})
            #print position
            #print dir(position)
@socketio.on('track_forwards_and_backwards', namespace='/test')            
def track_forwards_and_backwards(message):
    print message 
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
    forward_frames = ['/home/ubuntu/temp_videos/%s/%08d.jpg' % (video_hash, i) for i in range(frame, end)]
    if frame - plusminusframes > 0:
        end = frame - plusminusframes
    else:
        end = 0
    end = 0 
    backward_frames = ['/home/ubuntu/temp_videos/%s/%08d.jpg' % (video_hash, i) for i in range(frame, end, -1) if i > 0]
    print forward_frames
    #print frames
    forward_positions = []
    backward_positions = []
    #print map(int,message['coordinates'])
    c = message['coordinates']
    start_rectangle = dlib.rectangle(c['left'], c['top'], c['right'], c['bottom'])
    print start_rectangle
    import thread
     
    thread.start_new_thread(track_object, (request.namespace, forward_frames, start_rectangle, frame, box_id, 'forwards'))
    thread.start_new_thread(track_object, (request.namespace, backward_frames, start_rectangle, frame, box_id, 'backwards'))
    
    #return HttpResponse(json.dumps({'backward_positions': backward_positions, 'forward_positions': forward_positions, 'max_width': max_width, 'max_height': max_height}), content_type='application/json')            

@socketio.on('track_forwards', namespace='/test')            
def track_forwards(message):
    print message 
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
    
    print forward_frames
    #print frames
    forward_positions = []
    backward_positions = []
    #print map(int,message['coordinates'])
    c = message['coordinates']
    start_rectangle = dlib.rectangle(c['left'], c['top'], c['right'], c['bottom'])
    print start_rectangle
    import thread
     
    thread.start_new_thread(track_object, (request.namespace, forward_frames, start_rectangle, frame, box_id, 'forwards'))

@socketio.on('track_backwards', namespace='/test')            
def track_backwards(message):
    print message 
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
    print start_rectangle
    
    thread.start_new_thread(track_object, (request.namespace, backward_frames, start_rectangle, frame, box_id, 'forwards'))

def generate_redacted_video_thread(namespace, message):
    import cv2
    coords = message['coordinates'] # coordinates are a dictionary of frame -> dictionary of box id -> coordinates
    print coords
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
        print 'Framizing. %s done' % (percentage) 
        namespace.emit('framization_status', {'data': 'Applying redactions to each frame %s done' % (percentage)})
        if not frame.endswith('.jpg'):
            continue
        frame = str(int(frame[:-4]))
        print frame
        if frame in coords:
            
            filename = '/home/ubuntu/temp_videos/redacted_%s/%08d.jpg' % (video_hash, int(frame))
            print filename
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
    upload_to_s3('/home/ubuntu/temp_videos/redacted_%s.mp4' % (video_hash), userid)
    youtube_token = get_users_youtube_token(userid)
    namespace.emit('framization_status', {'data': 'Uploaded', 'filename': '%s/redacted_%s.mp4' % (userid, video_hash)})
    upload_to_youtube('/home/ubuntu/temp_videos/redacted_%s.mp4' % (video_hash), youtube_token)
    namespace.emit('framization_status', {'data': 'Uploaded to Youtube'})    
@socketio.on('generate_redacted_video', namespace='/test') 
def generate_redacted_video(message):     
    thread.start_new_thread(generate_redacted_video_thread, (request.namespace, message))      

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=80)
