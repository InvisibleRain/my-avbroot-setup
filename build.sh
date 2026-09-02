#!/bin/bash
set -eu

distro="grapheneos"
device="frankel"
#device="pdx245"
#distro="lineageos"
out_dir="/var/lib/containers/storage/volumes/my-avbroot-setup_mnt/_data"

function download_module() {
        module_api_url="https://api.github.com/repos/chenxiaolong/${1}/releases/latest"
        module_json=$(curl -s $module_api_url)
        module_zip_download_url=$(jq -r '.assets[] | select(.name | endswith("-release.zip")) | .browser_download_url' <(echo $module_json))
        module_sig_download_url=$(jq -r '.assets[] | select(.name | endswith("-release.zip.sig")) | .browser_download_url' <(echo $module_json))
        module_zip_filename=$(jq -r '.assets[] | select(.name | endswith("-release.zip")) | .name' <(echo $module_json))
        module_sig_filename=$(jq -r '.assets[] | select(.name | endswith("-release.zip.sig")) | .name' <(echo $module_json))
        curl -sL $module_zip_download_url -o ${out_dir}/${module_zip_filename}
        curl -sL $module_sig_download_url -o ${out_dir}/${module_sig_filename}
        echo $module_zip_filename
}

if [ $distro = "grapheneos" ]; then
        echo "Building GrapheneOS"
        grapheneos_channel="stable-security-preview"
        custota_dir="/var/www/custota"
        grapheneos_releases_base_url="https://releases.grapheneos.org"
        grapheneos_latest_release=$(curl -s "${grapheneos_releases_base_url}/${device}-${grapheneos_channel}")
        grapheneos_latest_version=$(echo $grapheneos_latest_release | awk '{print $1}')
        grapheneos_version_in_custota=$(ls ${custota_dir}/*.zip | awk -F/ '{print $NF}' | awk -F '-' '{print $3}')
        if [[ $grapheneos_latest_version -le $grapheneos_version_in_custota ]]; then
                echo 'GrapheneOS OTA image is up to date'
                exit 2
        fi
        grapheneos_ota_filename="${device}-ota_update-${grapheneos_latest_version}.zip"
        grapheneos_sig_filename="${device}-ota_update-${grapheneos_latest_version}.zip.sig"
        grapheneos_ota_download_url="${grapheneos_releases_base_url}/${grapheneos_ota_filename}"
        grapheneos_sig_download_url="${grapheneos_releases_base_url}/${grapheneos_sig_filename}"
        echo "Downloading $grapheneos_ota_filename"
        curl -sL $grapheneos_ota_download_url -o ${out_dir}/${grapheneos_ota_filename}
        curl -sL $grapheneos_sig_download_url -o ${out_dir}/${grapheneos_sig_filename}
        echo "Downloading modules"
        bcr_filename=$(download_module "BCR")
        custota_filename=$(download_module "Custota")

        patched_filename="${device}-ota_update-${grapheneos_latest_version}-custota-bcr.zip"
        echo "Building $patched_filename"
        podman run \
                -v my-avbroot-setup_mnt:/mnt \
                --rm localhost/my-avbroot-setup \
                /app/patch.py \
                --verify-cert-ota /mnt/grapheneos-releasekey.x509.pem \
                --input /mnt/${grapheneos_ota_filename} \
                --output /mnt/${patched_filename} \
                --sign-key-avb /mnt/avb.key \
                --sign-key-ota /mnt/ota.key \
                --sign-cert-ota /mnt/ota.crt \
                --patch-arg='--rootless' \
                --tmp-dir /var/tmp/ \
                --module-bcr /mnt/${bcr_filename} \
                --module-custota /mnt/${custota_filename}

        echo "Moving ${patched_filename} to ${out_dir}"
        rm -f $custota_dir/*.zip \
                ${out_dir}/${grapheneos_ota_filename}
        mv ${out_dir}/${patched_filename} $custota_dir

elif [ $distro = "lineageos" ]; then
        echo "Building LineageOS"
        download_base="https://download.lineageos.org"
        mirrorbits_base="https://mirrorbits.lineageos.org"
        ota_dir="/var/lib/containers/storage/volumes/lineageota_builds/_data/"
        api_url="${download_base}/api/v2/devices/${device}/builds"
        bcr_filename=$(download_module "BCR")
        oemunlock_filename=$(download_module "OEMUnlockOnBoot")
        json=$(curl -s $api_url)
        filepath=$(jq -r .[0].files[0].filepath <(echo $json))
        filename=$(jq -r .[0].files[0].filename <(echo $json))
        download_url="${mirrorbits_base}${filepath}"
        echo "Downloading $filename"
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
                --tmp-dir /var/tmp/ \
                --module-fdroid /mnt/org.fdroid.fdroid.privileged.ota_2130.zip \
                --module-mtgapps /mnt/MindTheGapps-16.0.0-arm64-20260409_073023.zip \
                --module-bcr /mnt/${bcr_filename} \
                --module-oemunlockonboot /mnt/${oemunlock_filename}

        echo "Moving ${patched_filename} to ${out_dir}"
        rm -f $ota_dir/*.zip \
                ${out_dir}/${filename}
        mv ${out_dir}/${patched_filename} $ota_dir
        systemctl restart podman-compose@lineageota.service
fi

