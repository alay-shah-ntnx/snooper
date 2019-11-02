#!/bin/bash
set -xe

FILER_SERVER="http://filer.dev.eng.nutanix.com:8080/"
FILER_DIRECTORY="Users/ashah/filer/snooper/"
FILES=(
"v1.1.0.tar.gz"
"wireshark-2.6.3-1.x86_64.rpm"
"wireshark-qt-2.6.3-1.x86_64.rpm"
)

PROJ_NAME="snooper"
_CWD=${PWD}
BUILD_DIR="__build"
_ROOT_DIR="ROOTDIR"
_OUTPUT_DIR="OUTPUT"

mkdir ${BUILD_DIR}
pushd ${BUILD_DIR}
mkdir ${_ROOT_DIR}
pushd ${_ROOT_DIR}
root_dir=${PWD}
mkdir ${PROJ_NAME}
pushd ${PROJ_NAME}
payload_dir=${PWD}

popd #PROJ_NAME
popd #_ROOT_DIR
popd #BUILD_DIR

cp -rf etc configs infra  packages ${payload_dir}
cp -f setmeup.sh ${root_dir}
pushd ${payload_dir}

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

pushd packages
for file in "${FILES[@]}"; do
    download "$file"
done
popd #packages
popd #payload_dir

pushd ${BUILD_DIR}
mkdir ${_OUTPUT_DIR}
pushd ${_OUTPUT_DIR}
output_dir_path="$PWD"
popd #_OUTPUT_DIR
popd #BUILD_DIR
pushd ${root_dir}


tar zcvf ${output_dir_path}/snooper.tar.gz ${PROJ_NAME}
cp setmeup.sh ${output_dir_path}/.

popd #root_dir


#tar zcvf snooper.tar.gz requirements.txt  infra
