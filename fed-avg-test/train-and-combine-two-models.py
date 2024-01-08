from sklearn import datasets
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn import metrics

# Load the MNIST dataset
digits = datasets.load_digits()

# Split the data into two equal part
X1, X2, y1, y2 = train_test_split(digits.data, digits.target, test_size=0.5, random_state=42)

# Create and train the first model using the first half of the data
model1 = MLPClassifier(hidden_layer_sizes=(64,), max_iter=1000, random_state=42, warm_start=True)
model1.fit(X1, y1)

# Create and train the second model using the second half of the data
model2 = MLPClassifier(hidden_layer_sizes=(64,), max_iter=1000, random_state=42, warm_start=True)
model2.fit(X2, y2)

# Evaluate the models on their respective test sets
predictions1 = model1.predict(X2)
predictions2 = model2.predict(X1)

# Print classification reports for each model
print("Classification Report for Model 1:\n", metrics.classification_report(y2, predictions1))
print("\nClassification Report for Model 2:\n", metrics.classification_report(y1, predictions2))


# print("Coeffs1: ", model1.coefs_)

print("Intercepts1: ", model1.intercepts_[0][1])


# print("Coeffs2: ", model2.coefs_)

print("Intercepts2: ", model2.intercepts_[0][1])

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


# Average the weights for each layer
averaged_coefs = [0.5 * (w1 + w2) for w1, w2 in zip(model1.coefs_, model2.coefs_)]
averaged_intercepts = [0.5 * (b1 + b2) for b1, b2 in zip(model1.intercepts_, model2.intercepts_)]

# Create a new model with the averaged weights
merged_model = MLPClassifier(hidden_layer_sizes=model1.hidden_layer_sizes, activation=model1.activation,
                            solver=model1.solver, alpha=model1.alpha, batch_size=model1.batch_size,
                            learning_rate=model1.learning_rate, max_iter=model1.max_iter,
                            random_state=model1.random_state, warm_start=True)
merged_model.fit(X2, y2) # just to initialize the variables

# Setting the avg coefficients
merged_model.coefs_ = averaged_coefs
merged_model.intercepts_ = averaged_intercepts


predictions_merged = merged_model.predict(X1)

# print("Coeffs avg: ", merged_model.coefs_)

#print("Intercepts avg: ", merged_model.intercepts_[0][1])
print("\nClassification Report for Merged model.\n", metrics.classification_report(y1, predictions_merged))

print("Balanced accuracy 1: ", metrics.balanced_accuracy_score(y2, predictions1))
print("Balanced accuracy 2: ", metrics.balanced_accuracy_score(y1, predictions2))
print("Balanced accuracy merged: ", metrics.balanced_accuracy_score(y1, predictions_merged))


# print("", ((model1.intercepts_[0][1] + model2.intercepts_[0][1])/2 ) - merged_model.intercepts_[0][1])
