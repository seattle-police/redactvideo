from flask import Flask, Response, request, redirect, render_template, make_response
from flask.ext.socketio import SocketIO, emit
import rethinkdb as r
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
    {"acl": "private"}
  ]
}""" % (get_setting('bucket_name'), user_id)
        context['upload'] = {}
        context['upload']['bucket_name'] = get_setting('bucket_name')
        context['upload']['policy'] = base64.b64encode(policy_document)
        context['upload']['access_key_id'] = get_setting('access_key_id')
        context['upload']['signature'] = base64.b64encode(hmac.new(str(get_setting('secret_access_key')), context['upload']['policy'], hashlib.sha1).digest())
        

        rs = bucket.list(user_id)

        context['videos'] = [key.name[key.name.index('/')+1:] for key in rs]
        context['has_authed_with_youtube'] = True if user_data.get('youtube_token') else False
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
        return render_template('index.html')

@app.route('/youtube_oauth_callback/') 
def youtube_oauth_callback():
    return render_template("youtube_callback.html")        
    
@app.route('/save_youtube_oauth_data/') 
def save_youtube_oauth_data():
    user_id = db.table('sessions').get(request.cookies.get('session')).run(conn)['userid']
    db.table('users').get(user_id).update({'youtube_token': request.args['token'][:request.args['token'].index('&')]}).run(conn)
    return Response('worked')

@app.route('/overblur_and_publish_all_videos/')
def overblur_and_publish_all_videos():
    user_id = db.table('sessions').get(request.cookies.get('session')).run(conn)['userid']
    youtube_token = db.table('users').get(user_id).run(conn)['youtube_token']
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

def is_valid_email(email):
    from email.utils import parseaddr
    parsed = parseaddr(email)
    if parsed[0] and parsed[1]:
        return True
    return False
    
def is_already_account(email):
    if list(db.table('users').filter({'id': email}).run(conn)):
        return True
    return False
    
    
@app.route('/submit_request_for_account/', methods=['POST'])
def submit_request_for_account():
    if is_valid_email(request.form['agency_email']):
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
                db.table('accounts_to_verify').insert({'id': secret_code, 'userid': agency_email}, conflict='update').run(conn)
                message = sendgrid.Mail()
                message.add_to(agency_email)
                message.set_subject('Confirm account for RedactVideo')
                message.set_html('<a href="http://redactvideo.org/confirm_account/?code=%s">Click here</a> to confirm your account.' % (secret_code))
                message.set_from('no-reply@redactvideo.org')
                sg = sendgrid.SendGridClient(get_setting('sendgrid_username'), get_setting('sendgrid_password'))
                status, msg = sg.send(message)
                approved = True
            else:
                approved = None # None instead of False so we can tell when admin has made decision
            
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
        
@app.route('/incoming_email/', methods=['POST'])
def incoming_email():
    print request.form
    return Response('')
    
@socketio.on('my event', namespace='/test')
def test_message(message):
    emit('my response', {'data': message['data']})

@socketio.on('my broadcast event', namespace='/test')
def test_message(message):
    emit('my response', {'data': message['data']}, broadcast=True)

@socketio.on('connect', namespace='/test')
def test_connect():
    print 
    emit('my response', {'data': 'Connected'})

@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=80)
