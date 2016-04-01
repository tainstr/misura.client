#!/bin/bash

set -e

LOGGED_USER=`whoami`
TARGET_DIR=/opt/misura4
BASH_RC=~/.bashrc

sudo apt-get -y update
sudo apt-get -y upgrade
sudo apt-get -y build-dep veusz
sudo apt-get -y install python-qt4-sql libqt4-sql-sqlite
sudo apt-get -y install wget unzip git-core python-setuptools python-scipy
sudo apt-get -y install libhdf5-7 libhdf5-dev
sudo easy_install pip

export HDF5_DIR=/opt/local
sudo -H pip install tables pycrypto pygments

echo
echo
echo Creating $TARGET_DIR
sudo mkdir -p $TARGET_DIR
sudo chown $LOGGED_USER $TARGET_DIR
echo "done."

echo "Getting Misura4 sources..."
cd $TARGET_DIR
git clone https://bitbucket.org/tainstr/misura.client.git
git clone https://bitbucket.org/tainstr/misura.canon.git
git clone https://github.com/tainstr/veusz.git
echo "done cloning."

echo Updating .bashrc
TARGET_DIR=/opt/misura4
LINE="export VEUSZ_RESOURCE_DIR=\"$TARGET_DIR/veusz\""
grep -q -F "$LINE" $BASH_RC || echo $LINE >> $BASH_RC
LINE="export PYTHONPATH=\$PYTHONPATH:$TARGET_DIR/veusz"
grep -q -F "$LINE" $BASH_RC || echo $LINE >> $BASH_RC
LINE="source \"$TARGET_DIR/misura.canon/misura/canon/canondefine.sh\""
grep -q -F "$LINE" $BASH_RC || echo $LINE >> $BASH_RC
LINE="source \"$TARGET_DIR/misura.client/misura/client/clientdefine.sh\""
grep -q -F "$LINE" $BASH_RC || echo $LINE >> $BASH_RC


source $BASH_RC

echo "Building Veusz helpers"
cd $TARGET_DIR/veusz
python setup.py build_ext --inplace

echo "Misura Client Setup complete"
echo "To launch the client"
echo "maq, mbr, mgr"
