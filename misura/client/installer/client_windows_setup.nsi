; Change this to specify location to build installer from
; misura.client\misura\client\installer\dist\misura4
!define PYINST_DIR ".\dist\misura4"
!define VEUSZ_SRC_DIR ".\..\..\..\..\"

; HM NIS Edit Wizard helper defines
!define PRODUCT_NAME "Misura"
!define /date DATE "%Y%m%d"
!define PRODUCT_VERSION "4.3-${DATE}"
!define PRODUCT_PUBLISHER "TA Instruments / Waters LLC"
!define PRODUCT_WEB_SITE "http://misura.readthedocs.io"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\misura.exe"
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
!define MUI_FINISHPAGE_RUN "$INSTDIR\misura.exe"
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
  CreateShortCut "$SMPROGRAMS\Misura\Misura Browser.lnk" "$INSTDIR\misura.exe" --browser "$INSTDIR\art\browser.ico"
  CreateShortCut "$DESKTOP\Misura Browser.lnk" "$INSTDIR\misura.exe" --browser "$INSTDIR\art\browser.ico"
  CreateShortCut "$SMPROGRAMS\Misura\Misura Acquisition.lnk" "$INSTDIR\misura.exe" --acquisition "$INSTDIR\art\misura.ico"
  CreateShortCut "$DESKTOP\Misura Acquisition.lnk" "$INSTDIR\misura.exe" --acquisition "$INSTDIR\art\misura.ico"
  CreateShortCut "$SMPROGRAMS\Misura\Misura Graphics.lnk" "$INSTDIR\misura.exe" --graphics "$INSTDIR\art\graphics.ico"
  CreateShortCut "$DESKTOP\Misura Graphics.lnk" "$INSTDIR\misura.exe" --graphics "$INSTDIR\art\graphics.ico"
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
  WriteRegStr HKCR "MisuraGraphics.Document\shell\open\command" "" '"$INSTDIR\misura.exe" --graphics "%1"'
  WriteRegStr HKCR "MisuraGraphics.Document\DefaultIcon" "" '"$INSTDIR\icons\graphics.ico"'
  
  WriteRegStr HKCR ".h5" "" "Misura.Document"
  WriteRegStr HKCR "Misura.Document" "" "Misura Document"
  WriteRegStr HKCR "Misura.Document\shell\open\command" "" '"$INSTDIR\misura.exe" --browser "%1"'
  WriteRegStr HKCR "Misura.Document\DefaultIcon" "" '"$INSTDIR\icons\browser.ico"'
  
  
  ; Installer options
	WriteINIStr "$INSTDIR\installer_options.ini" "main" "m3" 0
	WriteINIStr "$INSTDIR\installer_options.ini" "main" "flash" 0
	WriteINIStr "$INSTDIR\installer_options.ini" "main" "adv" 0
	WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "inst_flash" "0"
	WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "inst_m3" "0"
	WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "inst_adv" "0"
SectionEnd



Section "Flash diffusivity" CMP_FLASH

  SectionIn 1
  SetOutPath "$INSTDIR"
  WriteINIStr "$INSTDIR\installer_options.ini" "main" "flash" 1
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "inst_flash" "1"
  

SectionEnd

Section "Misura3 compatibility" CMP_M3

  SectionIn 2
  SetOutPath "$INSTDIR"
  WriteINIStr "$INSTDIR\installer_options.ini" "main" "m3" 1
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "inst_m3" "1"

SectionEnd

Section "Advanced mode" CMP_ADV

  SectionIn 3
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
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\misura.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\misura.exe"
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

