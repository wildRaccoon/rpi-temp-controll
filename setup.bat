@echo off
REM Скрипт для налаштування проекту на Windows

echo 🔧 Налаштування проекту контролю температури...

REM Перевірка наявності Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не знайдено. Будь ласка, встановіть Python 3.8 або новіший.
    pause
    exit /b 1
)

echo ✅ Python знайдено
python --version

REM Створення віртуального середовища
if not exist "venv" (
    echo 📦 Створення віртуального середовища...
    python -m venv venv
    echo ✅ Віртуальне середовище створено
) else (
    echo ✅ Віртуальне середовище вже існує
)

REM Активація віртуального середовища
echo 🔌 Активація віртуального середовища...
call venv\Scripts\activate.bat

REM Оновлення pip
echo ⬆️  Оновлення pip...
python -m pip install --upgrade pip

REM Встановлення залежностей
echo 📥 Встановлення залежностей...
pip install -r requirements.txt

REM Створення необхідних директорій
echo 📁 Створення директорій...
if not exist "logs" mkdir logs
if not exist "data" mkdir data
if not exist "web\static" mkdir web\static
if not exist "web\templates" mkdir web\templates

REM Створення .gitkeep файлів
if not exist "logs\.gitkeep" type nul > logs\.gitkeep
if not exist "data\.gitkeep" type nul > data\.gitkeep

REM Копіювання прикладу конфігурації, якщо config.yaml не існує
if not exist "config.yaml" (
    if exist "config.example.yaml" (
        echo 📋 Створення config.yaml з прикладу...
        copy config.example.yaml config.yaml
        echo ⚠️  Будь ласка, відредагуйте config.yaml зі своїми налаштуваннями!
    )
) else (
    echo ✅ config.yaml вже існує
)

echo.
echo ✅ Налаштування завершено!
echo.
echo 📝 Наступні кроки:
echo    1. Відредагуйте config.yaml зі своїми налаштуваннями
echo    2. Для тестування запустіть: python main.py --test-mode
echo    3. Для production запустіть: python main.py
echo.
echo 💡 Для активації venv в майбутньому використовуйте:
echo    venv\Scripts\activate.bat
echo.

pause

