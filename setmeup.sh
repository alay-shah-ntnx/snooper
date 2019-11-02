set -ex
tar zxvf snooper.tar.gz
pushd snooper
yum install -y epel-release
yum install -y packages/wireshark-2.6.3-1.x86_64.rpm
yum install -y packages/wireshark-qt-2.6.3-1.x86_64.rpm
yum install -y python-devel

python packages/get-pipe.py
pip install virtualenv
virtualenv -p python2.7 env
source env/bin/activate

_TPM="env/.nutanix.tmp"
mkdir -p ${_TPM}
tar zxvf packages/v1.1.0.tar.gz -C ${_TPM}
pushd ${_TPM}
pushd basemap-1.1.0/geos-3.3.3
./configure --enable-python
make
make install

pip install matplotlib
popd
pushd  basemap-1.1.0
python setup.py install
popd
popd

pip install -r etc/requirements.txt
rm -rf ${_TPM}
