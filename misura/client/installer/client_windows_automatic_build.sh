#!/usr/bin/bash

CODE_BASE=$USERPROFILE/Desktop/misura4
DEPLOY_DIR=//Ess-server/company/Installations/Misura4
CLIENT_DIR=$CODE_BASE/misura.client/misura/client
CANON_DIR=$CODE_BASE/misura.canon/misura/canon

VEUSZ_DIR=$CODE_BASE/veusz
INSTALLER_DIR=$CLIENT_DIR/installer
SPEC_FILE=$INSTALLER_DIR/client_windows_pyinst.spec
DISTRIBUTION_DIR=$INSTALLER_DIR/dist
OUTPUT_MISURA4_DIR=$DISTRIBUTION_DIR/misura4
CANON_LINK=$CLIENT_DIR/../canon

BUILD_IN_PROGRSS_FILE=$INSTALLER_DIR/build_in_progress
LAST_BUILD_STATUS_FILE=$INSTALLER_DIR/last_build_status
touch $LAST_BUILD_STATUS_FILE

if [ -a $BUILD_IN_PROGRSS_FILE ]; then
	echo "Build already in progress."
	exit 0
fi

git remote update
NEW_COMMITS=$(git log HEAD..origin/master --oneline)
if [ -z "$NEW_COMMITS" ]; then
	echo "No changes detected."
	exit 0
fi

echo "Changes detected on remote. Pulling sources..."
git pull --rebase master
cd $CANON_DIR
git pull --rebase master
cd -
echo "Done."
echo "Removing old local build..."
rm -rf "$DISTRIBUTION_DIR"
echo "Done."

echo "Let's start..."
touch $BUILD_IN_PROGRSS_FILE

rm -rf "$CANON_LINK"
ln -s "$CANON_DIR" "$CANON_LINK"

mkdir "$DISTRIBUTION_DIR"
pyinstaller -y "$SPEC_FILE"

if [ $? -ne 0 ]; then
	echo "Error building Misura4 package."
	rm -f $BUILD_IN_PROGRSS_FILE
	echo "Pyinstaller error!" > $LAST_BUILD_STATUS_FILE
	exit 1
fi

rm -rf $CANON_LINK

cp -r "$DISTRIBUTION_DIR/configuration/"* $OUTPUT_MISURA4_DIR
cp -r "$DISTRIBUTION_DIR/browser/"* $OUTPUT_MISURA4_DIR
cp -r "$DISTRIBUTION_DIR/acquisition/"* $OUTPUT_MISURA4_DIR

# hack to make svg icons work also on Windows Vista
cp C:/Python27/Lib/site-packages/PyQt4/plugins/imageformats/qsvg4.dll "$OUTPUT_MISURA4_DIR/qt4_plugins/imageformats/"
# hack in case of Anaconda python distribution
cp C:/Anaconda2/Library/bin/mkl_* "$OUTPUT_MISURA4_DIR/"
rm -f $BUILD_IN_PROGRSS_FILE
echo "OK" > $LAST_BUILD_STATUS_FILE

echo "Done!"
echo
