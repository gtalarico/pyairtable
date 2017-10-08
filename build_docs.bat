cd "%CD%"\docs
echo "%CD%"
call make.bat html
cd ..

START chrome %CD%\docs\build\html\index.html