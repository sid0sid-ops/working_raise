# 06. Windows User Onboarding & Setup Guide

This guide provides a step-by-step walkthrough for running the RAISE backend on **Windows 10 and Windows 11** laptops without friction, terminal errors, or environment conflicts.

---

## 1. Choose Your Windows Setup Method

| Method | When to Use | Setup Time | What You Need |
| :--- | :--- | :--- | :--- |
| **Method A: Native Windows (Recommended)** | Standard Windows laptops (8GB–16GB RAM), fast development | **< 5 minutes** | Python 3.11+ and Git only (**Zero Docker, Zero WSL2**) |
| **Method B: WSL2 (Ubuntu on Windows)** | Developers wanting the full Linux environment, local Docker, or local Rust compilation | **15–20 minutes** | Windows 10/11 with WSL2 & Docker Desktop enabled |

---

## 2. Method A: Native Windows Setup (5-Minute Quickstart)

### Step 1: Install Python 3.11+
1. Download Python 3.11 or 3.12 from [python.org](https://www.python.org/downloads/windows/).
2. ⚠️ **CRITICAL STEP**: On the first installer screen, you **MUST check the box**:
   > **`[X] Add python.exe to PATH`**  
   *(If you skip this, Windows will show "python is not recognized as an internal or external command".)*
3. Click **Install Now**.

### Step 2: Install Git for Windows
1. Download and run the installer from [git-scm.com](https://git-scm.com/download/win).
2. Use all default settings during installation.

### Step 3: Clone the Repository
Open **Command Prompt (`cmd`)** or **PowerShell** and run:
```powershell
git clone -b backend https://github.com/sid0sid-ops/working_raise.git
cd working_raise
```

### Step 4: Run the Windows 1-Click Setup Script
Create or run [`setup.bat`](file:///Users/sid/Documents/project/Frontend/scratch/working_raise/setup.bat) directly in the folder:

```cmd
setup.bat
```

Or run via Python:
```powershell
python setup.py
```
* Select **Option 1 (Cloud-Native Zero-GPU)** when prompted.
* Enter your free **Groq** and **Neo4j AuraDB** keys (or press Enter to configure later in `.env`).

### Step 5: Start the Backend Server
```powershell
# In PowerShell:
.\.venv\Scripts\Activate.ps1
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload

# Or in Command Prompt (CMD):
.\.venv\Scripts\activate.bat
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```
Open your browser to: **`http://127.0.0.1:8000/docs`** to see the interactive Swagger API documentation.

---

## 3. Dedicated Windows Batch Scripts (`setup.bat` and `run.bat`)

To make it truly 1-click on Windows, provide these two batch scripts in the project root:

### Script 1: `setup.bat` (Place in project root)
```batch
@echo off
TITLE RAISE Backend - Windows 1-Click Setup
COLOR 0A

echo ======================================================
echo       RAISE RESEARCH WORKSTATION - WINDOWS SETUP
echo ======================================================
echo.

:: Check Python installation
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in your PATH!
    echo Please install Python 3.11+ from https://www.python.org/downloads/
    echo Make sure to check "Add python.exe to PATH" during installation.
    pause
    exit /b 1
)

echo [1/4] Checking Python version...
python --version

echo.
echo [2/4] Creating virtual environment (.venv)...
if not exist ".venv" (
    python -m venv .venv
    echo Virtual environment created.
) else (
    echo Virtual environment already exists.
)

echo.
echo [3/4] Installing dependencies...
call .\.venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel

:: Install sanitized requirements
python -m pip install -r requirements.txt

echo.
echo [4/4] Setting up .env configuration...
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env
        echo Created .env from .env.example template.
    ) else (
        echo ENVIRONMENT=development > .env
        echo LOG_LEVEL=INFO >> .env
        echo USE_RUST_CORE=false >> .env
        echo Created default .env file.
    )
) else (
    echo .env already exists. Preserving current configuration.
)

echo.
echo ======================================================
echo           SETUP COMPLETE! YOU ARE READY TO GO.
echo ======================================================
echo To start the server anytime, simply double-click "run.bat"
echo.
pause
```

### Script 2: `run.bat` (Double-click to start anytime)
```batch
@echo off
TITLE RAISE Backend Server
COLOR 0B

echo Starting RAISE Backend API Gateway on http://127.0.0.1:8000...
echo Swagger Documentation: http://127.0.0.1:8000/docs
echo.

call .\.venv\Scripts\activate.bat
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
pause
```

---

## 4. Method B: WSL2 Setup (For Local Docker & Full Sovereign Stack)

If a Windows user wants to run local Docker containers (Neo4j, Redis, Qdrant) or compile Rust natively:

1. **Install WSL2**:
   Open PowerShell as Administrator and run:
   ```powershell
   wsl --install -d Ubuntu
   ```
   Restart the PC when prompted.
2. **Install Docker Desktop for Windows**:
   - Download from [docker.com](https://www.docker.com/products/docker-desktop/).
   - During setup, check **"Use the WSL 2 based engine"**.
   - In Docker Desktop Settings -> **Resources -> WSL Integration**, enable integration with Ubuntu.
3. **Open Ubuntu Terminal**:
   Inside Ubuntu, follow the standard Linux instructions:
   ```bash
   git clone -b backend https://github.com/sid0sid-ops/working_raise.git
   cd working_raise
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn src.main:app --reload
   ```

---

## 5. Common Windows Pitfalls & Instant Fixes

### Error 1: "activate.ps1 cannot be loaded because running scripts is disabled on this system"
* **Cause**: Windows PowerShell security policy blocks local script execution by default.
* **Fix**: In your PowerShell window, run this command once before activating:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  .\.venv\Scripts\Activate.ps1
  ```

### Error 2: "error: Microsoft Visual C++ 14.0 or greater is required"
* **Cause**: A package is trying to compile C/C++ or Rust code locally because pre-compiled Windows wheels were missing.
* **Fix**: 
  - Switch to **Profile 1 (Cloud-Native)**. In `requirements.txt`, ensure you are using pre-built wheels (`pip install --only-binary :all:`).
  - Do NOT compile the native Rust engine on Windows unless you have installed [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with "Desktop development with C++".

### Error 3: Filename too long / `MAX_PATH` error during Git clone
* **Cause**: Windows has a historical 260-character path limit.
* **Fix**: Run in PowerShell as Administrator:
  ```powershell
  git config --system core.longpaths true
  ```

### Error 4: Line Ending Warnings (`CRLF` vs `LF`)
* **Cause**: Windows uses Carriage Return + Line Feed (`\r\n`) while Linux/Mac uses Line Feed (`\n`).
* **Fix**: Configure Git to handle conversions smoothly:
  ```powershell
  git config --global core.autocrlf true
  ```
