import os
import json
import boto3

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    bucket = event['bucket']
    in_key = event['in_key']
    in_key_base =  os.path.basename(in_key)
    out_key = event['out_key']
    out_key_base = os.path.basename(out_key)
    options = event['options']
    print bucket, in_key, in_key_base
    s3_client.download_file(bucket, in_key, '/tmp/'+in_key_base)
    print 'downloaded'
    cmd = '$LAMBDA_TASK_ROOT/ffmpeg -i /tmp/%s %s /tmp/%s > /tmp/log.txt 2>&1' % (in_key_base, options, out_key_base)
    print cmd
    os.system(cmd)
    print 'cmd done'
    s3_client.upload_file('/tmp/'+out_key_base, bucket, out_key)
    print 'uploaded'
    with open('/tmp/log.txt') as f:
        print f.read()
    return
    
