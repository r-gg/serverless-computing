import io
from flask import Flask, jsonify, request
import sklearn
from minio import Minio
from minio.error import S3Error
import numpy as np
import json

import logging as log

app = Flask(__name__)

@app.route('/setup-minio')
def minio_setup():

    client = Minio(
        "minio-operator9000.minio-dev.svc.cluster.local:9000",
        access_key="minioadmin1",
        secret_key="minioadmin1",
        secure=False
    )
    print("connected to the client")

    new_bucket_name = "my-test-bucket"
    res_string = ""
    try: 
        buckets = client.list_buckets()

        


        # Create new bucket and set anonymous RW access policy
        if new_bucket_name not in [bucket.name for bucket in buckets]:
            client.make_bucket(new_bucket_name)

            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": ["s3:GetObject", "s3:PutObject"],
                        "Resource": f"arn:aws:s3:::{new_bucket_name}/*"
                    }
                ]
            }

            # Apply the policy to the bucket
            client.set_bucket_policy(new_bucket_name, json.dumps(policy))
            res_string += f"Created bucket: {new_bucket_name}\n"
        else:
            res_string += f"Bucket {new_bucket_name} already exists. \n" 
        
    except S3Error as err:
        print(err)
        
    print("made the bucket")

    # Attempt to upload from an anonymous client
    anon_client = Minio("minio-operator9000.minio-dev.svc.cluster.local:9000",
                        secure=False)
    
    print("connected with anon client")
    try:
        result = anon_client.put_object(
            new_bucket_name, "my-object", io.BytesIO(b"hello"), 5, 
        )
        res_string += "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        )
    except S3Error as err:
        print(err)

    
    return res_string, 200

@app.route('/service')
def service():
    print("Welcome to notification service")
    return 'Notification Service',200

@app.route('/sendEmail',methods=["POST"])
def sendEmail():
  return jsonify({"Accepted":202}),202
    
        
if __name__ == '__main__':
	app.run(debug=True)