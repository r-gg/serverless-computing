import numpy as np
from sklearn.metrics import accuracy_score

import mnist_setup
import utils


def train_model_v1(global_clf):
    for i in range(0, number_of_splits, number_of_clients):
        if not (hasattr(global_clf, 'coefs_') and hasattr(global_clf, 'intercepts_')):
            global_clf.fit(X_train_split[i], y_train_split[i])
        else:
            clfs = []
            for j in range(number_of_clients):
                current_split = i + j
                if current_split >= number_of_splits:
                    break
                clf = utils.create_classifier()
                clf = utils.copy_params(global_clf, clf)
                # clf = utils.set_model_params(clf, utils.get_model_parameters(global_clf))
                for k in range(50):
                    clf.partial_fit(X_train_split[current_split], y_train_split[current_split], classes=np.arange(10))
                # calculate accuracy
                accuracy = accuracy_score(y_test, clf.predict(X_test))
                print(f"  Accuracy for client {j} on split {current_split}: {accuracy}")
                clfs.append(clf)

            # average the weights and biases
            #global_clf.coefs_ = [sum([clf.coefs_[i] for clf in clfs]) / number_of_clients for i in range(len(clfs[0].coefs_))]
            #global_clf.intercepts_ = [sum([clf.intercepts_[i] for clf in clfs]) / number_of_clients for i in range(len(clfs[0].intercepts_))]
            # calculate accuracy
            accuracy = accuracy_score(y_test, global_clf.predict(X_test))
            print(f"Accuracy for global model after {i+number_of_clients} splits : {accuracy}")


if __name__ == "__main__":
    train_set, test_set = mnist_setup.download_dataset()
    X_train, y_train = train_set["images"], train_set["labels"]
    X_test, y_test = test_set["images"], test_set["labels"]

    number_of_clients = 2
    number_of_splits = 51
    X_train_split, y_train_split = utils.split_data(number_of_splits, X_train, y_train)
    print(f"X_train_split[0] has {len(X_train_split[0])} samples: {X_train_split[0]}")
    print(f"y_train_split[0] has {len(y_train_split[0])} samples: {y_train_split[0]}")
    global_clf = utils.create_classifier()

    # for i in range(number_of_splits):
    #     print(f"Training on split {i}")
    #     for j in range(50):
    #         global_clf.partial_fit(X_train_split[i], y_train_split[i], classes=np.arange(10))
    #     # calculate accuracy
    #     accuracy = accuracy_score(y_test, global_clf.predict(X_test))
    #     print(f"Accuracy for global model after {i} splits : {accuracy}")

    train_model_v1(global_clf)
    #global_clf_2 = utils.create_classifier()
    #global_clf_2.fit(X_train, y_train)
    #accuracy = accuracy_score(y_test, global_clf_2.predict(X_test))
    #print(f"Accuracy for global model fitted once: {accuracy}")



