import io
import os
from flask import Flask, request
from sklearn.metrics import accuracy_score
from sklearn.neural_network import MLPClassifier
from minio import Minio
from minio.error import S3Error
import numpy as np
import gzip
import json
import requests
from kafka.admin import KafkaAdminClient, NewTopic
from kafka import KafkaConsumer
import pickle
import time
import random
import zipfile
from io import BytesIO

app = Flask(__name__)

minio_access_key="minioadmin1"
minio_secret_key="minioadmin1"
dataset_bucket_name = "dataset-bucket"

results_bucket_name = "results-bucket"

global_model_bucket_name = "global-model-bucket"
global_model_file_name = 'global-model.pkl'
kafka_url = "kafkica.openwhisk.svc.cluster.local"


admin_client = KafkaAdminClient(
    bootstrap_servers=kafka_url, 
    client_id='myAdminClient' # can be set to any value
)

n_splits = 100


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

def download_emnist_files(url, file_names, save_dir):
    """
    url - URL of the zip file containing the EMNIST dataset
    (https://rds.westernsydney.edu.au/Institutes/MARCS/BENS/EMNIST/emnist-gzip.zip)
    """
    response = requests.get(url, stream=True, verify=False)
    if response.status_code == 200:
        with zipfile.ZipFile(BytesIO(response.content)) as thezip:
            for file_name in file_names:
                thezip.extract(file_name, path=save_dir)
                # Move files from 'gzip' subdirectory to the desired directory and remove the 'gzip' subdirectory
                extracted_file_path = os.path.join(save_dir, file_name)
                target_file_path = os.path.join(save_dir, os.path.basename(file_name).replace('emnist-digits-', ''))
                os.rename(extracted_file_path, target_file_path)
            print(f"Extracted: {', '.join([os.path.basename(file_name) for file_name in file_names])}")
    else:
        print(f"Failed to download from {url}")

def extract_images_and_labels(image_file, label_file):
    with gzip.open(image_file, 'rb') as f:
        images = np.frombuffer(f.read(), np.uint8, offset=16).reshape(-1, 784)
    
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
        save_gzipped_file(images[part_indices], os.path.join(directory, f'part{i+1}_emnist_train_images.gz'))
        save_gzipped_file(labels[part_indices], os.path.join(directory, f'part{i+1}_emnist_train_labels.gz'))

        # Save test images and labels (same test set for each part)
        # save_gzipped_file(test_images, os.path.join(directory, f'part{i+1}_emnist_test_images.gz'))
        # save_gzipped_file(test_labels, os.path.join(directory, f'part{i+1}_emnist_test_labels.gz'))

def save_gzipped_file(data, file_path):
    # Ensure the directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with gzip.open(file_path, 'wb') as f:
        f.write(data)


@app.route('/download-and-split-dataset')
def download_dataset():
    url = 'https://rds.westernsydney.edu.au/Institutes/MARCS/BENS/EMNIST/emnist-gzip.zip'
    digit_files = [
        'gzip/emnist-digits-train-images-idx3-ubyte.gz',
        'gzip/emnist-digits-train-labels-idx1-ubyte.gz',
        'gzip/emnist-digits-test-images-idx3-ubyte.gz',
        'gzip/emnist-digits-test-labels-idx1-ubyte.gz'
    ]

    # Directory where to save the downloaded files
    save_dir = 'EMNIST_data'
    os.makedirs(save_dir, exist_ok=True)

    # Download MNIST dataset files only if all four files are missing
    download_emnist_files(url, digit_files, save_dir)

    # Perform splitting only if all 200 split files are missing    
    split_dir = 'split_emnist_data'

    if not os.path.exists(split_dir) or len(os.listdir(split_dir)) != 200:
        # Load and extract data
        train_images, train_labels = extract_images_and_labels(os.path.join(save_dir, 'train-images-idx3-ubyte.gz'),
                                                            os.path.join(save_dir, 'train-labels-idx1-ubyte.gz'))
        test_images, test_labels = extract_images_and_labels(os.path.join(save_dir, 'test-images-idx3-ubyte.gz'),
                                                            os.path.join(save_dir, 'test-labels-idx1-ubyte.gz'))

        app.logger.info(f"Training set (images, labels): {train_images.shape}, {train_labels.shape}")
        app.logger.info(f"Test set (images, labels): {test_images.shape}, {test_labels.shape}")


        split_and_save_dataset_locally(train_images, train_labels, test_images, test_labels, n_splits, split_dir)
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
    for i in range(1, (n_splits + 1)):
        app.logger.info(f"Uploaded {i-1} out of {n_splits}")
        for file_type in ['train_images', 'train_labels']:
            file_name = f'part{i}_emnist_{file_type}.gz'
            file_path = f'split_emnist_data/{file_name}'
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
    res_string += create_bucket(client, results_bucket_name, "")
    
    return res_string, 200

@app.route('/build-everything')
def build_everything():
    minio_setup()
    download_dataset()
    upload_splits_to_minio()
    setup_kafka()
    return "Minio is set, dataset splits uploaded to minio and kafka topic added", 200




@app.route('/setup-kafka')
def setup_kafka():
    if ('federated' not in admin_client.list_topics()):
        topic_list = [NewTopic(name="federated", num_partitions=1, replication_factor=1)]
        admin_client.create_topics(new_topics=topic_list, validate_only=False)
        return "Kafka topic added", 200
    return "Kafka topic already exists", 200

