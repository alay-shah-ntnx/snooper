set -ex
yum install -y epel-release
yum install -y wireshark-2.6.3-1.x86_64.rpm
yum install -y wireshark-qt-2.6.3-1.x86_64.rpm
yum install -y python-devel

python get-pipe.py
pip install virtualenv
tar zxvf snooper.tar.gz
virtualenv -p python2.7 env
source env/bin/activate

tar zxvf v1.1.0.tar.gz
pushd basemap-1.1.0/geos-3.3.3
./configure --enable-python
make
make install

pip install matplotlib
popd
pushd  basemap-1.1.0
python setup.py install
popd

pip install -r requirements.txt
rm -rf basemap-1.1.0/ v1.1.0.tar.gz  wireshark-*
