#!/usr/bin/env python

import gzip
import os
import pickle
import time

import numpy as np
from sklearn.metrics import accuracy_score

from kafka import KafkaProducer
from minio import Minio

kafka_url = "kafkica.openwhisk.svc.cluster.local"
dataset_bucket_name = "dataset-bucket"
global_model_bucket_name = "global-model-bucket"
global_model_file_name = 'global-model.pkl'


def download_and_extract(client, bucket_name, object_name, file_path):
    client.fget_object(bucket_name, object_name, file_path)
    with gzip.open(file_path, 'rb') as f_in:
        if 'images' in object_name:
            return np.frombuffer(f_in.read(), np.uint8).reshape(-1, 784)  # 28x28 images
        else:
            return np.frombuffer(f_in.read(), np.uint8)


def train_mnist_model(minio_client, bucket_name, part_num, global_model):
    local_dir = '/tmp/mnist_data_part{}'.format(part_num)
    os.makedirs(local_dir, exist_ok=True)

    # Download and load dataset parts
    train_images = download_and_extract(minio_client, bucket_name, f'part{part_num}_emnist_train_images.gz',
                                        os.path.join(local_dir, 'train_images.gz'))
    train_labels = download_and_extract(minio_client, bucket_name, f'part{part_num}_emnist_train_labels.gz',
                                        os.path.join(local_dir, 'train_labels.gz'))

    print(f"Number of training images: {train_images.shape[0]}", flush=True)
    # Train neural network
    clf = global_model
    train_images = train_images / 255.0
    for i in range(50):
        clf.partial_fit(train_images, train_labels, classes=np.arange(10))

    predictions = clf.predict(train_images)
    train_accuracy = accuracy_score(train_labels, predictions)
    return train_accuracy, clf


def main(args):
    start_time = time.time()
    part_number = args.get("split_nr", 1)
    round_number = args.get("round_nr", 1)
    producer = KafkaProducer(
        bootstrap_servers=kafka_url,
        value_serializer=lambda v: pickle.dumps(v)
    )

    client = Minio(
        "minio-operator9000.minio-dev.svc.cluster.local:9000",
        secure=False
    )

    # Fetch the global model
    try:
        response = client.get_object(global_model_bucket_name, global_model_file_name)
        serialized_data = response.read()
    finally:
        response.close()
        response.release_conn()

    global_model = pickle.loads(serialized_data)
    print(f"Warm start value of global model: {global_model.warm_start}", flush=True)

    train_accuracy, model = train_mnist_model(client, dataset_bucket_name, part_number, global_model)

    duration = time.time() - start_time
    message = {
        "model": model,
        "round_number": round_number,
        "train_accuracy": train_accuracy,
        "activation_duration": duration
    }
    producer.send('federated', message)
    producer.flush()

    return {"res": f"Done training on part {part_number}"}


if __name__ == '__main__':
    import sys

    sys.exit(main(sys.argv))
