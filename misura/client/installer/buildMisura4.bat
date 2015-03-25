REM Compile and deploy script for ESS environment 

set codeBase=%userprofile%\Desktop\misura4
set deployDir=\\Ess-server\company\Installations\Misura4
set pyinst=pyinstaller
set python=C:\Python27\python.exe


set sourceDir=%codeBase%\misura4
set clientDir=%sourceDir%\client
set canonDir=%sourceDir%\canon
set veuszDir=%codeBase%\veusz

set installerDir=%codeBase%\misura4\client\installer
set specFile=%installerDir%\client_windows_pyinst.spec
set out=%installerDir%\dist

C:
cd %installerDir%
%pyinst% -y %specFile%

xcopy %out%\configuration\* %out%\misura4
xcopy %out%\archive\* %out%\misura4
xcopy %out%\acquisition\* %out%\misura4

REM Deploy step
rem del /q "%deployDir%\misura4" 
rem xcopy /E /Y /I "%out%\misura4" "%deployDir%\misura4"
