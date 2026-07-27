#!/bin/ash
set -ux

if [ $# -eq 0 ]; then
	echo "ERROR: Wrong number of arguments. Specify project name" >/dev/stderr
	exit 1
fi

api_url="https://api.github.com/repos/chenxiaolong/${1}/releases/latest"
json=$(wget -q -O- $api_url)

version=$(jq -r '.tag_name | sub("^v"; "")' <(echo $json))
zip_download_url=$(jq -r '.assets[] | select(.name | endswith("-x86_64-unknown-linux-gnu.zip")) | .browser_download_url' <(echo $json))
sig_download_url=$(jq -r '.assets[] | select(.name | endswith("-x86_64-unknown-linux-gnu.zip.sig")) | .browser_download_url' <(echo $json))
zip_name=$(jq -r '.assets[] | select(.name | endswith("-x86_64-unknown-linux-gnu.zip")) | .name' <(echo $json))
sig_name=$(jq -r '.assets[] | select(.name | endswith("-x86_64-unknown-linux-gnu.zip.sig")) | .name' <(echo $json))

cd $(mktemp -d)
wget "$zip_download_url"
wget "$sig_download_url"

echo chenxiaolong ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDOe6/tBnO7xZhAWXRj3ApUYgn+XZ0wnQiXM8B7tPgv4 > chenxiaolong_trusted_keys
ssh-keygen -Y verify -f chenxiaolong_trusted_keys -I chenxiaolong -n file -s $sig_name < $zip_name
ret_code=$?

if [ $ret_code -eq 0 ]; then
	unzip -d /usr/local/bin $zip_name
	rm -f $zip_name $sig_name
elif [ $ret_code -eq 255 ]; then
	echo "ERROR: Signature verification failed" >/dev/stderr
else
	echo "ERROR: Unknown error" >/dev/stderr
fi
