import io
import os
from flask import Flask, jsonify, request
from sklearn.metrics import accuracy_score
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
import time

app = Flask(__name__)


# --------------- MinIO And dataset setup

minio_access_key="minioadmin1"
minio_secret_key="minioadmin1"
dataset_bucket_name = "dataset-bucket"
global_model_bucket_name = "global-model-bucket"
global_model_file_name = 'global-model.pkl'
minis = {
    "mini_x" : None,
    "mini_y" : None
}

test_set = {
    "images" : None,
    "labels" : None
}

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

def set_minis():
    url_base = 'http://yann.lecun.com/exdb/mnist/'
    test_file_names = ['t10k-images-idx3-ubyte.gz', 't10k-labels-idx1-ubyte.gz']

    # Directory where to save the downloaded files
    save_dir = 'MNIST_data'
    os.makedirs(save_dir, exist_ok=True)

    # Check if test files exist, if not download them
    
    file_path = os.path.join(save_dir, test_file_names[0])
    if not os.path.exists(file_path):
        download_mnist_files(url_base, test_file_names, save_dir)

    # Load and extract data from test files
    test_images, test_labels = extract_images_and_labels(os.path.join(save_dir, 't10k-images-idx3-ubyte.gz'),
                                                         os.path.join(save_dir, 't10k-labels-idx1-ubyte.gz'))

    # Set mini variables
    minis['mini_x'] = test_images[0:2].reshape(-1, 784)
    minis['mini_y'] = test_labels[0:2].reshape(-1,)
    test_set['images'] = test_images.reshape(-1, 784)
    test_set['labels'] = test_labels.reshape(-1,)

    app.logger.info("Mini variables set")


@app.route('/download-and-split-dataset')
def download_dataset():
    url_base = 'http://yann.lecun.com/exdb/mnist/'
    file_names = ['train-images-idx3-ubyte.gz', 'train-labels-idx1-ubyte.gz',
                't10k-images-idx3-ubyte.gz', 't10k-labels-idx1-ubyte.gz']

    # Directory where to save the downloaded files
    save_dir = 'MNIST_data'
    os.makedirs(save_dir, exist_ok=True)

    # Download MNIST dataset files only if all four files are missing
    missing_files = [not os.path.exists(os.path.join(save_dir, file_name)) for file_name in file_names]
    if any(missing_files):
        download_mnist_files(url_base, file_names, save_dir)
    else:
        app.logger.info("MNIST dataset files already exist")

    # Perform splitting only if all 200 split files are missing    
    split_dir = 'split_mnist_data'

    if not os.path.exists(split_dir) or len(os.listdir(split_dir)) != 200:
        # Load and extract data
        train_images, train_labels = extract_images_and_labels(os.path.join(save_dir, 'train-images-idx3-ubyte.gz'),
                                                            os.path.join(save_dir, 'train-labels-idx1-ubyte.gz'))
        test_images, test_labels = extract_images_and_labels(os.path.join(save_dir, 't10k-images-idx3-ubyte.gz'),
                                                            os.path.join(save_dir, 't10k-labels-idx1-ubyte.gz'))

        minis['mini_x'] = test_images[0:2].reshape(-1, 784)
        minis['mini_y'] = test_labels[0:2].reshape(-1,)
        app.logger.info(f"Training set (images, labels): {train_images.shape}, {train_labels.shape}")
        app.logger.info(f"Test set (images, labels): {test_images.shape}, {test_labels.shape}")

        test_set['images'] = test_images.reshape(-1, 784)
        test_set['labels'] = test_labels.reshape(-1,)

        split_and_save_dataset_locally(train_images, train_labels, test_images, test_labels, 50, 'split_mnist_data')
    else:
        app.logger.info("Split files already exist, loading minis")
        set_minis()
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
    return "Minio is set, dataset splits uploaded to minio and kafka topic added", 200

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


