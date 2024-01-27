FROM python:3.11-slim

# Set the working directory
WORKDIR /opt

# Install wget if it's not available
RUN apt-get update && apt-get install -y wget

# Download OpenWhisk CLI
RUN wget https://github.com/apache/openwhisk-cli/releases/download/1.2.0/OpenWhisk_CLI-1.2.0-linux-amd64.tgz

# Extract the downloaded file
RUN tar zxvf OpenWhisk_CLI-1.2.0-linux-amd64.tgz

# Move the binary to a directory in the PATH
RUN mv wsk /usr/local/bin/wsk

RUN wsk property set --apihost owdev-nginx.openwhisk.svc.cluster.local

RUN wsk property set --auth 23bc46b1-71f6-4ed5-8c54-816aa4f8c502:123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP

RUN apt-get install -y vim

RUN apt-get install -y lsof

RUN apt-get install -y net-tools

# Set the working directory for your application
WORKDIR /app

# Copy the application files to the container
COPY . .

# Install any dependencies
RUN pip install -r requirements.txt

# Command to run when the container starts
CMD ["python","app.py"]
