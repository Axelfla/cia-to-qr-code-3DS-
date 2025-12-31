@echo off
title 3DS QR Generator - Lanceur
color 0B

REM Vérifier et installer les dépendances au premier lancement
if not exist ".installed" (
    echo ====================================
    echo  PREMIERE INSTALLATION
    echo ====================================
    echo.
    echo Installation des modules necessaires...
    echo Cela peut prendre 1-2 minutes.
    echo.
    
    python -m pip install --upgrade pip --quiet
    pip install qrcode pillow requests beautifulsoup4 --quiet
    
    if %errorlevel% equ 0 (
        echo. > .installed
        echo.
        echo [OK] Installation terminee !
        echo.
    ) else (
        echo.
        echo ERREUR lors de l'installation !
        echo Verifiez que Python est installe.
        pause
        exit /b 1
    )
)

REM Lancer l'application
cls
echo ====================================
echo  3DS QR GENERATOR
echo ====================================
echo.
echo Lancement de l'application...
echo.

python 3ds_qr_generator.py

if %errorlevel% neq 0 (
    echo.
    echo ERREUR lors du lancement !
    echo.
    pause
)
