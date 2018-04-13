; Change this to specify location to build installer from
!define VEUSZ_SRC_DIR "c:\users\misura\desktop\misura4"
!define PYINST_DIR "${VEUSZ_SRC_DIR}\misura.client\misura\client\installer\dist\misura4"

; HM NIS Edit Wizard helper defines
!define PRODUCT_NAME "Misura"
;!define PRODUCT_VERSION "4.2"
!define PRODUCT_PUBLISHER "TA Instruments/Waters LLC"
!define PRODUCT_WEB_SITE "http://misura.readthedocs.io"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\browser.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

SetCompressor /solid lzma

; MUI 1.67 compatible ------
!include "MUI.nsh"

; MUI Settings
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; Welcome page
!insertmacro MUI_PAGE_WELCOME
; License page
!insertmacro MUI_PAGE_LICENSE "${PYINST_DIR}\COPYING"
; Directory page
!insertmacro MUI_PAGE_DIRECTORY
; Instfiles page
!insertmacro MUI_PAGE_INSTFILES
; Finish page
!define MUI_FINISHPAGE_RUN "$INSTDIR\browser.exe"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\README"
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_INSTFILES

; Language files
!insertmacro MUI_LANGUAGE "English"

; MUI end ------

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "misura-${PRODUCT_VERSION}-windows-setup.exe"
InstallDir "$PROGRAMFILES\Misura"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
ShowInstDetails show
ShowUnInstDetails show

; taken from http://stackoverflow.com/questions/719631/how-do-i-require-user-to-uninstall-previous-version-with-nsis
; The "" makes the section hidden.
Section "" SecUninstallPrevious
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

Section "MainSection" SEC01
  SetOutPath "$INSTDIR"
  SetOverwrite try
  File "${PYINST_DIR}\*.exe"
  File "${PYINST_DIR}\*.dll"
  File "${PYINST_DIR}\*.pyd"
  File "${PYINST_DIR}\*.manifest"
  File "${VEUSZ_SRC_DIR}\veusz\veusz\embed.py"
  File "${VEUSZ_SRC_DIR}\veusz\veusz\__init__.py"

  CreateDirectory "$SMPROGRAMS\Misura"
  CreateShortCut "$SMPROGRAMS\Misura\Browser.lnk" "$INSTDIR\browser.exe"
  CreateShortCut "$DESKTOP\Browser.lnk" "$INSTDIR\browser.exe"
  SetOverwrite ifnewer

  File "${PYINST_DIR}\README"
  File "${PYINST_DIR}\COPYING"
  File "${PYINST_DIR}\VERSION"

  SetOutPath "$INSTDIR\eggs"
  File "${PYINST_DIR}\eggs\*.egg"

  SetOutPath "$INSTDIR\icons"
  File "${PYINST_DIR}\icons\*.png"
  File "${PYINST_DIR}\icons\*.ico"
  File "${PYINST_DIR}\icons\*.svg"
  
  SetOutPath "$INSTDIR\art"
  File "${PYINST_DIR}\art\*.png"
  File "${PYINST_DIR}\art\*.ico"
  File "${PYINST_DIR}\art\*.svg"

  SetOutPath "$INSTDIR\ui"
  File "${PYINST_DIR}\ui\*.ui"

  SetOutPath "$INSTDIR\examples"
  File "${PYINST_DIR}\examples\*.vsz"
  File "${PYINST_DIR}\examples\*.py"
  File "${PYINST_DIR}\examples\*.dat"
  File "${PYINST_DIR}\examples\*.csv"
  SetOutPath "$INSTDIR"

  SetOutPath "$INSTDIR\qt4_plugins\iconengines"
  File "${PYINST_DIR}\qt4_plugins\iconengines\*.dll"
  SetOutPath "$INSTDIR"

  SetOutPath "$INSTDIR\qt4_plugins\imageformats"
  File "${PYINST_DIR}\qt4_plugins\imageformats\*.dll"
  SetOutPath "$INSTDIR"

  WriteRegStr HKCR ".vsz" "" "MisuraGraphics.Document"
  WriteRegStr HKCR "MisuraGraphics.Document" "" "Misura Graphics Document"
  WriteRegStr HKCR "MisuraGraphics.Document\shell\open\command" "" '"$INSTDIR\graphics.exe" "%1"'
  WriteRegStr HKCR "MisuraGraphics.Document\DefaultIcon" "" '"$INSTDIR\icons\graphics.ico"'
  
  WriteRegStr HKCR ".h5" "" "Misura.Document"
  WriteRegStr HKCR "Misura.Document" "" "Misura Document"
  WriteRegStr HKCR "Misura.Document\shell\open\command" "" '"$INSTDIR\browser.exe" "%1"'
  WriteRegStr HKCR "Misura.Document\DefaultIcon" "" '"$INSTDIR\icons\browser.ico"'
SectionEnd

Section -AdditionalIcons
  WriteIniStr "$INSTDIR\${PRODUCT_NAME}.url" "InternetShortcut" "URL" "${PRODUCT_WEB_SITE}"
  CreateShortCut "$SMPROGRAMS\Veusz\Website.lnk" "$INSTDIR\${PRODUCT_NAME}.url"
  CreateShortCut "$SMPROGRAMS\Veusz\Uninstall.lnk" "$INSTDIR\uninst.exe"
SectionEnd

Section -Post
  WriteUninstaller "$INSTDIR\uninst.exe"
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\browser.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\browser.exe"
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

Section Uninstall
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
  Delete "$INSTDIR\embed.py"
  Delete "$INSTDIR\__init__.py"

  Delete "$INSTDIR\eggs\*.egg"

  Delete "$INSTDIR\qt4_plugins\iconengines\*.dll"
  Delete "$INSTDIR\qt4_plugins\imageformats\*.dll"

  Delete "$INSTDIR\icons\*.png"
  Delete "$INSTDIR\icons\*.ico"
  Delete "$INSTDIR\icons\*.svg"
  Delete "$INSTDIR\ui\*.ui"
  Delete "$INSTDIR\examples\*.*"
  
  Delete "$INSTDIR\art\*.png"
  Delete "$INSTDIR\art\*.ico"
  Delete "$INSTDIR\art\*.svg"
  Delete "$INSTDIR\thegram\*"
  
  Delete "$SMPROGRAMS\Misura\Uninstall.lnk"
  Delete "$SMPROGRAMS\Misura\Website.lnk"
  Delete "$DESKTOP\Browser.lnk"
  Delete "$SMPROGRAMS\Misura\Browser.lnk"

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
