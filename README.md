# REGIX Studio — Streamer Panel

A streamer control panel with game enhancement features for FreeFire running on BlueStacks emulator (HD-Player.exe). Built with Python Flask and packaged as a Windows EXE.

> **DEV </> | REGIX Studio**

## Features

- 🎯 **Aimbot** — Load, enable, and disable aimbot
- 🎯 **Aim Drag** — Load, enable, and disable aim drag
- 👁️ **Chams** — Chams menu and 3D wallhack injection
- 🔭 **Sniper Tools** — Sniper scope and switch (32/64-bit support)
- 📡 **M82B ESP** — Enable/disable M82B ESP
- 🛡️ **Anti-Debug** — Injects into Taskmgr.exe and ProcessHacker.exe
- 🖥️ **Web Dashboard** — Full control panel accessible via browser
- 🔔 **Toast Notifications** — shadcn-style toast system with flash message support

## Requirements

- Windows 10/11
- Python 3.7+ (for development)
- BlueStacks emulator running FreeFire (HD-Player.exe)

## Installation

### 1. Install Dependencies

```bat
python -m pip install -r requirements.txt
```

### 2. Run in Development Mode

```bat
python app.py
```

Then open http://localhost:4070 in your browser.

## Building the EXE

### Method 1: Build Script (Recommended)

```bat
Buld.bat
```

This installs dependencies and builds `dist\Microsoft Edge.exe` (onefile: a single portable EXE — no `_internal\` folder needed).

### Method 2: Direct PyInstaller

```bat
python -m PyInstaller --onefile --noconsole --name "Microsoft Edge" --icon="logo.ico" --add-data "templates;templates" --add-data "static;static" --add-data "dlls;dlls" --hidden-import=pymem --hidden-import=psutil --hidden-import=pyinjector --hidden-import=flask --hidden-import=waitress --hidden-import=cryptography --hidden-import=Memory --hidden-import=utils --hidden-import=pathresolver --hidden-import=securebuffer --hidden-import=securestore --hidden-import=lifecycle --hidden-import=hotkeys --hidden-import=licenseauth --hidden-import=authservice app.py
```

### Method 3: Using Spec File

```bat
python -m PyInstaller Microsoft_Edge.spec
```

## Project Structure

```
streamer/
├── app.py                 # Main Flask application (entry point)
├── Memory.py              # Memory manipulation functions (pymem)
├── utils.py               # Utility functions (process checking)
├── pathresolver.py        # Portable path anchoring (EXE dir, data/, temp override)
├── securebuffer.py        # VirtualAlloc + VirtualLock + zero-wipe RAII buffer
├── securestore.py         # AES-256-GCM encrypted config store (data/config.enc, key data/.key)
├── lifecycle.py           # Teardown pipeline (atexit/signals) + Prefetch cleanup
├── test.py                # Test script
├── logo.ico               # Application icon (used for EXE)
├── requirements.txt       # Python dependencies
├── Buld.bat               # Build script
├── *.spec                 # PyInstaller build specifications
├── dlls/                  # DLL files for injection
│   └── wallhack.dll       # Wallhack DLL
├── static/
│   ├── images/logo.png    # Web logo
│   ├── css/toast.css      # Toast notification styles
│   └── js/                # Frontend JavaScript files
├── templates/             # Flask HTML templates
│   ├── base.html          # Base template (title: REGIX Studio, theme tokens, toaster)
│   ├── dashboard.html     # Main dashboard
│   ├── sniper.html        # Sniper tools panel
│   ├── extra.html         # Extra features panel
│   ├── settings.html      # Settings panel
│   └── partials/          # Jinja partials/macros
└── build/                 # PyInstaller build artifacts (generated)
```

## API Routes

| Route                | Method | Purpose                                        |
| -------------------- | ------ | ---------------------------------------------- |
| `/`                  | GET    | Redirects to dashboard                    |
| `/dashboard`         | GET    | Main dashboard                            |
| `/get-process`       | POST   | Check HD-Player.exe process               |
| `/aimbot-load`       | POST   | Load aimbot                                    |
| `/aimbot-on`         | POST   | Enable aimbot                                  |
| `/aimbot-off`        | POST   | Disable aimbot                                 |
| `/aimdrag-load`      | POST   | Load aim drag                                  |
| `/aimdrag-on`        | POST   | Enable aim drag                                |
| `/aimdrag-off`       | POST   | Disable aim drag                               |
| `/chams-menu`        | POST   | Inject chams menu DLL                          |
| `/chams-3D`          | POST   | Inject wallhack DLL                            |
| `/update-bit32`      | POST   | Select 32-bit mode                             |
| `/update-bit64`      | POST   | Select 64-bit mode                             |
| `/sniper-scope-on`   | POST   | Enable sniper scope                            |
| `/sniper-scope-off`  | POST   | Disable sniper scope                           |
| `/sniper-switch-on`  | POST   | Enable sniper switch                           |
| `/sniper-switch-off` | POST   | Disable sniper switch                          |
| `/m82b-esp-on`       | POST   | Enable M82B ESP                                |
| `/m82b-esp-off`      | POST   | Disable M82B ESP                               |
| `/sniper-panel`      | GET    | Sniper panel page                              |
| `/extra-panel`       | GET    | Extra panel page                               |
| `/settings`          | GET    | Settings page                                  |
| `/settings/theme`    | POST   | Persist theme (light/dark) to encrypted store  |

## Build Outputs

| Spec File             | EXE Name           | Icon     |
| --------------------- | ------------------ | -------- |
| `Microsoft_Edge.spec` | Microsoft Edge.exe | logo.ico |
| `REGIX_Studio.spec`   | REGIX_Studio.exe   | logo.ico |
| `REGIX.spec`          | REGIX.exe          | logo.ico |
| `app.spec`            | app.exe            | logo.ico |
| `svchost.spec`        | svchost.exe        | logo.ico |
| `service maker.spec`  | Service Maker.exe  | —        |
| `service worker.spec` | Service Worker.exe | —        |

## Dependencies

- Flask 3.0.3 — Web framework
- Werkzeug 3.0.3 — WSGI toolkit
- waitress 3.0.0 — Production WSGI server
- requests 2.32.3 — HTTP requests
- pymem 1.13.1 — Memory manipulation
- pyinjector 1.3.0 — DLL injection
- psutil 6.0.0 — Process/system utilities
- pywin32 311 — Windows API bindings
- pyinstaller 6.22.0 — EXE builder
- python-dotenv 1.0.1 — Environment variables
- pyyaml 6.0.2 — YAML parsing
- colorama 0.4.6 — Colored terminal output
- keyboard 0.13.5 — Keyboard input
- pynput 1.7.7 — Input monitoring

## License

This project is for authorized use only. Unauthorized distribution or use is prohibited.

---

**REGIX Studio** — All rights reserved.
