; Change this to specify location to build installer from
; misura.client\misura\client\installer\dist\misura4
!define PYINST_DIR ".\dist\misura4"
!define VEUSZ_SRC_DIR ".\..\..\..\..\"

; HM NIS Edit Wizard helper defines
!define PRODUCT_NAME "Misura"
!define /date DATE "%Y%m%d"
!define PRODUCT_VERSION "4.4-${DATE}"
!define PRODUCT_PUBLISHER "TA Instruments / Waters LLC"
!define PRODUCT_WEB_SITE "http://misura.readthedocs.io"
!define TASK_NAME "misura.exe"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\${TASK_NAME}"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"


SetCompressor /solid lzma
;SetCompress off
; MUI 1.67 compatible ------
!include "MUI.nsh"

; MUI Settings
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; Welcome page
!insertmacro MUI_PAGE_WELCOME
; License page
!insertmacro MUI_PAGE_LICENSE "${PYINST_DIR}\LICENSE"
; Directory page
!insertmacro MUI_PAGE_DIRECTORY
; Components selection page
!insertmacro MUI_PAGE_COMPONENTS
; Instfiles page
!insertmacro MUI_PAGE_INSTFILES
; Finish page
;!define MUI_FINISHPAGE_RUN "$INSTDIR\${TASK_NAME}"
!define MUI_FINISHPAGE_LINK "Open Misura Documentation"
!define MUI_FINISHPAGE_LINK_LOCATION "${PRODUCT_WEB_SITE}"
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_INSTFILES

; Language files
!insertmacro MUI_LANGUAGE "English"

; MUI end ------

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "misura-${PRODUCT_VERSION}.exe"
InstallDir "$PROGRAMFILES\Misura"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
ShowInstDetails show
ShowUnInstDetails show

; taken from https://stackoverflow.com/a/47174096
!macro IsRunning 
  DetailPrint "Checking open instance..."
  Delete $TEMP\misuraproc.tmp
  ExecWait "cmd /c for /f $\"tokens=1,2$\" %i in ('tasklist') do (if /i %i EQU ${TASK_NAME} fsutil file createnew $TEMP\misuraproc.tmp 0)"
  IfFileExists $TEMP\misuraproc.tmp 0 notRunning
   ;we have atleast one main window active
   MessageBox MB_OK|MB_ICONEXCLAMATION "Misura is running. Please close all instances and retry. If no Misura window is visible, check for misura.exe in the task manager or reboot." /SD IDOK
   Quit
  notRunning:
	DetailPrint "No running ${TASK_NAME} instance was found"
!macroend

; taken from http://stackoverflow.com/questions/719631/how-do-i-require-user-to-uninstall-previous-version-with-nsis
; The "" makes the section hidden.
Section -SecUninstallPrevious
    Call UninstallPrevious
SectionEnd

Function UninstallPrevious

    ; Check for uninstaller.
    ReadRegStr $R0 ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString"
    ${If} $R0 == ""
        Goto Done
    ${EndIf}
	
	!insertmacro IsRunning
	
    DetailPrint "Removing previous installation."
	
    ; Run the uninstaller
    ExecWait '"$R0" _?=$INSTDIR'

    Done:

FunctionEnd

