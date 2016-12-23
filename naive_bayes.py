import csv
from sklearn.naive_bayes import GaussianNB
import numpy as np


def _read_lines(trainingset_path):
    with open(trainingset_path, 'r') as data:
        reader = csv.reader(data)
        # skipping headers
        next(reader)

        for line in reader:
            yield [float(i) for i in line]

def train_naive_bayes(trainingset_path):
    X = []
    Y = []
    for line in _read_lines(trainingset_path):
        X.append(line[:-1])
        Y.append(line[-1])
    clf = GaussianNB()
    clf.fit(X, Y)

    return clf



