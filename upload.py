import requests
from os import fstat
import json

def upload_to_youtube(file_path, token):

    fi = open(file_path)

    base_headers = {
        'Authorization': '%s %s' % ('Bearer',
                                    token),
        'content-type': 'application/json'
    }

    initial_headers = base_headers.copy()
    initial_headers.update({
        'x-upload-content-length': fstat(fi.fileno()).st_size,
        'x-upload-content-type': 'video/mp4'
    })
    initial_resp = requests.post(
        'https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status,contentDetails',
        headers=initial_headers,
        data=json.dumps({
            'snippet': {
                'title': 'my title',
            },
            'status': {
                'privacyStatus': 'public',
                'embeddable': True
            }
        })
    )
    print initial_resp.text
    upload_url = initial_resp.headers['location']
    resp = requests.put(
        upload_url,
        headers=base_headers,
        data=fi
    )
    fi.close()