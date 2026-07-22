FROM docker.io/python:3.14-alpine

COPY . /app

RUN python3 -m pip install --break-system-packages -r /app/requirements.txt
RUN apk update && apk upgrade && apk add openssh-keygen
RUN wget https://github.com/chenxiaolong/afsr/releases/download/v1.0.4/afsr-1.0.4-x86_64-unknown-linux-gnu.zip && unzip -d /usr/local/bin afsr-1.0.4-x86_64-unknown-linux-gnu.zip && rm afsr-1.0.4-x86_64-unknown-linux-gnu.zip
RUN wget https://github.com/chenxiaolong/avbroot/releases/download/v3.32.0/avbroot-3.32.0-x86_64-unknown-linux-gnu.zip && unzip -d /usr/local/bin avbroot-3.32.0-x86_64-unknown-linux-gnu.zip && rm avbroot-3.32.0-x86_64-unknown-linux-gnu.zip
RUN wget https://github.com/chenxiaolong/Custota/releases/download/v6.3/custota-tool-6.3-x86_64-unknown-linux-gnu.zip && unzip -d /usr/local/bin custota-tool-6.3-x86_64-unknown-linux-gnu.zip && rm custota-tool-6.3-x86_64-unknown-linux-gnu.zip

WORKDIR /app

