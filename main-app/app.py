import io
import os
from flask import Flask, jsonify, request
import sklearn
from sklearn.neural_network import MLPClassifier
from minio import Minio
from minio.error import S3Error
import numpy as np
import gzip
import json
import pandas as pd
import requests
import logging 
from kafka.admin import KafkaAdminClient, NewTopic
from kafka import KafkaProducer, KafkaConsumer
import pickle

app = Flask(__name__)


# --------------- MinIO And dataset setup

minio_access_key="minioadmin1"
minio_secret_key="minioadmin1"
dataset_bucket_name = "dataset-bucket"
global_model_bucket_name = "global-model-bucket"
global_model_file_name = 'global-model.pkl'

def download_mnist_files(url_base, file_names, save_dir):
    for file_name in file_names:
        url = url_base + file_name
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            file_path = os.path.join(save_dir, file_name)
            with open(file_path, 'wb') as f:
                f.write(response.raw.read())
            app.logger.info(f"Downloaded {file_name}")
        else:
            app.logger.info(f"Failed to download {file_name}")

def extract_images_and_labels(image_file, label_file):
    with gzip.open(image_file, 'rb') as f:
        images = np.frombuffer(f.read(), np.uint8, offset=16).reshape(-1, 28, 28)
    
    with gzip.open(label_file, 'rb') as f:
        labels = np.frombuffer(f.read(), np.uint8, offset=8)

    return images, labels

def split_and_save_dataset_locally(images, labels, test_images, test_labels, parts, directory):
    # Splitting data into equal parts
    indices = np.arange(len(images))
    np.random.shuffle(indices)

    size = len(images) // parts
    for i in range(parts):
        app.logger.info(f"Saving: part {i} of {parts}")
        part_indices = indices[i*size:(i+1)*size] if i < parts - 1 else indices[i*size:]

        # Save train images and labels
        save_gzipped_file(images[part_indices], os.path.join(directory, f'part{i+1}_mnist_train_images.gz'))
        save_gzipped_file(labels[part_indices], os.path.join(directory, f'part{i+1}_mnist_train_labels.gz'))

        # Save test images and labels (same test set for each part)
        save_gzipped_file(test_images, os.path.join(directory, f'part{i+1}_mnist_test_images.gz'))
        save_gzipped_file(test_labels, os.path.join(directory, f'part{i+1}_mnist_test_labels.gz'))

def save_gzipped_file(data, file_path):
    # Ensure the directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with gzip.open(file_path, 'wb') as f:
        f.write(data)

@app.route('/download-dataset')
def download_dataset():
    url_base = 'http://yann.lecun.com/exdb/mnist/'
    file_names = ['train-images-idx3-ubyte.gz', 'train-labels-idx1-ubyte.gz',
                't10k-images-idx3-ubyte.gz', 't10k-labels-idx1-ubyte.gz']

    # Directory where to save the downloaded files
    save_dir = 'MNIST_data'
    os.makedirs(save_dir, exist_ok=True)

    # Download MNIST dataset files
    download_mnist_files(url_base, file_names, save_dir)

    # Load and extract data
    train_images, train_labels = extract_images_and_labels(os.path.join(save_dir, 'train-images-idx3-ubyte.gz'),
                                                        os.path.join(save_dir, 'train-labels-idx1-ubyte.gz'))
    test_images, test_labels = extract_images_and_labels(os.path.join(save_dir, 't10k-images-idx3-ubyte.gz'),
                                                        os.path.join(save_dir, 't10k-labels-idx1-ubyte.gz'))

    app.logger.info(f"Training set (images, labels): {train_images.shape}, {train_labels.shape}")
    app.logger.info(f"Test set (images, labels): {test_images.shape}, {test_labels.shape}")

    split_and_save_dataset_locally(train_images, train_labels, test_images, test_labels, 50, 'split_mnist_data')
    return "Downloaded and split", 200

@app.route("/upload-splits")
def upload_splits_to_minio():
    # Upload to MinIO
    bucket_name = 'dataset-bucket'  # replace with your bucket name
    client = Minio(
        "minio-operator9000.minio-dev.svc.cluster.local:9000",
        access_key=minio_access_key,
        secret_key=minio_secret_key,
        secure=False
    )
    res_str = create_bucket(client, bucket_name, "")

    app.logger.info(f"Uploading to the minio bucket")
    for i in range(1, 51):
        app.logger.info(f"Uploaded {i-1} out of 50")
        for file_type in ['train_images', 'train_labels', 'test_images', 'test_labels']:
            file_name = f'part{i}_mnist_{file_type}.gz'
            file_path = f'split_mnist_data/{file_name}'
            client.fput_object(bucket_name, file_name, file_path)
    return res_str + "\nUploaded splits to the new minio bucket", 200


