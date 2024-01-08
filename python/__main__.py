#!/usr/bin/env python

from minio import Minio
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import classification_report
import numpy as np
import gzip
import os
from kafka import KafkaProducer

kafka_url = "kafkica.openwhisk.svc.cluster.local"



def download_and_extract(client, bucket_name, object_name, file_path):
    client.fget_object(bucket_name, object_name, file_path)
    with gzip.open(file_path, 'rb') as f_in:
        if 'images' in object_name:
            return np.frombuffer(f_in.read(), np.uint8, offset=16).reshape(-1, 784)  # 28x28 images
        else:
            return np.frombuffer(f_in.read(), np.uint8, offset=8)

def train_mnist_model(minio_client, bucket_name, part_num):
    local_dir = '/tmp/mnist_data_part{}'.format(part_num)
    os.makedirs(local_dir, exist_ok=True)

    # Download and load dataset parts
    train_images = download_and_extract(minio_client, bucket_name, f'part{part_num}_mnist_train_images.gz', os.path.join(local_dir, 'train_images.gz'))
    train_labels = download_and_extract(minio_client, bucket_name, f'part{part_num}_mnist_train_labels.gz', os.path.join(local_dir, 'train_labels.gz'))
    test_images = download_and_extract(minio_client, bucket_name, f'part{part_num}_mnist_test_images.gz', os.path.join(local_dir, 'test_images.gz'))
    test_labels = download_and_extract(minio_client, bucket_name, f'part{part_num}_mnist_test_labels.gz', os.path.join(local_dir, 'test_labels.gz'))

    # Train neural network
    clf = MLPClassifier(hidden_layer_sizes=(50,), max_iter=20, solver='sgd', random_state=1, verbose=True)
    clf.fit(train_images, train_labels)
    predictions = clf.predict(test_images)
    return classification_report(test_labels, predictions)


def main(args):
    # print(args)
    part_number = 1
    producer = KafkaProducer(
        bootstrap_servers=kafka_url
    )

    producer.send('federated', f'Openwhisk Action with split number {part_number} started'.encode())
    producer.flush()

    client = Minio(
        "minio-operator9000.minio-dev.svc.cluster.local:9000",
        secure=False
    )
    dataset_bucket_name = 'dataset-bucket'
    

    classification_report = train_mnist_model(client, dataset_bucket_name, part_number)

    # producer.send('federated', f'Openwhisk Action with split number {part_number} finished')
    # producer.flush()



    return classification_report


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))