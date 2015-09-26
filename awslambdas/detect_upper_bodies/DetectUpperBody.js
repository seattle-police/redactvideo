// dependencies
var async = require('async');
var AWS = require('aws-sdk');
var cv = require('opencv');
var gm = require('gm')
            .subClass({ imageMagick: true }); // Enable ImageMagick integration.
var util = require('util');
var http = require('http');
var querystring = require('querystring');

// constants
var MAX_WIDTH  = 100;
var MAX_HEIGHT = 100;

// face detection properties
var rectColor = [0, 255, 0];
var rectThickness = 2;

// get reference to S3 client 
var s3 = new AWS.S3();
 
exports.handler = function(event, context) {
	// Read options from the event.
	console.log("Reading options from event:\n", util.inspect(event, {depth: 5}));
    var filename = event.filename;
	var srcBucket = 'redactvideodotorg';
	

	// Download the image from S3, run upperbody detection, and send the coordinates to redactvideo app.
	async.waterfall([
		function download(next) {
			// Download the image from S3 into a buffer.
			s3.getObject({
					Bucket: srcBucket,
					Key: filename
				},
				next);
			},
		function tranform(response, next) {
			cv.readImage(response.Body, function(err, im){
                console.log('before HS.xml');
                im.detectObject('HS.xml', {}, function(err, faces) {
                    if (err) throw err;
                    console.log('got pass HS.xml');
                    var detectedRegions = [];
                    for (var i = 0; i < faces.length; i++) {
                        console.log('detected');
                        face = faces[i];
                        detectedRegions.push([face.x, face.y, face.width, face.height]);
                        //im.rectangle([face.x, face.y], [face.x + face.width, face.y + face.height], rectColor, rectThickness);
                    }
                    next(null, response.ContentType, im.toBuffer(), detectedRegions);
                });
            })
            
		},
		function upload(contentType, data, detectedRegions, next) {
			
            var postData = querystring.stringify({
              'filename': filename,
              'detected_regions': JSON.stringify(detectedRegions)
            });

            var options = {
              hostname: 'redactvideo.org',
              port: 80,
              path: '/save_upperbody_detection_coordinates/',
              method: 'POST',
              headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Content-Length': postData.length
              }
            };

            var req = http.request(options, function(res) {
              console.log('STATUS: ' + res.statusCode);
              console.log('HEADERS: ' + JSON.stringify(res.headers));
              res.setEncoding('utf8');
              res.on('data', function (chunk) {
                console.log('BODY: ' + chunk);
              });
              res.on('end', function() {
                console.log('No more data in response.');
                context.done();
              })
            });

            req.on('error', function(e) {
              console.log('problem with request: ' + e.message);
            });

            // write data to request body
            req.write(postData);
            req.end();
        }
		], function (err) {
			
			context.done();
		}
	);
};