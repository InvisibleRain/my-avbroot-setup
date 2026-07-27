FROM docker.io/python:3.14-alpine

COPY . /app

RUN apk update && apk upgrade && apk add openssh-keygen jq

RUN /app/docker/install_dependency.sh afsr
RUN /app/docker/install_dependency.sh avbroot
RUN /app/docker/install_dependency.sh custota

RUN python3 -m pip install --break-system-packages -r /app/requirements.txt

WORKDIR /app

