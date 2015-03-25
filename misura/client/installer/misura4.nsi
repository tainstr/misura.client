!define VERSION "0-py2.6.5"

; Eseguibili
!define depath	"\\Essmeridia\software\Misura4_Dep"
!define python	"python-2.6.6.msi"
!define setup 	"setuptools-0.6c11.win32-py2.6.exe"
!define pil		"PIL-1.1.7.win32-py2.6.exe"
!define numpy	"numpy-1.5.1-win32-superpack-python2.6.exe"
!define numexpr	"numexpr-1.4.2.win32-py2.6.exe"
!define scipy	"scipy-0.9.0rc1-win32-superpack-python2.6.exe"
!define pyqt	"PyQt-Py2.6-gpl-4.8.3-1.exe"
; Nota: cython.exe va creato dallo zip scaricato dal sito, indicando come directory di destinazione
; C:\Python26\Lib\site-packages\cython
!define cython	"Cython-0.14.1.exe"
!define tables	"tables-2.2.1.win32-py2.6.exe"
!define bonjour	"BonjourSetup.exe"
!define pybonjour	"pybonjour-1.1.1.tar.gz"
!define qtiplot	"qtiplot-0.9.8.2.exe"
!define pyodbc	"pyodbc-2.1.8.win32-py2.6.exe"
!define	hdfview	"hdfview_install_windows_vm.exe"
!define svn		"TortoiseSVN-1.6.12.20536-win32-svn-1.6.15.msi"
!define misura	"MisuraClient.exe"
!define zip		"7z.exe"

!define sitePackages	"C:\Python26\Lib\site-packages"
!define easyInstall		"C:\Python26\Scripts\easy_install.exe"


Name "Misura4 Development Environment"
BrandingText "Misura4 Devel - ${VERSION}"
OutFile "Misura4_dev.${VERSION}.exe"
SetCompress off

ShowInstDetails show

!include "MUI.nsh"


Page components
ComponentText "Misura4 Development Sub-Packages"

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

InstallDir "$DESKTOP\Misura_Setup"

Function cko
	Pop $0
	IntCmp $0 0 is0 not0 not0
not0:
	MessageBox MB_OK "The sub-installer exited with an error"
is0:
FunctionEnd


Section "-"
	SetOutPath $INSTDIR
	File "${depath}\${zip}"
SectionEnd

Section "Python"
	File "${depath}\${python}"
	nsExec::ExecToLog 'msiexec /i "$INSTDIR\${python}"'
	Call cko
SectionEnd

Section "SetupTools"
	File "${depath}\${setup}"
	nsExec::ExecToLog "$INSTDIR\${setup}"
	Call cko
SectionEnd

Section "PIL"
	File "${depath}\${pil}"
	nsExec::ExecToLog "$INSTDIR\${pil}"
	Call cko
SectionEnd

Section "NumPy"
	File "${depath}\${numpy}"
	nsExec::ExecToLog "$INSTDIR\${numpy}"
	Call cko
SectionEnd

Section "NumExpr"
	File "${depath}\${numexpr}"
	nsExec::ExecToLog "$INSTDIR\${numexpr}"
	Call cko
SectionEnd

Section "SciPy"
	File "${depath}\${scipy}"
	nsExec::ExecToLog "$INSTDIR\${scipy}"
	Call cko
SectionEnd

Section "PyQt"
	File "${depath}\${pyqt}"
	nsExec::ExecToLog "$INSTDIR\${pyqt}"
	Call cko
SectionEnd

Section "Cython"
	File "${depath}\${cython}"
	nsExec::ExecToLog "$INSTDIR\${cython}"
	Call cko
SectionEnd

Section "PyTables"
	File "${depath}\${tables}"
	nsExec::ExecToLog "$INSTDIR\${tables}"
	Call cko
SectionEnd

Section "Bonjour"
	File "${depath}\${bonjour}"
	nsExec::ExecToLog "$INSTDIR\${bonjour}"
	Call cko
SectionEnd

Section "PyBonjour"
	File "${depath}\${pybonjour}"
	nsExec::ExecToLog '${easyInstall} "$INSTDIR\${pybonjour}"'
	Call cko
SectionEnd

Section "QtiPlot"
	File "${depath}\${qtiplot}"
	nsExec::ExecToLog "$INSTDIR\${qtiplot}"
	Call cko
SectionEnd

Section "PyODBC"
	File "${depath}\${pyodbc}"
	nsExec::ExecToLog "$INSTDIR\${pyodbc}"
	Call cko
SectionEnd

Section "HDF View"
	File "${depath}\${hdfview}"
	nsExec::ExecToLog "$INSTDIR\${hdfview}"
	Call cko
SectionEnd

Section "Tortoise SVN Client"
	File "${depath}\${svn}"
	nsExec::ExecToLog 'msiexec /i "$INSTDIR\${svn}"'
	Call cko
SectionEnd




