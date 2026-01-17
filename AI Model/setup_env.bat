@echo off
echo 🌲 Setting up VerdeScan AI Environment...

if exist venv (
    echo Virtual environment already exists.
) else (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

echo.
echo ✅ Environment setup complete!
echo.
echo To activate this environment in the future, run:
echo    venv\Scripts\activate
echo.
pause