Section "Misura" SEC01
  SectionIn RO
  SetOutPath "$INSTDIR"
  SetOverwrite try
  File "${PYINST_DIR}\*.exe"
  File "${PYINST_DIR}\*.dll"
  File "${PYINST_DIR}\*.pyd"
  File "${PYINST_DIR}\*.manifest"

  CreateDirectory "$SMPROGRAMS\Misura"
  CreateShortCut "$SMPROGRAMS\Misura\Misura Browser.lnk" "$INSTDIR\${TASK_NAME}" --browser "$INSTDIR\art\browser.ico"
  CreateShortCut "$DESKTOP\Misura Browser.lnk" "$INSTDIR\${TASK_NAME}" --browser "$INSTDIR\art\browser.ico"

  SetOverwrite ifnewer

  File "${PYINST_DIR}\README"
  File "${PYINST_DIR}\COPYING"
  File "${PYINST_DIR}\VERSION"

  ;SetOutPath "$INSTDIR\eggs"
  ;File "${PYINST_DIR}\eggs\*.egg"

  SetOutPath "$INSTDIR\icons"
  File "${PYINST_DIR}\icons\*.png"
  File "${PYINST_DIR}\icons\*.ico"
  File "${PYINST_DIR}\icons\*.svg"
  
  SetOutPath "$INSTDIR\art"
  File /r "${PYINST_DIR}\art\*"
  
  SetOutPath "$INSTDIR\i18n"
  File /r "${PYINST_DIR}\i18n\*"

  SetOutPath "$INSTDIR\Include"
  File /r "${PYINST_DIR}\Include\*"
  
  SetOutPath "$INSTDIR\IPython"
  File /r "${PYINST_DIR}\IPython\*"

  SetOutPath "$INSTDIR\mpl-data"
  File /r "${PYINST_DIR}\mpl-data\*"
  
  SetOutPath "$INSTDIR\OpenGL\"
  File /r "${PYINST_DIR}\OpenGL\*"

  SetOutPath "$INSTDIR\pytz"
  File /r "${PYINST_DIR}\pytz\*"
  
  SetOutPath "$INSTDIR\thegram"
  File /r "${PYINST_DIR}\thegram\*"

  SetOutPath "$INSTDIR\ui"
  File "${PYINST_DIR}\ui\*.ui"

  SetOutPath "$INSTDIR\examples"
  File "${PYINST_DIR}\examples\*.vsz"
  File "${PYINST_DIR}\examples\*.py"
  File "${PYINST_DIR}\examples\*.dat"
  File "${PYINST_DIR}\examples\*.csv"
  SetOutPath "$INSTDIR"

  SetOutPath "$INSTDIR\qt4_plugins\"
  File /r "${PYINST_DIR}\qt4_plugins\"
  SetOutPath "$INSTDIR"

  WriteRegStr HKCR ".vsz" "" "MisuraGraphics.Document"
  WriteRegStr HKCR "MisuraGraphics.Document" "" "Misura Graphics Document"
  WriteRegStr HKCR "MisuraGraphics.Document\shell\open\command" "" '"$INSTDIR\${TASK_NAME}" --graphics "%1"'
  WriteRegStr HKCR "MisuraGraphics.Document\DefaultIcon" "" '"$INSTDIR\icons\graphics.ico"'
  
  WriteRegStr HKCR ".h5" "" "Misura.Document"
  WriteRegStr HKCR "Misura.Document" "" "Misura Document"
  WriteRegStr HKCR "Misura.Document\shell\open\command" "" '"$INSTDIR\${TASK_NAME}" --browser "%1"'
  WriteRegStr HKCR "Misura.Document\DefaultIcon" "" '"$INSTDIR\icons\browser.ico"'
  
  
  ; Installer options
	WriteINIStr "$INSTDIR\installer_options.ini" "main" "m3" 0
	WriteINIStr "$INSTDIR\installer_options.ini" "main" "flash" 0
	WriteINIStr "$INSTDIR\installer_options.ini" "main" "adv" 0
	WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "inst_flash" "0"
	WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "inst_m3" "0"
	WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "inst_adv" "0"
	
	; Grant full permissions on installation folder to avoid main-1 error
	AccessControl::GrantOnFile "$INSTDIR" "(BU)" "FullAccess"
SectionEnd

Section "Acquisition (ODP)" CMP_ACQ

  SectionIn 1
  SetOutPath "$INSTDIR"
  SetOverwrite try
  CreateShortCut "$SMPROGRAMS\Misura\Misura Acquisition.lnk" "$INSTDIR\${TASK_NAME}" --acquisition "$INSTDIR\art\misura.ico"
  CreateShortCut "$DESKTOP\Misura Acquisition.lnk" "$INSTDIR\${TASK_NAME}" --acquisition "$INSTDIR\art\misura.ico"
  ; Remember selection
  WriteINIStr "$INSTDIR\installer_options.ini" "main" "acq" 1
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "inst_acq" "1"

SectionEnd

Section "Advanced Graphics" CMP_GRAPH

  SectionIn 2
  SetOutPath "$INSTDIR"
  SetOverwrite try
  CreateShortCut "$SMPROGRAMS\Misura\Misura Graphics.lnk" "$INSTDIR\${TASK_NAME}" --graphics "$INSTDIR\art\graphics.ico"
  CreateShortCut "$DESKTOP\Misura Graphics.lnk" "$INSTDIR\${TASK_NAME}" --graphics "$INSTDIR\art\graphics.ico"
  ; Remember selection
  WriteINIStr "$INSTDIR\installer_options.ini" "main" "graph" 1
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "inst_graph" "1"

SectionEnd

Section "Flash diffusivity" CMP_FLASH

  SectionIn 3
  SetOutPath "$INSTDIR"
  WriteINIStr "$INSTDIR\installer_options.ini" "main" "flash" 1
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "inst_flash" "1"

SectionEnd

Section "Misura3 compatibility" CMP_M3

  SectionIn 4
  SetOutPath "$INSTDIR"
  WriteINIStr "$INSTDIR\installer_options.ini" "main" "m3" 1
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "inst_m3" "1"

SectionEnd

Section "Advanced Mode" CMP_ADV

  SectionIn 5
  SetOutPath "$INSTDIR"
  WriteINIStr "$INSTDIR\installer_options.ini" "main" "adv" 1
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "inst_adv" "1"

SectionEnd

Section -AdditionalIcons
  WriteIniStr "$INSTDIR\${PRODUCT_NAME}.url" "InternetShortcut" "URL" "${PRODUCT_WEB_SITE}"
  CreateShortCut "$SMPROGRAMS\Misura\Website.lnk" "$INSTDIR\${PRODUCT_NAME}.url"
  CreateShortCut "$SMPROGRAMS\Misura\Uninstall.lnk" "$INSTDIR\uninst.exe"
SectionEnd

Section -Post
  WriteUninstaller "$INSTDIR\uninst.exe"
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\${TASK_NAME}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\${TASK_NAME}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
SectionEnd


Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "$(^Name) was successfully removed from your computer."
FunctionEnd

Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to completely remove $(^Name) and all of its components?" IDYES +2
  Abort
