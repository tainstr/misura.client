REM Compile and deploy script for ESS environment 

set codeBase=%userprofile%\Desktop\misura4
set deployDir=\\192.168.0.118\misura\Installations
set pyinst=pyinstaller
set python=C:\Python27\python.exe

set clientDir=%codeBase%\misura.client\misura\client
set canonDir=%codeBase%\misura.canon\misura\canon
set veuszDir=%codeBase%\veusz

set installerDir=%clientDir%\\installer
set specFile=%installerDir%\client_windows_pyinst.spec
set out=%installerDir%\dist

set day=%date:~0,2%
set month=%date:~3,2%
set year=%date:~6,4%
set stamp=%year%%month%%day%_%TIME::=-%
move "%deployDir%\misura4" "%deployDir%\build_%stamp%"
xcopy /E /Y /I "%out%\misura4" "%deployDir%\misura4"