def create_bucket(client, new_bucket_name, res_string):
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
        app.logger.info(err)
        
    return res_string


@app.route('/setup-minio')
def minio_setup():

    client = Minio(
        "minio-operator9000.minio-dev.svc.cluster.local:9000",
        access_key="minioadmin1",
        secret_key="minioadmin1",
        secure=False
    )
    app.logger.info("connected to the client")

    res_string = create_bucket(client, dataset_bucket_name, "")
    res_string += create_bucket(client, global_model_bucket_name, "")

    

    # Attempt to upload from an anonymous client
    anon_client = Minio("minio-operator9000.minio-dev.svc.cluster.local:9000",
                        secure=False)
    
    app.logger.info("connected with anon client")
    try:
        result = anon_client.put_object(
            dataset_bucket_name, "my-object", io.BytesIO(b"hello"), 5, 
        )
        res_string += "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        )
    except S3Error as err:
        app.logger.info(err)

    
    return res_string, 200

@app.route('/build-everything')
def build_everything():
    minio_setup()
    download_dataset()
    upload_splits_to_minio()
    setup_kafka()

# ------------------ Kafka

kafka_url = "kafkica.openwhisk.svc.cluster.local"

admin_client = KafkaAdminClient(
    bootstrap_servers=kafka_url, 
    client_id='myAdminClient' # can be set to any value
)



@app.route('/setup-kafka')
def setup_kafka():
    if ('federated' not in admin_client.list_topics()):
        topic_list = [NewTopic(name="federated", num_partitions=1, replication_factor=1)]
        admin_client.create_topics(new_topics=topic_list, validate_only=False)
        return "Kafka topic added", 200
    return "Kafka topic already exists", 200

@app.route('/service')
def service():
    app.logger.info("Welcome to notification service")
    return 'Notification Service',200


def merge_models(model1, model2_coefs, model2_intercepts, mini_x, mini_y):
    averaged_coefs = [0.5 * (w1 + w2) for w1, w2 in zip(model1.coefs_, model2_coefs)]
    averaged_intercepts = [0.5 * (b1 + b2) for b1, b2 in zip(model1.intercepts_, model2_intercepts)]

    # Create a new model with the averaged weights
    merged_model = MLPClassifier(hidden_layer_sizes=model1.hidden_layer_sizes, activation=model1.activation,
                                solver=model1.solver, alpha=model1.alpha, batch_size=model1.batch_size,
                                learning_rate=model1.learning_rate, max_iter=model1.max_iter,
                                random_state=model1.random_state, warm_start=True)
    merged_model.fit(mini_x, mini_y) # just to initialize the variables
    merged_model.coefs_ = averaged_coefs
    merged_model.intercepts_ = averaged_intercepts
    return merged_model

# Saves the new global model to minio
def save_new_global_model(client, global_model_new):
    serialized_data = pickle.dumps(global_model_new)

    client.put_object(
        global_model_bucket_name,
        global_model_file_name,
        data=io.BytesIO(serialized_data),
        length=len(serialized_data),
        content_type="application/octet-stream"
    )


@app.route('/learn')
def learn():
    consumer = KafkaConsumer(
        'federated',
        bootstrap_servers=kafka_url,
        auto_offset_reset='earliest', # Start reading from the earliest messages
        group_id='federated_grp',
        value_deserializer=lambda m: pickle.loads(m)
    )
    # Warm start needed for incremental learning
    global_model = MLPClassifier(hidden_layer_sizes=(50,), max_iter=50, solver='sgd', random_state=1, verbose=True, warm_start=True)

    # Save global model to MinIO
    client = Minio("minio-operator9000.minio-dev.svc.cluster.local:9000",
                        secure=False)
    
    app.logger.info("Saving first global model")

    save_new_global_model(client, global_model)

    app.logger.info("Starting training")

    # Start training 
    os.system("wsk -i action invoke learner --param split_nr 3")

    result_dict = None
    app.logger.info("Awaiting kafka answers")
    # Await kafka answers
    for message in consumer:
        app.logger.info("Got kafka answer")
        result_dict = message.value
        break 

    new_model_coefs = result_dict['coefs']
    new_model_intercepts = result_dict['intercepts']

    # Aggregate when done ~ TODO
    # Currently only the avg is take from the previous global model and new model
    app.logger.info("Aggregating")
    global_model = merge_models(global_model, new_model_coefs, new_model_intercepts)

    app.logger.info("Saving new model")
    # Save new global Model
    save_new_global_model(client, global_model)
    
    # loop



    return "Learned", 200

if __name__ == '__main__':
	app.run(debug=True)