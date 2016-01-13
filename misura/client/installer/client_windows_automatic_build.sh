#!/usr/bin/bash

CODE_BASE=$USERPROFILE/Desktop/misura4
DEPLOY_DIR=//Ess-server/company/Installations/Misura4
CLIENT_DIR=$CODE_BASE/misura.client/misura/client
CANON_DIR=$CODE_BASE/misura.canon/misura/canon

VEUSZ_DIR=$CODE_BASE/veusz
INSTALLER_DIR=$CLIENT_DIR/installer
SPEC_FILE=$INSTALLER_DIR/client_windows_pyinst.spec
OUTPUT_ROOT_DIR=$INSTALLER_DIR/dist
OUTPUT_MISURA4_DIR=$OUTPUT_ROOT_DIR/misura4

NEW_COMMITS=$(git log HEAD..origin/master --oneline)

if [ -z "$NEW_COMMITS" ]; then
	echo "No changes detected."
	exit 0
fi

echo "Changes detected on remote. Pulling sources..."
git pull
echo "Done."
echo "Removing old local build..."
rm -rf $OUTPUT_ROOT_DIR
echo "Done."

echo "Let's start..."
mkdir $OUTPUT_ROOT_DIR
pyinstaller -y $SPEC_FILE

if [ $? -ne 0 ]; then
	echo "Error building Misura4 package."
	exit 1
fi


cp -r $OUTPUT_ROOT_DIR/configuration/* $OUTPUT_MISURA4_DIR
cp -r $OUTPUT_ROOT_DIR/browser/* $OUTPUT_MISURA4_DIR
cp -r $OUTPUT_ROOT_DIR/acquisition/* $OUTPUT_MISURA4_DIR

# hack to make svg icons work also on Windows Vista
cp C:/Python27/Lib/site-packages/PyQt4/plugins/imageformats/qsvg4.dll "$OUTPUT_MISURA4_DIR/qt4_plugins/imageformats/"

echo "Done!"
echo
