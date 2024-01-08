#!/usr/bin/env python

from minio import Minio
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import classification_report, accuracy_score
import numpy as np
import gzip
import os
import pickle
from kafka import KafkaProducer

kafka_url = "kafkica.openwhisk.svc.cluster.local"
dataset_bucket_name = "dataset-bucket"
global_model_bucket_name = "global-model-bucket"
global_model_file_name = 'global-model.pkl'

mini_x = None
mini_y = None

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
    train_images = download_and_extract(minio_client, bucket_name, f'part{part_num}_mnist_train_images.gz', os.path.join(local_dir, 'train_images.gz'))
    train_labels = download_and_extract(minio_client, bucket_name, f'part{part_num}_mnist_train_labels.gz', os.path.join(local_dir, 'train_labels.gz'))
    test_images = download_and_extract(minio_client, bucket_name, f'part{part_num}_mnist_test_images.gz', os.path.join(local_dir, 'test_images.gz'))
    test_labels = download_and_extract(minio_client, bucket_name, f'part{part_num}_mnist_test_labels.gz', os.path.join(local_dir, 'test_labels.gz'))

    # Train neural network
    clf = global_model
    clf.fit(train_images, train_labels)
    predictions = clf.predict(test_images)
    return accuracy_score(test_labels, predictions), clf


def main(args):
    # print(args)
    part_number = args.get("split_nr",1)
    producer = KafkaProducer(
        bootstrap_servers=kafka_url,
        value_serializer=lambda v: pickle.dumps(v)
    )

    producer.send('federated', f'Openwhisk Action with split number {part_number} started'.encode())
    producer.flush()

    client = Minio(
        "minio-operator9000.minio-dev.svc.cluster.local:9000",
        secure=False
    )

    # Fetch the object
    try:
        response = client.get_object(global_model_bucket_name, global_model_file_name)
        serialized_data = response.read()
    finally:
        response.close()
        response.release_conn()

    # Deserialize the data
    global_model = pickle.loads(serialized_data)

    accuracy, model = train_mnist_model(client, dataset_bucket_name, part_number, global_model)
    
    res_dict = {
        "coefs" : model.coefs_,
        "intercepts": model.intercepts_
    }

    producer.send('federated', res_dict)
    producer.flush()

    return { "res": f"Done training on part {part_number}, local test accuracy: {accuracy}" }


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))