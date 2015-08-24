REM Compile and deploy script for ESS environment 

set codeBase=%userprofile%\Desktop\misura4
set deployDir=\\Ess-server\company\Installations\Misura4
set pyinst=pyinstaller
set python=C:\Python27\python.exe

set sourceDir=%codeBase%\misura
set clientDir=%sourceDir%\client
set canonDir=%sourceDir%\canon
set veuszDir=%codeBase%\veusz

set installerDir=%codeBase%\misura\client\installer
set specFile=%installerDir%\client_windows_pyinst.spec
set out=%installerDir%\dist

REM del /q /s "%deployDir%\misura4" 
set stamp=%DATE:/=-%_%TIME::=-%
mv "%deployDir%\misura4" "%deployDir%\build_%stamp%"
xcopy /E /Y /I "%out%\misura4" "%deployDir%\misura4"

