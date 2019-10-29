#!/bin/bash

FILER_SERVER="http://filer.dev.eng.nutanix.com:8080/"
FILER_DIRECTORY="Users/ashah/filer/snooper/"
FILES=(
"v1.1.0.tar.gz"
"wireshark-2.6.3-1.x86_64.rpm"
"wireshark-qt-2.6.3-1.x86_64.rpm"
)

function _check_integrity {
    local file_name="$1"
    (
    set -e
    md5sum -c ${file_name}
    rm -f ${file_name}
    )
    _ret=$?
    if [ ${_ret} -ne 0 ]; then
	    exit ${_ret}
    fi
    
}
function download {
    local file_name="$1"
    local md5_file=${file_name}.md5
    wget -O ${file_name} ${FILER_SERVER}/${FILER_DIRECTORY}/${file_name}
    wget -O ${md5_file} ${FILER_SERVER}/${FILER_DIRECTORY}/${md5_file}
    _check_integrity ${md5_file}
}


for file in "${FILES[@]}"; do
    download "$file"
done

tar zcvf snooper.tar.gz requirements.txt  infra
