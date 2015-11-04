#!/bin/bash

# symbolic link needed for python bug
# https://bugs.python.org/issue11374
ln -s /opt/misura4/misura.canon/misura/canon /opt/misura4/misura.client/misura/canon

pyinstaller -y client_linux_pyinst.spec
rm /opt/misura4/misura.client/misura/canon

OUT_DIR=/opt/misura4/misura.client/misura/client/installer/dist

cp $OUT_DIR/configuration/* $OUT_DIR/misura4/
cp $OUT_DIR/browser/* $OUT_DIR/misura4/
cp $OUT_DIR/acquisition/* $OUT_DIR/misura4/

cd $OUT_DIR
tar c misura4 | bzip2 -9 > misura4.tbz2
cd -

echo Done: you can find misura4 tbz2 in $OUT_DIR
echo
