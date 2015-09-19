import os
# framize means convert a video to its frames
def framize(video_path, target_dir):
    target_dir = target_dir.rstrip('/') # strip / because / is added in the line below
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    os.system('ffmpeg -i %s %s/%%08d.jpg' % (video_path, target_dir))

def put_folder_on_s3(source_path, prefix, bucket_name, aws_access_key_id, aws_access_key_secret):
    # code from https://gist.github.com/SavvyGuard/6115006
    import boto
    import boto.s3

    import os.path
    import sys

    # Fill these in - you get them when you sign up for S3
    AWS_ACCESS_KEY_ID = aws_access_key_id
    AWS_ACCESS_KEY_SECRET = aws_access_key_secret
    # Fill in info on data to upload
    # destination bucket name
    bucket_name = bucket_name
    # source directory
    sourceDir = source_path
    # destination directory name (on s3)
    destDir = prefix.strip('/')+'/'

    #max size in bytes before uploading in parts. between 1 and 5 GB recommended
    MAX_SIZE = 20 * 1000 * 1000
    #size of parts when uploading in parts
    PART_SIZE = 6 * 1000 * 1000

    conn = boto.connect_s3(AWS_ACCESS_KEY_ID, AWS_ACCESS_KEY_SECRET)

    bucket = conn.create_bucket(bucket_name,
            location=boto.s3.connection.Location.DEFAULT)


    uploadFileNames = []
    for (sourceDir, dirname, filename) in os.walk(sourceDir):
        uploadFileNames.extend(filename)
        break

    def percent_cb(complete, total):
        sys.stdout.write('.')
        sys.stdout.flush()

    for i, filename in enumerate(uploadFileNames):
        print i, len(uploadFileNames)
        sourcepath = os.path.join(sourceDir, filename)
        destpath = os.path.join(destDir, filename)
        print 'Uploading %s to Amazon S3 bucket %s' % \
               (sourcepath, bucket_name)

        filesize = os.path.getsize(sourcepath)
        if filesize > MAX_SIZE:
            print "multipart upload"
            mp = bucket.initiate_multipart_upload(destpath)
            fp = open(sourcepath,'rb')
            fp_num = 0
            while (fp.tell() < filesize):
                fp_num += 1
                print "uploading part %i" %fp_num
                mp.upload_part_from_file(fp, fp_num, cb=percent_cb, num_cb=10, size=PART_SIZE)

            mp.complete_upload()

        else:
            print "singlepart upload"
            k = boto.s3.key.Key(bucket)
            k.key = destpath
            k.set_contents_from_filename(sourcepath,
                    cb=percent_cb, num_cb=10)
                    
if __name__ == '__main__':
    import rethinkdb as r
    conn = r.connect( "localhost", 28015).repl()
    db = r.db('redactvideodotorg')
    def get_setting(setting):
        try:
            return db.table('settings').get(setting).run(conn)['value']   
        except:
            return '' 
    #framize('/home/ubuntu/temp_videos/QIGPUX.mp4', '/home/ubuntu/temp_videos/S/')
    import os
    command = 'aws 	--aws-access-key %s	--aws-secret-key %s s3 sync /home/ubuntu/temp_videos/S/ s3://redactvideodotorg/test_framization_2' % (get_setting('access_key_id'), get_setting('secret_access_key'))
    print command
    #put_folder_on_s3('/home/ubuntu/temp_videos/S/', get_setting('bucket_name'), 'test_framization', get_setting('access_key_id'), get_setting('secret_access_key'))
            
    