REM Compile and deploy script for ESS environment 

set codeBase=%userprofile%\Desktop\misura4
set deployDir=\\Ess-server\company\Installations\Misura4
set pyinst=pyinstaller
set python=C:\Python27\python.exe

set clientDir=%codeBase%\misura.client\misura\client
set canonDir=%codeBase%\misura.canon\misura\canon
set veuszDir=%codeBase%\veusz

set installerDir=%clientDir%\\installer
set specFile=%installerDir%\client_windows_pyinst.spec
set out=%installerDir%\dist

REM Recreate dist output directory
del /q /s "%out%"
mkdir "%out%"

C:
cd %installerDir%
%pyinst% -y %specFile%

REM Consolidate local build
xcopy %out%\configuration\* %out%\misura4
xcopy %out%\browser\* %out%\misura4
xcopy %out%\acquisition\* %out%\misura4

REM hack to make svg icons work also on Windows Vista
copy C:\Python27\Lib\site-packages\PyQt4\plugins\imageformats\qsvg4.dll %out%\misura4\qt4_plugins\imageformats
