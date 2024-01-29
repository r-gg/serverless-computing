import pickle
import random
import time
from io import BytesIO

import numpy as np
import requests
from flask import Flask, request
from sklearn.metrics import accuracy_score
from sklearn.neural_network import MLPClassifier

import mnist_setup


def get_free_port() -> int:
    response = requests.get('http://127.0.0.1:8080/get_free_port')
    if response.status_code != 200:
        raise Exception(f"Error getting free port: {response.text}")
    return int(response.text)


def load_data(directory, dataset_name):
    X_train = mnist_setup.extract_images_and_labels_as_1d_vector(f"{directory}/{dataset_name}_train_images.gz")
    y_train = mnist_setup.extract_images_and_labels_as_1d_vector(f"{directory}/{dataset_name}_train_labels.gz")
    return X_train, y_train


class FederatedLearningClient:
    def __init__(self):
        self.app = Flask(__name__)
        self.client_id = random.randint(0, 100000)
        self.early_stopping = False
        self.port = get_free_port()
        self.dataset_name = self.register_client()

        @self.app.route('/healthcheck', methods=['GET'])
        def healthcheck():
            return 'OK', 200

        @self.app.route('/start_training', methods=['POST'])
        def start_training():
            self.early_stopping = False
            args = request.args.to_dict()
            dataset = args['dataset']
            round_nr = args['round']
            self.app.logger.info(
                f"{self.client_id}: Training started for round_nr: {round_nr} with dataset: {dataset}")

            directory = f'split_{self.dataset_name}_data'
            X_train, y_train = load_data(directory, dataset)

            serialized_model = request.files['model'].read()
            model, delta_time, accuracy = self.train_model(serialized_model, X_train, y_train, round_nr)

            serialized_model_stream = BytesIO(pickle.dumps(model))
            requests.post(f'http://127.0.0.1:8080/post_updated_model?round={round_nr}&client_id={self.client_id}',
                          files={'model': serialized_model_stream}, data={'accuracy': accuracy, 'time': delta_time})
            return f'Training round {round_nr} finished for client {self.client_id}'

        @self.app.route('/stop_training', methods=['POST'])
        def early_stopping():
            self.early_stopping = True
            return 'Training stopped', 200

    def register_client(self):
        response = requests.post('http://127.0.0.1:8080/register_client',
                                 data={'client_id': self.client_id, 'port': self.port})
        print("Client registered, dataset_name: ", response.text)
        return response.text

    def train_model(self, serialized_model, X_train, y_train, round_nr):
        model: MLPClassifier = pickle.loads(serialized_model)
        self.app.logger.info(f"Model loaded for round {round_nr}: {model}")

        start_time = time.time()
        # for i in range(model.max_iter):
        for i in range(50):
            if self.early_stopping:
                break
            model.partial_fit(X_train, y_train, classes=np.arange(10))

        end_time = time.time()
        delta = round(end_time - start_time, 2)
        self.app.logger.info(f"Training finished for round {round_nr} in {delta} seconds")

        accuracy = accuracy_score(y_train, model.predict(X_train))
        print(f"Accuracy for client {self.client_id} on train data: {accuracy}")
        return model, delta, accuracy

    def run(self):
        print(f"Starting client on port {self.port}")
        self.app.run(port=self.port, debug=True, use_reloader=False)


if __name__ == '__main__':
    client = FederatedLearningClient()
    client.run()
