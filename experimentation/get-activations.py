import subprocess
import csv
import argparse

# Create an ArgumentParser object
parser = argparse.ArgumentParser()

# Define a positional argument
parser.add_argument('limit', help='number of latest activations')

# Parse the command-line arguments
args = parser.parse_args()

# Access the values of parsed arguments
limit = int(args.limit)

print(f'Limit is {limit}')

# Run the command and save output to a .txt file
subprocess.run(['wsk', '-i', 'activation', 'list'])

# Function to run the command and save/append output to a .txt file
def run_command(cmd, output_file, append=False):
    with open(output_file, "a" if append else "w") as file:
        subprocess.run(cmd, stdout=file, text=True, check=True)

# Function to convert .txt file to .csv
def txt_to_csv(input_file, output_file):
    with open(input_file, 'r') as infile:
        lines = infile.readlines()

    # Remove headers from all chunks except the first
    lines = [line for i, line in enumerate(lines) if i == 0 or not line.startswith('Datetime')]

    data = []
    for line in lines:
        columns = line.split(maxsplit=7)
        columns[6] = columns[6].strip()
        if len(columns) > 8:
            columns[7:] = [' '.join(columns[7:])]
        data.append(columns)

    with open(output_file, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerows(data)

n = limit #n_clients * n_rounds  # example value, change as needed

# File paths
txt_file_path = './out.txt'
csv_file_path = './activations.csv'

# Determine how many calls are needed (200 activations per call)
num_calls = (n + 199) // 200

# Make the necessary calls and append to the .txt file
for i in range(num_calls):
    skip_count = i * 200
    limit = min(200, n - skip_count)
    run_command(['wsk', '-i', 'activation', 'list', '--limit', str(limit), '--skip', str(skip_count)], txt_file_path, append=i > 0)

# Convert the .txt file to a .csv file
txt_to_csv(txt_file_path, csv_file_path)

print(f"The activations have been saved to {csv_file_path}")


