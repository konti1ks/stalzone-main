@echo off
chcp 65001 > nul
title Stalzone Main — сборка .exe

echo ==========================================
echo   Stalzone Main - СБОРКА EXE
echo ==========================================
echo.

REM проверка venv
if not exist ".venv\Scripts\python.exe" (
    echo [ОШИБКА] Виртуальное окружение .venv не найдено
    pause
    exit /b 1
)

echo [1/5] Установка PyInstaller...
.venv\Scripts\python.exe -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo [ОШИБКА] PyInstaller не установился
    pause
    exit /b 1
)

echo.
echo [2/5] Генерация app.ico...
.venv\Scripts\python.exe make_icon.py
if errorlevel 1 (
    echo [ОШИБКА] Иконка не создалась
    pause
    exit /b 1
)

echo.
echo [3/5] Очистка старых сборок...
if exist build rmdir /S /Q build
if exist dist rmdir /S /Q dist

echo.
echo [4/5] Сборка .exe (1-3 минуты, не закрывай)...
.venv\Scripts\python.exe -m PyInstaller StalzoneMain.spec --noconfirm --clean

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Сборка упала. Смотри сообщения выше.
    pause
    exit /b 1
)

echo.
echo [5/5] Копирование базы и рецептов...
if exist "stalzone-database" (
    xcopy /E /I /Y /Q "stalzone-database" "dist\StalzoneMain\stalzone-database" > nul
    echo    stalzone-database скопирована
) else (
    echo    [ВНИМАНИЕ] Папка stalzone-database не найдена в корне!
)

if exist "recipes.json" (
    copy /Y "recipes.json" "dist\StalzoneMain\recipes.json" > nul
    echo    recipes.json скопирован
)

echo.
echo ==========================================
echo   ГОТОВО
echo ==========================================
echo.
echo Запускаемый файл:
echo    dist\StalzoneMain\StalzoneMain.exe
echo.
echo Всю папку dist\StalzoneMain можно архивировать
echo и передавать другу.
echo.
pause