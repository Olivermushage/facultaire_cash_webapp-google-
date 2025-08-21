@echo off
echo Nettoyage des anciennes builds...
rmdir /s /q build
rmdir /s /q dist
del /q /f app.spec

echo Construction de l’exécutable...
pyinstaller --noconfirm --clean --onefile ^
--add-data "templates;templates" ^
--add-data "static;static" ^
--add-data "data;data" ^
app.py

echo Build terminé.
pause
