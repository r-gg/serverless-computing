import numpy as np
from sklearn.metrics import accuracy_score
from sklearn.neural_network import MLPClassifier

import mnist_setup

N_CLASSES = 10  # MNIST has 10 classes (0 - 9)
N_FEATURES = 784  # Number of features in dataset


def initialize_mlp_model(model: MLPClassifier, X_dummy, y_dummy):
    """Initialize MLPClassifier model with dummy data."""
    model.fit(X_dummy, y_dummy)
    model.n_outputs_ = N_CLASSES
    model.classes_ = np.array([i for i in range(N_CLASSES)])

    return model


def evaluate_model(X, y, model: MLPClassifier):
    """Evaluate model on given data."""
    return accuracy_score(y, model.predict(X))


def load_data(dataset_name='mnist'):
    train_set, test_set = mnist_setup.download_dataset(dataset=dataset_name)
    X_train, y_train = train_set["images"], train_set["labels"]
    X_test, y_test = test_set["images"], test_set["labels"]
    return X_train, y_train, X_test, y_test


def create_classifier(hidden_layer_sizes=(50,), max_iter=20, solver='sgd', random_state=1, warm_start=True):
    return MLPClassifier(
        hidden_layer_sizes=hidden_layer_sizes,
        max_iter=max_iter,
        solver=solver,
        random_state=random_state,
        warm_start=warm_start,
    )


def calculate_stats(client_stats):
    avg_accuracy_per_round = []
    avg_time_per_round = []

    # sort by round number
    client_stats.sort(key=lambda x: x['round'])

    print("Client stats: ", client_stats)

    # get max round number
    max_round = 0
    for stats in client_stats:
        if stats['round'] > max_round:
            max_round = stats['round']

    # initialize lists
    for i in range(max_round):
        avg_accuracy_per_round.append({
            'round': i,
            'avg_accuracy': 0,
            'accuracy_per_client': []
        })
        avg_time_per_round.append({
            'round': i,
            'avg_time': 0,
            'time_per_client': []
        })

    print("Max round: ", max_round)
    print("len(avg_accuracy_per_round): ", len(avg_accuracy_per_round))
    print("len(avg_time_per_round): ", len(avg_time_per_round))

    # fill lists
    for stats in client_stats:
        round_nr = stats['round']
        avg_accuracy_per_round[round_nr - 1]['accuracy_per_client'].append(stats['accuracy'])
        avg_time_per_round[round_nr - 1]['time_per_client'].append(stats['time'])

    # calculate averages
    for i in range(max_round):
        avg_accuracy_per_round[i]['avg_accuracy'] = np.average(avg_accuracy_per_round[i]['accuracy_per_client'])
        avg_time_per_round[i]['avg_time'] = np.average(avg_time_per_round[i]['time_per_client'])

    # sort lists by round number
    avg_accuracy_per_round.sort(key=lambda x: x['round'])
    avg_time_per_round.sort(key=lambda x: x['round'])
    return avg_accuracy_per_round, avg_time_per_round
