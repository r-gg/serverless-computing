import os
import pickle
import random
import threading
import time
from io import BytesIO

import requests
from flask import Flask, request
from flask_cors import cross_origin
from flask_socketio import SocketIO
from sklearn.neural_network import MLPClassifier

import mnist_setup
import utils


class FederatedLearningServer:
    def __init__(self, dataset_name='mnist', max_iter=20, nr_parts=50):
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, debug=True, cors_allowed_origins="*")
        self.clients = []
        self.client_stats = []
        self.server_stats = []
        self.subscribers = {}
        self.splits = {}
        self.global_model = None
        self.DIRECTORY = f'split_{dataset_name}_data'
        self.dataset_name = dataset_name
        self.nr_parts = nr_parts
        self.training_rounds = 20
        self.max_iter = max_iter
        self.FREE_PORTS = list(range(8081, 8099))
        self.round_nr = 0
        self.start_time = time.time()
        self.current_models = []
        self.n_selected = 1
        self.in_merging = False
        self.X_train, self.y_train, self.X_test, self.y_test = utils.load_data(self.dataset_name)
        self.history = []
        self.prepare_splits()
        self.prepare_global_model()
        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/number_client')
        def get_number_of_clients():
            return str(len(self.clients))

        @self.app.route('/register_client', methods=['POST'])
        def register_client():
            """Register a client on the server. Return the dataset_name so that the client knows the directory"""
            client_id = request.form.get('client_id')
            port = request.form.get('port')
            self.app.logger.info(f"Client {client_id} registered on port {port}")
            client = {
                'client_id': client_id,
                'port': port
            }
            self.broadcast_message('client_registered', client)
            self.clients.append(client)
            return self.dataset_name, 200

        @self.app.route('/check_clients', methods=['GET'])
        def check_clients_route():
            return self.check_clients()

        @self.app.route('/get_clients', methods=['GET'])
        @cross_origin()
        def get_clients():
            return self.clients

        @self.app.route('/start_training', methods=['GET'])
        def start_training_route():
            args = request.args.to_dict()
            return self.start_training(int(args['n_rounds']), int(args['n_selected']))

        @self.app.route('/post_updated_model', methods=['POST'])
        def post_updated_model():
            args = request.args.to_dict()
            if 'round' in args:
                round_number = int(args['round'])
                if round_number is not self.round_nr:
                    print(f"Round number {round_number} is not {self.round_nr}")
                    return 'Wrong round number', 400
            client_id = args['client_id']
            accuracy = float(request.form.get('accuracy'))
            delta_time = float(request.form.get('time'))
            client_update = {
                'client_id': client_id,
                'round': self.round_nr,
                'accuracy': round(accuracy, 4),
                'time': delta_time
            }
            #TODO: Only send the client models that have been chosen for merging
            self.broadcast_message('update_client', client_update)
            self.client_stats.append(client_update)
            serialized_model = request.files['model'].read()
            client = [client for client in self.clients if client['client_id'] == client_id][0]
            self.app.logger.info(
                f"Received model from client {client_id} with port {client['port']} for round {self.round_nr}")
            model: MLPClassifier = pickle.loads(serialized_model)
            self.app.logger.info(f"Training model for round {self.round_nr}")
            self.current_models.append(model)
            temp_list = self.current_models.copy()

            if len(self.current_models) >= self.n_selected and not self.in_merging:
                self.in_merging = True

                n_models = len(self.current_models)
                for client in self.clients:
                    threading.Thread(target=self.stop_training_round, args=(client,)).start()

                self.merge_models(temp_list)

                if self.global_model is None:
                    self.prepare_global_model()

                accuracy = utils.evaluate_model(self.X_test, self.y_test, self.global_model)
                self.app.logger.info(f"Accuracy for round {self.round_nr} using {n_models} clients: {accuracy}")
                update = {
                    'round': self.round_nr,
                    'accuracy': round(accuracy, 4),
                    'accumulated_time': time.time() - self.start_time
                }
                self.broadcast_message('update_accuracy', update)
                self.server_stats.append(update)
                if self.round_nr < self.training_rounds:
                    self.start_training_round()
                    self.in_merging = False
                    return f'Training round {self.round_nr} started'
                else:
                    threading.Thread(target=self.calculate_metrics).start()
                    return 'Training finished'
            else:
                return f'Not all models received yet'

        @self.app.route('/get_free_port', methods=['GET'])
        def get_free_port():
            if len(self.FREE_PORTS) == 0:
                return 'No free ports', 500
            return str(self.FREE_PORTS.pop(0)), 200

        @self.app.route('/healthcheck', methods=['GET'])
        def healthcheck():
            return 'OK', 200

        @self.socketio.on('connect')
        def connect():
            print(f"Client connected with sid {request.sid}")

        @self.socketio.on('disconnect')
        def disconnect():
            print(f"Client disconnected with sid {request.sid}")

        @self.socketio.on('start_training')
        def start_training_ws(n_rounds: str, n_selected: str):
            self.start_training(int(n_rounds), int(n_selected))

    def start_training(self, n_rounds, n_selected):
        self.start_time = time.time()
        self.round_nr = 0
        self.in_merging = False
        self.prepare_splits()
        self.prepare_global_model()

        self.check_clients()

        self.training_rounds = n_rounds
        self.n_selected = n_selected

        self.app.logger.info(
            f"Training started for {self.training_rounds} rounds with {self.n_selected} selected clients per round")
        self.broadcast_message('training_started', {
            'n_rounds': self.training_rounds,
            'n_selected': self.n_selected
        })
        thread = threading.Thread(target=self.start_training_round)
        thread.start()
        return 'Training started...', 200

    def check_clients(self):
        result = ''
        clients_to_remove = []
        result += str(self.clients) + "\n\n"
        for client in self.clients:
            try:
                response = requests.get(f"http://127.0.0.1:{client['port']}/healthcheck")
                if response.status_code != 200:
                    clients_to_remove.append(client)
                result += f"Client on port {client['port']}\n"
            except Exception:
                clients_to_remove.append(client)

        for client in clients_to_remove:
            self.clients.remove(client)
            result += f"Client on port {client['port']} is not healthy -> removed\n"

        return result

    def broadcast_message(self, event: str, data):
        self.socketio.emit(event, {'data': data})

    def start_training_round(self):
        self.current_models = []
        self.round_nr += 1
        serialized_model = pickle.dumps(self.global_model)
        self.send_training_request_to_clients(serialized_model)

    def send_training_request_to_clients(self, serialized_model):
        for client in self.clients:
            selected_split = None
            # check if there are still splits to send -  send random split to client
            if not any(self.splits.values()):
                # take random split
                selected_split = random.choice(list(self.splits.keys()))
            else:
                # find first split that was not sent to a client
                for split in self.splits:
                    if not self.splits[split]:
                        self.splits[split] = True
                        selected_split = split
                        break

            # send split to client
            threading.Thread(target=self.send_model, args=(client, selected_split, serialized_model)).start()
            self.app.logger.info(f"Sending split {selected_split} to client {client['client_id']}")

    def send_model(self, client, split, serialized_model):
        serialized_model_stream = BytesIO(serialized_model)
        requests.post(
            f"http://127.0.0.1:{client['port']}/start_training?dataset={split}&round={self.round_nr}",
            files={'model': serialized_model_stream}
        )

    def stop_training_round(self, client):
        requests.post(f"http://127.0.0.1:{client['port']}/stop_training")

    def merge_models(self, models):
        # average the weights and biases
        self.app.logger.info(f"Merging {len(models)} models")
        self.global_model.coefs_ = [sum([model.coefs_[i] for model in models]) / len(self.clients) for i in
                                    range(len(models[0].coefs_))]
        self.global_model.intercepts_ = [
            sum([model.intercepts_[i] for model in models]) / len(models) for i
            in
            range(len(models[0].intercepts_))]

    def calculate_metrics(self):
        avg_accuracy, avg_time = utils.calculate_stats(self.client_stats)
        result_dir = 'results'
        # create directory if it does not exist
        if not os.path.exists(result_dir):
            os.makedirs(result_dir)
        # write results to a file
        filename = f"result_{self.dataset_name}_rounds_{self.training_rounds}_clients_{len(self.clients)}_selected_{self.n_selected}.txt"
        print("Path: " + os.path.join(result_dir, filename))
        f = open(os.path.join(result_dir, filename), "w")
        f.write(f"Dataset: {self.dataset_name}\n")
        f.write(f"Number of clients: {len(self.clients)}\n")
        f.write(f"Number of splits: {self.nr_parts}\n")
        f.write(f"Number of training rounds: {self.training_rounds}\n")
        f.write(f"Number of selected clients per round: {self.n_selected}\n")

        f.write("Server values: \n")
        f.write("round, accuracy, accumulated_time\n")
        for stat in self.server_stats:
            f.write(f"{stat['round']}, {stat['accuracy']}, {stat['accumulated_time']}\n")

        f.write("-----------------------------------------------------------------------------\n")
        f.write(f"Average client values: \n")
        f.write(f"round, avg_accuracy, avg_time \n")
        for i in range(len(avg_accuracy)):
            f.write(
                f"{avg_accuracy[i]['round']}, {avg_accuracy[i]['avg_accuracy']}, {avg_time[i]['avg_time']}\n")

        f.close()

    def prepare_splits(self):
        self.splits = mnist_setup.prepare_splits(self.DIRECTORY, self.X_train, self.y_train,
                                                 self.nr_parts, dataset_name=self.dataset_name)

    def prepare_global_model(self):
        self.global_model = utils.create_classifier(max_iter=self.max_iter)
        utils.initialize_mlp_model(self.global_model, self.X_train[:50], self.y_train[:50])

    def run(self, debug=True, port=8080):
        # self.app.run(debug=debug, port=port, use_reloader=False)
        self.socketio.run(app=self.app, debug=debug, port=port, use_reloader=False, log_output=True,
                          allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    server = FederatedLearningServer(dataset_name='emnist', max_iter=20, nr_parts=100)
    server.run(debug=True, port=8080)
