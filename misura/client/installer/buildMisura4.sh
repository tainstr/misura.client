#!/bin/bash

# symbolic link needed for python bug
# https://bugs.python.org/issue11374
ln -s /opt/misura4/misura.canon/misura/canon /opt/misura4/misura.client/misura/canon

pyinstaller -y client_linux_pyinst.spec
rm /opt/misura4/misura.client/misura/canon
