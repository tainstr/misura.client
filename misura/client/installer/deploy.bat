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

set stamp=%DATE:/=-%_%TIME::=-%
mv "%deployDir%\misura4" "%deployDir%\build_%stamp%"
xcopy /E /Y /I "%out%\misura4" "%deployDir%\misura4"

