#!/bin/bash

set -e

LOGGED_USER=`whoami`
TARGET_DIR=/opt/misura4
BASH_RC=~/.bashrc
PROFILE_RC=~/.profile
DESKTOP=`xdg-user-dir DESKTOP`

function update_bashrc {

	echo Updating $1
	LINE="export VEUSZ_RESOURCE_DIR=\"$TARGET_DIR/veusz\""
	grep -q -F "$LINE" $1 || echo $LINE >> $1
	LINE="export PYTHONPATH=\$PYTHONPATH:$TARGET_DIR/veusz"
	grep -q -F "$LINE" $1 || echo $LINE >> $1
	LINE="source \"$TARGET_DIR/misura.canon/misura/canon/canondefine.sh\""
	grep -q -F "$LINE" $1 || echo $LINE >> $1
	LINE="source \"$TARGET_DIR/misura.client/misura/client/clientdefine.sh\""
	grep -q -F "$LINE" $1 || echo $LINE >> $1
}

update_bashrc "$BASH_RC"
update_bashrc "$PROFILE_RC"


function create_icon {
echo Creating desktop icon for $1
echo "[Desktop Entry]
Type=Application
Exec=bash -c \"source /home/$LOGGED_USER/.profile; python /opt/misura4/misura.client/misura/client/bin/$1.py\"
Terminal=false
Name=$1
Icon=/opt/misura4/misura.client/misura/client/art/$2" > "$DESKTOP/$1.desktop"
chmod +x "$DESKTOP/$1.desktop"
}

create_icon acquisition icon.svg
create_icon browser browser.svg
create_icon graphics graphics.svg

echo "INSTALLING..."

sudo apt-get -y update
sudo apt-get -y upgrade
sudo apt-get -y build-dep veusz
sudo apt-get -y install python-qt4-sql libqt4-sql-sqlite
#sudo apt-get -y install python-pyqt5 libqt5sql5-sqlite
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


echo "Building Veusz helpers"
cd $TARGET_DIR/veusz
python setup.py build_ext --inplace

source $BASH_RC


echo "Misura Client Setup complete"