def merge_models(models):
    # Ensure there is at least one model to merge
    if not models:
        raise ValueError("No models provided for merging")

    # Calculate the average of coefficients and intercepts
    averaged_coefs = [sum(w) / len(models) for w in zip(*[model.coefs_ for model in models])]
    averaged_intercepts = [sum(b) / len(models) for b in zip(*[model.intercepts_ for model in models])]

    # Create a new model with the averaged weights, using parameters from the first model
    first_model = models[0]
    merged_model = MLPClassifier(hidden_layer_sizes=first_model.hidden_layer_sizes, activation=first_model.activation,
                                 solver=first_model.solver, alpha=first_model.alpha, batch_size=first_model.batch_size,
                                 learning_rate=first_model.learning_rate, max_iter=first_model.max_iter,
                                 random_state=first_model.random_state, warm_start=False)
    
    # Initialize the model (replace 'X_sample' and 'y_sample' with actual data)
    merged_model.partial_fit(minis['mini_x'], minis['mini_y'], classes=np.arange(10)) # just to initialize the variables    
    # Set the averaged weights and biases
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

# Usage: /learn?nclients=10&nrounds=10&nselected=5
@app.route('/learn')
def learn():
    set_minis() # Needed for initializing the models upon each merge

    args = request.args.to_dict()
    app.logger.info(f"Received args: {args}")

    nclients = 3
    nrounds = 5
    nselected = 3

    if 'nclients' in args:
        nclients = int(args['nclients'])
    if 'nrounds' in args:
        nrounds = int(args['nrounds'])
    if 'nselected' in args:
        nselected = int(args['nselected'])


    consumer = KafkaConsumer(
        'federated',
        bootstrap_servers=kafka_url,
        # auto_offset_reset='earliest', # Start reading from the earliest messages
        group_id='federated_grp_8',
        value_deserializer=lambda m: pickle.loads(m)
    )
    # Warm start needed for incremental learning
    global_model = MLPClassifier(hidden_layer_sizes=(50,), max_iter=50, solver='sgd', random_state=1, verbose=True, warm_start=False)
    # Just initializing the coefs
    global_model.partial_fit(minis['mini_x'], minis['mini_y'], classes=np.arange(10)) # just to initialize the variables

    # Save global model to MinIO
    client = Minio("minio-operator9000.minio-dev.svc.cluster.local:9000",
                        secure=False)
    
    app.logger.info("Saving first global model")

    save_new_global_model(client, global_model)

    app.logger.info("Starting training")
    time.sleep(3)
    
    accuracies = []
    part_counter = 1 # points to the next data chunk to be trained on
    for round in range(1,nrounds):
        # Start training  

        if nclients < nselected:
            nselected = nclients
        
        

        for i in range(nclients):
            status = os.system(f"wsk -i action invoke learner --param split_nr {part_counter % 50}")
            if status != 0:
                return "Error invoking learner", 500
            part_counter+=1

        app.logger.info("Awaiting kafka answers")
        timeout = 10  # Set your timeout in seconds
        start_time = time.time()

        new_models = []
        while len(new_models) < nselected:
            app.logger.info("Starting polling")
            message = consumer.poll()  # Timeout_ms blocks entirely for some reason
            app.logger.info(f"Polling done, message : {message}")
            if message:
                for _, messages in message.items():
                    for msg in messages:
                        new_model = msg.value
                        new_models.append(new_model)
                        app.logger.info(f"Received {len(new_models)} out of {nselected})")
                if len(new_models) >= nselected:
                    break   # Exit after the first message is processed
                break
            app.logger.info("No message received, checking timeout, time difference is " + str(time.time() - start_time) + " seconds")

            if time.time() - start_time > timeout:
                app.logger.info("Timeout reached, no message received.")
                break

            app.logger.info("No message received, sleeping")
            time.sleep(1)

        
        # Aggregate when done ~ TODO
        # Currently only the new model is taken as a new global model
        app.logger.info("Aggregating")
        
        #global_model = merge_models(global_model, new_model.coefs_, new_model.intercepts_)
        
        # global_model = new_model
        if len(new_models) == 0:
            app.logger.info("No new models received, exiting")
            break
        global_model = merge_models(new_models)
        preds = global_model.predict(test_set['images'])
        acc = accuracy_score(test_set['labels'], preds)
        accuracies.append(acc)
        app.logger.info("Saving new model")
        # Save new global Model
        save_new_global_model(client, global_model)




    consumer.close()
    return f"Learned: Accuracies {accuracies}", 200

if __name__ == '__main__':
	app.run(debug=True, port=5001)