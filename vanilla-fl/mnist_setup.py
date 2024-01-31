import gzip
import os
import zipfile
from io import BytesIO

import numpy as np
import requests


def download_mnist_files(url_base, file_names, save_dir):
    # Download MNIST dataset files only if all four files are missing
    missing_files = [not os.path.exists(os.path.join(save_dir, file_name)) for file_name in file_names]
    if not any(missing_files):
        print("MNIST dataset files already exist")
        return

    for file_name in file_names:
        url = url_base + file_name
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            if file_name.startswith('t10k'):
                file_name = file_name.replace('t10k', 'test')
            file_path = os.path.join(save_dir, file_name)
            with open(file_path, 'wb') as f:
                f.write(response.raw.read())
            print(f"Downloaded {file_name}")
        else:
            print(f"Failed to download {file_name}")


def download_emnist_digit_files(url, save_dir):
    digit_files = [
        'gzip/emnist-digits-train-images-idx3-ubyte.gz',
        'gzip/emnist-digits-train-labels-idx1-ubyte.gz',
        'gzip/emnist-digits-test-images-idx3-ubyte.gz',
        'gzip/emnist-digits-test-labels-idx1-ubyte.gz'
    ]

    # Download MNIST dataset files only if all four files are missing
    missing_files = [not os.path.exists(os.path.join(save_dir, file_name.split('gzip/emnist-digits-')[1])) for file_name
                     in digit_files]
    if any(missing_files):
        print("Downloading EMNIST dataset files (~550MB, this may take a while)")
        _download_emnist_files(url, digit_files, save_dir)
    else:
        print("EMNIST dataset files already exist")


def _download_emnist_files(url, file_names, save_dir: str):
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
            os.rmdir(os.path.join(save_dir, 'gzip'))
    else:
        print(f"Failed to download from {url}")


def extract_images_and_labels(image_file, label_file):
    with gzip.open(image_file, 'rb') as f:
        images = np.frombuffer(f.read(), np.uint8, offset=16).reshape(-1, 28, 28)

    with gzip.open(label_file, 'rb') as f:
        labels = np.frombuffer(f.read(), np.uint8, offset=8)

    return images, labels


def extract_images_and_labels_as_1d_vector(file_path):
    with gzip.open(file_path, 'rb') as f_in:
        if 'images' in file_path:
            return np.frombuffer(f_in.read(), np.uint8).reshape(-1, 784)  # 28x28 images
        else:
            return np.frombuffer(f_in.read(), np.uint8)


def _split_and_save_dataset_locally(images, labels, parts, directory, dataset_name='mnist'):
    # clear directory
    for file in os.listdir(directory):
        os.remove(os.path.join(directory, file))

    # Splitting data into equal parts
    indices = np.arange(len(images))
    np.random.shuffle(indices)

    size = len(images) // parts
    for i in range(parts):
        print(f"Saving: part {i} of {parts}")
        part_indices = indices[i * size:(i + 1) * size] if i < parts - 1 else indices[i * size:]

        if i + 1 < 10:
            nr = f'0{i + 1}'
        else:
            nr = i + 1

        # Save train images and labels
        save_gzipped_file(images[part_indices], os.path.join(directory, f'part{nr}_{dataset_name}_train_images.gz'))
        save_gzipped_file(labels[part_indices], os.path.join(directory, f'part{nr}_{dataset_name}_train_labels.gz'))


def prepare_splits(directory, images, labels, parts, dataset_name='mnist'):
    # check if splits already exist - create them otherwise
    if not os.path.exists(directory):
        print(f"Creating directory {directory}")
        os.makedirs(directory)
    else:
        print(f"Directory {directory} already exists")
    if not os.listdir(directory) or len(os.listdir(directory)) != parts * 2:
        print("Creating splits")
        _split_and_save_dataset_locally(
            images=images,
            labels=labels,
            parts=parts,
            directory=directory,
            dataset_name=dataset_name
        )
    else:
        print("Splits already exist")

    names = get_split_filenames(dataset_name)
    splits = {}
    for n in names:
        splits[n] = False
    return splits


def save_gzipped_file(data, file_path):
    # Ensure the directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with gzip.open(file_path, 'wb') as f:
        f.write(data)


def load_and_extract_data(save_dir='MNIST_data'):
    train_images, train_labels = extract_images_and_labels(os.path.join(save_dir, 'train-images-idx3-ubyte.gz'),
                                                           os.path.join(save_dir, 'train-labels-idx1-ubyte.gz'))
    test_images, test_labels = extract_images_and_labels(os.path.join(save_dir, 'test-images-idx3-ubyte.gz'),
                                                         os.path.join(save_dir, 'test-labels-idx1-ubyte.gz'))

    print(f"Training set (images, labels): {train_images.shape}, {train_labels.shape}")
    print(f"Test set (images, labels): {test_images.shape}, {test_labels.shape}")

    train_set = {
        'images': train_images.reshape(-1, 784),
        'labels': train_labels.reshape(-1, )
    }
    test_set = {
        'images': test_images.reshape(-1, 784),
        'labels': test_labels.reshape(-1, )
    }

    return train_set, test_set


def download_dataset(dataset='emnist'):
    # Directory where to save the downloaded files
    if dataset == 'emnist':
        save_dir = 'EMNIST_data'
        os.makedirs(save_dir, exist_ok=True)
        url = 'https://rds.westernsydney.edu.au/Institutes/MARCS/BENS/EMNIST/emnist-gzip.zip'
        download_emnist_digit_files(url, save_dir)
    else:
        save_dir = 'MNIST_data'
        os.makedirs(save_dir, exist_ok=True)
        url_base = 'http://yann.lecun.com/exdb/mnist/'
        file_names = ['train-images-idx3-ubyte.gz', 'train-labels-idx1-ubyte.gz',
                      't10k-images-idx3-ubyte.gz', 't10k-labels-idx1-ubyte.gz']
        download_mnist_files(url_base, file_names, save_dir)

    # Load and extract data
    return load_and_extract_data(save_dir)


def get_split_filenames(dataset_name='mnist'):
    files = os.listdir(f'split_{dataset_name}_data')
    parts = [(file.split('_')[0] + '_' + file.split('_')[1]) for file in files]
    # remove duplicates
    parts = list(set(parts))
    # sort
    parts.sort()

    return parts