def merge_models(models, sample_x, sample_y):
    # Ensure there is at least one model to merge
    if not models:
        raise ValueError("No models provided for merging")

    # Calculate the average of coefficients and intercepts
    averaged_coefs = [sum(w) / len(models) for w in zip(*[model.coefs_ for model in models])]
    averaged_intercepts = [sum(b) / len(models) for b in zip(*[model.intercepts_ for model in models])]

    # Create a new model with the averaged weights, using parameters from the first model
    first_model = models[0]
    merged_model = first_model 
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
    args = request.args.to_dict()
    app.logger.info(f"Received args: {args}")

    test_images = None
    test_labels = None
    save_dir = 'EMNIST_data'
    if not os.path.exists(save_dir):
        return "Dataset not downloaded", 500
    else:
        app.logger.info("Dataset already downloaded")
        test_images, test_labels = extract_images_and_labels(os.path.join(save_dir, 'test-images-idx3-ubyte.gz'),
                                                            os.path.join(save_dir, 'test-labels-idx1-ubyte.gz'))
        test_images = test_images / 255.0

    nclients = 3
    nrounds = 5
    nselected = 3

    if 'nclients' in args:
        nclients = int(args['nclients'])
    if 'nrounds' in args:
        nrounds = int(args['nrounds'])
    if 'nselected' in args:
        nselected = int(args['nselected'])

    id = random.randint(0, 1000000)
    consumer = KafkaConsumer(
        'federated',
        bootstrap_servers=kafka_url,
        # auto_offset_reset='earliest', # Start reading from the earliest messages
        group_id=f'federated_grp_{id}',
        value_deserializer=lambda m: pickle.loads(m)
    )
    # Warm start needed for incremental learning
    global_model = MLPClassifier(hidden_layer_sizes=(50,), 
                                 max_iter=20, 
                                 solver='sgd', 
                                 random_state=1, 
                                 verbose=True, 
                                 warm_start=True,
                                 learning_rate_init=0.01)

    # Save global model to MinIO
    client = Minio("minio-operator9000.minio-dev.svc.cluster.local:9000",
                        secure=False)
    
    app.logger.info("Saving first global model")

    save_new_global_model(client, global_model)

    app.logger.info("Starting training")
    time.sleep(3)
    timeout = 30  # seconds

    accuracies = []
    part_counter = 1 # points to the next data chunk to be trained on
    training_start = time.time()
    timed_out = False
    train_accuracies = [] # list of lists. each list contains the train accuracies of the clients of one round
    train_round_durations = []
    activation_durations = []
    for round in range(nrounds):
        # Start training  
        

        if nclients < nselected:
            nselected = nclients
        start_time = time.time()
        round_start_time = time.time()
        for i in range(nclients):
            status = os.system(f"wsk -i action invoke learner --param split_nr {(part_counter % n_splits) + 1} --param round_nr {round}")
            if status != 0:
                return "Error invoking learner", 500
            part_counter+=1

        app.logger.info("Awaiting kafka answers")
        

        new_models = []
        current_train_accuracies = []
        current_activation_durations = []

        while len(new_models) < nselected:
            message = consumer.poll()  # Timeout_ms blocks entirely for some reason
            if message:
                for _, messages in message.items():
                    for msg in messages:
                        res = msg.value
                        round_number = res['round_number']
                        if round_number < round:
                            app.logger.info(f"Received message from previous round {round_number}, ignoring because we are in round {round}")
                            continue
                        new_model = res['model']
                        new_models.append(new_model)
                        current_train_accuracies.append(res['train_accuracy'])
                        current_activation_durations.append(res['activation_duration'])
                        app.logger.info(f"Received {len(new_models)} out of {nselected})")
                        start_time = time.time() # Resetting the timer
                if len(new_models) >= nselected:
                    break   # Exit after the first message is processed
            app.logger.info("No message received, checking timeout, time difference is " + str(time.time() - start_time) + " seconds")

            if time.time() - start_time > timeout:
                app.logger.info("Timeout reached, no message received.")
                timed_out = True
                break

            app.logger.info("No message received, sleeping")
            time.sleep(1)

        if timed_out:
            break

        if len(new_models) == 0:
            app.logger.info("No new models received, exiting")
            break
        app.logger.info("Aggregating")        
        global_model = merge_models(new_models, test_images[0].reshape(1, -1), test_labels[0].reshape(-1, 1))
        preds = global_model.predict(test_images)
        acc = accuracy_score(test_labels, preds)
        accuracies.append(acc)
        app.logger.info(f"Round {round}: accuracy {acc}")
        train_accuracies.append(current_train_accuracies)
        activation_durations.append(current_activation_durations)
        app.logger.info("Saving new model")
        train_round_durations.append(time.time() - round_start_time)
        # Save new global Model
        save_new_global_model(client, global_model)

    consumer.close()
    if timed_out:
        return "Timeout reached", 500
    training_end = time.time()
    training_time = training_end - training_start
    memory = 512
    result = {
        "rounds": nrounds,
        "clients": nclients,
        "selected": nselected,
        "accuracies": accuracies,
        "train_accuracies": train_accuracies,
        "training_time": training_time,
        "timed_out": timed_out,
        "train_round_durations": train_round_durations,
        "activation_durations": activation_durations,
        "memory" : memory
    }
    # Save result to MinIO
    serialized_data = pickle.dumps(result)

    app.logger.info("Saving result to MinIO bucket")
    client.put_object(
        results_bucket_name,
        f'result_rounds_{nrounds}_clients_{nclients}_selected_{nselected}_memory_{memory}.pkl',
        data=io.BytesIO(serialized_data),
        length=len(serialized_data),
        content_type="application/octet-stream"
    )

    
    res = f"""
    Rounds: {nrounds} \n
    Clients: {nclients} \n
    Selected: {nselected}  \n
    Resulting Accuracies {accuracies} \n
    Training time {training_time}"""
    return res, 200

if __name__ == '__main__':
	app.run(debug=True, port=5000)