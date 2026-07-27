#!/bin/bash

device="pdx245"
download_base="https://download.lineageos.org"
mirrorbits_base="https://mirrorbits.lineageos.org"
out_dir="/var/lib/containers/storage/volumes/my-avbroot-setup_mnt/_data"
ota_dir="/var/lib/containers/storage/volumes/lineageota_builds/_data/"
api_url="${download_base}/api/v2/devices/${device}/builds"

json=$(curl -s $api_url)
filepath=$(jq -r .[0].files[0].filepath <(echo $json))
filename=$(jq -r .[0].files[0].filename <(echo $json))
download_url="${mirrorbits_base}${filepath}"
curl -sL $download_url -o ${out_dir}/${filename}

date=$(jq -r .[0].date <(echo $json) | tr -d '-')
version=$(jq -r .[0].version <(echo $json))
patched_filename="lineage-${version}-${date}-UNOFFICIAL-${device}-fdroid-mtgapps-bcr-oemunlock.zip"
echo "Building ${patched_filename}"
podman run \
	-v my-avbroot-setup_mnt:/mnt \
	--rm localhost/my-avbroot-setup \
	/app/patch.py \
	--verify-cert-ota /mnt/lineage-ota.crt \
	--input /mnt/${filename} \
	--output /mnt/${patched_filename} \
	--sign-key-avb /mnt/avb.key \
	--sign-key-ota /mnt/ota.key \
	--sign-cert-ota /mnt/ota.crt \
	--patch-arg='--clear-vbmeta-flags' \
	--patch-arg='--re-sign=boot' \
	--patch-arg='--re-sign=init_boot' \
	--patch-arg='--rootless' \
	--skip-custota-tool \
	--tmp-dir /var/tmp/
	--module-fdroid /mnt/org.fdroid.fdroid.privileged.ota_2130.zip \
	--module-mtgapps /mnt/MindTheGapps-16.0.0-arm64-20260409_073023.zip \
	--module-bcr /mnt/BCR-3.4-release.zip \
	--module-oemunlockonboot /mnt/OEMUnlockOnBoot-1.4-release.zip \
mv ${out_dir}/${patched_filename} $ota_dir
systemctl restart podman-compose@lineageota.service
