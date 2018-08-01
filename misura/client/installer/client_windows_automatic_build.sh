#!/usr/bin/bash

CODE_BASE=$USERPROFILE/Desktop/misura4
DEPLOY_DIR=//Ess-server/company/Installations/Misura4
CLIENT_DIR=$CODE_BASE/misura.client/misura/client
CANON_DIR=$CODE_BASE/misura.canon/misura/canon
THEGRAM_DIR=$CODE_BASE/thegram

VEUSZ_DIR=$CODE_BASE/veusz
INSTALLER_DIR=$CLIENT_DIR/installer
SPEC_FILE=$INSTALLER_DIR/client_windows_pyinst.spec
DISTRIBUTION_DIR=$INSTALLER_DIR/dist
OUTPUT_MISURA4_DIR=$DISTRIBUTION_DIR/main
CANON_LINK=$CLIENT_DIR/../canon

BUILD_IN_PROGRSS_FILE=$INSTALLER_DIR/build_in_progress
LAST_BUILD_STATUS_FILE=$INSTALLER_DIR/last_build_status
touch $LAST_BUILD_STATUS_FILE

if [ -a $BUILD_IN_PROGRSS_FILE ] && [ -z "$1" ]; then
	echo "Build already in progress."
	exit 0
fi

touch $BUILD_IN_PROGRSS_FILE

# CLIENT #############
git remote update
git checkout master
NEW_CLIENT_COMMITS=$(git log HEAD..origin/master --oneline)
if [ -n "$NEW_CLIENT_COMMITS" ]; then
  git pull --rebase
fi

# CANON ############
cd $CANON_DIR
git remote update
git checkout master
NEW_CANON_COMMITS=$(git log HEAD..origin/master --oneline)
if [ -n "$NEW_CANON_COMMITS" ]; then
  git pull --rebase
fi

# VEUSZ ############
cd $VEUSZ_DIR
git remote update
git checkout master
NEW_VEUSZ_COMMITS=$(git log HEAD..origin/master --oneline)
if [ -n "$NEW_VEUSZ_COMMITS" ]; then
  git pull --rebase
fi

# THEGRAM ############
cd $THEGRAM_DIR
git remote update
git checkout master
NEW_THEGRAM_COMMITS=$(git log HEAD..origin/master --oneline)
if [ -n "$NEW_THEGRAM_COMMITS" ]; then
  git pull --rebase
fi


if [ -z "$1" ] && [ -z "$NEW_CLIENT_COMMITS" ] && [ -z "$NEW_CANON_COMMITS" ] && [ -z "$NEW_VEUSZ_COMMITS" ] && [ -z "$NEW_THEGRAM_COMMITS" ]; then
   echo "No changes detected."
   rm $BUILD_IN_PROGRSS_FILE
   exit 0
fi

##################
cd "$INSTALLER_DIR"
echo "Changes detected."
echo "Removing old local build..."
rm -rf "$DISTRIBUTION_DIR"
echo "Done."

echo "Let's start..."

rm -rf "$CANON_LINK"
ln -s "$CANON_DIR" "$CANON_LINK"

mkdir "$DISTRIBUTION_DIR"
mkdir "$OUTPUT_MISURA4_DIR"



###################
###################
pyinstaller -y --clean --win-private-assemblies "$SPEC_FILE"
###################
###################

# Copy the correct license
cp $CODE_BASE/misura.client/LICENSE.txt $OUTPUT_MISURA4_DIR/LICENSE

# Create version stamps
VERSION="$OUTPUT_MISURA4_DIR/VERSION"
GIT_CLIENT=`git -C "$CLIENT_DIR" log --pretty=format:'%h' -n 1`
GIT_CANON=`git -C "$CANON_DIR" log --pretty=format:'%h' -n 1`
GIT_VEUSZ=`git -C "$VEUSZ_DIR" log --pretty=format:'%h' -n 1`
echo "misura.client = $GIT_CLIENT" > $VERSION
echo "misura.canon = $GIT_CANON" >> $VERSION
echo "veusz = $GIT_VEUSZ" >> $VERSION
STAMP=`date +"%F %T"`
echo "date = $STAMP" >> $VERSION


if [ $? -ne 0 ]; then
	echo "Error building Misura4 package."
	rm -f $BUILD_IN_PROGRSS_FILE
	echo "Pyinstaller error!" > $LAST_BUILD_STATUS_FILE
	exit 1
fi

rm -rf $CANON_LINK

# copy compiled packages
python -m compileall $CODE_BASE/thegram/thegram
cp -r "$CODE_BASE/thegram/thegram" "$OUTPUT_MISURA4_DIR"
# remove sources
find "$OUTPUT_MISURA4_DIR/thegram" -name \*.py -type f -delete

# hack to make svg icons work also on Windows Vista
cp C:/Python27/Lib/site-packages/PyQt4/plugins/imageformats/qsvg4.dll "$OUTPUT_MISURA4_DIR/qt4_plugins/imageformats/"

# hack in case of Anaconda python distribution
CONDADIR=`which conda`
CONDADIR=`dirname "$CONDADIR"`
CONDADIR=`dirname "$CONDADIR"`
cp "$CONDADIR"/Library/bin/mkl_* "$OUTPUT_MISURA4_DIR/"

mv "$OUTPUT_MISURA4_DIR" "$DISTRIBUTION_DIR/misura4"
"C:\Program Files (x86)\NSIS\makensis.exe" "$INSTALLER_DIR/client_windows_setup.nsi"

rm -f $BUILD_IN_PROGRSS_FILE
echo "OK" > $LAST_BUILD_STATUS_FILE

echo "Done!"
echo