FunctionEnd


Section -Uninstall
  Delete "$INSTDIR\${PRODUCT_NAME}.url"
  Delete "$INSTDIR\uninst.exe"

  Delete "$INSTDIR\COPYING"
  Delete "$INSTDIR\README"
  Delete "$INSTDIR\VERSION"

  Delete "$INSTDIR\*.pyd"
  Delete "$INSTDIR\*.dll"
  Delete "$INSTDIR\*.exe"
  Delete "$INSTDIR\*.manifest"
  Delete "$INSTDIR\*.zip"
  
  
  RMDir /r "${PYINST_DIR}\art"
  RMDir /r "${PYINST_DIR}\i18n"
  RMDir /r "${PYINST_DIR}\Include"
  RMDir /r "${PYINST_DIR}\IPython"
  RMDir /r "${PYINST_DIR}\mpl-data"
  RMDir /r "${PYINST_DIR}\OpenGL"
  RMDir /r "${PYINST_DIR}\pytz"
  RMDir /r "${PYINST_DIR}\thegram"
  RMDir /r "$INSTDIR\qt4_plugins"

  Delete "$INSTDIR\icons\*.png"
  Delete "$INSTDIR\icons\*.ico"
  Delete "$INSTDIR\icons\*.svg"
  Delete "$INSTDIR\ui\*.ui"
  Delete "$INSTDIR\examples\*.*"
  
  Delete "$SMPROGRAMS\Misura\Uninstall.lnk"
  Delete "$SMPROGRAMS\Misura\Website.lnk"
  Delete "$DESKTOP\Misura Browser.lnk"
  Delete "$SMPROGRAMS\Misura\Misura Browser.lnk"
  Delete "$DESKTOP\Misura Acquisition.lnk"
  Delete "$SMPROGRAMS\Misura\Misura Acquisition.lnk"
  Delete "$DESKTOP\Misura Graphics.lnk"
  Delete "$SMPROGRAMS\Misura\Misura Graphics.lnk"

  RMDir "$SMPROGRAMS\Misura"
  RMDir "$INSTDIR\eggs"
  RMDir "$INSTDIR\qt4_plugins\iconengines"
  RMDIR "$INSTDIR\qt4_plugins\imageformats"
  RMDir "$INSTDIR\qt4_plugins"
  RMDIR "$INSTDIR\icons"
  RMDir "$INSTDIR\ui"
  RMDIR "$INSTDIR\examples"
  RMDir "$INSTDIR"

  DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
  DeleteRegKey HKCR ".vsz"
  DeleteRegKey HKCR "MisuraGraphics.Document\shell\open\command"
  DeleteRegKey HKCR "MisuraGraphics.Document\DefaultIcon"
  DeleteRegKey HKCR "MisuraGraphics.Document"
  DeleteRegKey HKCR ".h5"
  DeleteRegKey HKCR "Misura.Document\shell\open\command"
  DeleteRegKey HKCR "Misura.Document\DefaultIcon"
  DeleteRegKey HKCR "Misura.Document"
  SetAutoClose true
SectionEnd

Function .OnInit
	!insertmacro UnselectSection ${CMP_ACQ}
	ReadRegStr $R0 ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "inst_acq"
	DetailPrint "cmp_acq $R0"
	${If} $R0 == "1"
	${OrIf} $R0 == ""
	   !insertmacro SelectSection ${CMP_ACQ}
	${EndIf}

	!insertmacro UnselectSection ${CMP_GRAPH}
	ReadRegStr $R0 ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "inst_graph"
	DetailPrint "cmp_graph $R0"
	${If} $R0 == "1"
	${OrIf} $R0 == ""
	   !insertmacro SelectSection ${CMP_GRAPH}
	${EndIf}

	!insertmacro UnselectSection ${CMP_M3}
	ReadRegStr $R0 ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "inst_m3"
	DetailPrint "cmp_m3 $R0"
	${If} $R0 == "1"
	   !insertmacro SelectSection ${CMP_M3}
	${EndIf}

	!insertmacro UnselectSection ${CMP_FLASH}
	ReadRegStr $R0 ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "inst_flash"
	DetailPrint "cmp_flash $R0"
	${If} $R0 == "1"
	   !insertmacro SelectSection ${CMP_FLASH}
	${EndIf}
	
	!insertmacro UnselectSection ${CMP_ADV}
	ReadRegStr $R0 ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "inst_adv"
	DetailPrint "cmp_adv $R0"
	${If} $R0 == "1"
	   !insertmacro SelectSection ${CMP_ADV}
	${EndIf}
FunctionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${CMP_M3} "Misura3 database import functionality"
  !insertmacro MUI_DESCRIPTION_TEXT ${CMP_FLASH} "Import FlashLine diffusivity test data and run advanced models and post-anlaysis"
  !insertmacro MUI_DESCRIPTION_TEXT ${CMP_ADV} "Expose all private options, experimental features and possibly misleading functionalities."
!insertmacro MUI_FUNCTION_DESCRIPTION_END