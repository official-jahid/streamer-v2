# AGENTS.md — Project Guide for AI Agents

This file provides essential context for AI agents (like Cline) working on this project. Read this before making any changes.

## Project Overview

**Project:** REGIX Studio — Streamer Panel
**Type:** Python Flask web application packaged as a Windows EXE
**Purpose:** A streamer control panel with game enhancement features (aimbot, chams, ESP, sniper tools) for FreeFire running on BlueStacks emulator (HD-Player.exe)

## Branding

| REGIX                     |
| ------------------------- |
| REGIX                     |
| REGIX Studio              |
| Microsoft Edge (EXE name) |
| REGIX_Studio              |
| REGIX                     |

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
├── Buld.bat               # Build script (note: intentionally misspelled "Buld")
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

## Key Files & Their Roles

### app.py (Main Application)

- Flask app with routes for aimbot, chams, ESP, sniper tools
- No authentication: `/` redirects straight to the dashboard
- Injects DLLs into HD-Player.exe (BlueStacks) using pyinjector
- Has anti-debug features (injects into Taskmgr.exe and ProcessHacker.exe)
- Runs on port 4070
- Sets AppUserModelID "REGIX.Studio" for taskbar icon

### Key Routes

| Route                | Method | Purpose                                       |
| -------------------- | ------ | --------------------------------------------- |
| `/`                  | GET    | Redirects to dashboard                        |
| `/dashboard`         | GET    | Main dashboard                                |
| `/get-process`       | POST   | Check HD-Player.exe process                   |
| `/aimbot-load`       | POST   | Load aimbot                                   |
| `/aimbot-on`         | POST   | Enable aimbot                                 |
| `/aimbot-off`        | POST   | Disable aimbot                                |
| `/aimdrag-load`      | POST   | Load aim drag                                 |
| `/aimdrag-on`        | POST   | Enable aim drag                               |
| `/aimdrag-off`       | POST   | Disable aim drag                              |
| `/chams-menu`        | POST   | Inject chams menu DLL                         |
| `/chams-3D`          | POST   | Inject wallhack DLL                           |
| `/update-bit32`      | POST   | Select 32-bit mode                            |
| `/update-bit64`      | POST   | Select 64-bit mode                            |
| `/sniper-scope-on`   | POST   | Enable sniper scope                           |
| `/sniper-scope-off`  | POST   | Disable sniper scope                          |
| `/sniper-switch-on`  | POST   | Enable sniper switch                          |
| `/sniper-switch-off` | POST   | Disable sniper switch                         |
| `/m82b-esp-on`       | POST   | Enable M82B ESP                               |
| `/m82b-esp-off`      | POST   | Disable M82B ESP                              |
| `/sniper-panel`      | GET    | Sniper panel page                             |
| `/extra-panel`       | GET    | Extra panel page                              |
| `/settings`          | GET    | Settings page                                 |
| `/settings/theme`    | POST   | Persist theme (light/dark) to encrypted store |

### Spec Files (PyInstaller)

| Spec File             | EXE Name           | Icon     |
| --------------------- | ------------------ | -------- |
| `Microsoft_Edge.spec` | Microsoft Edge.exe | logo.ico |
| `REGIX_Studio.spec`   | REGIX_Studio.exe   | logo.ico |
| `REGIX.spec`          | REGIX.exe          | logo.ico |
| `app.spec`            | app.exe            | logo.ico |
| `svchost.spec`        | svchost.exe        | logo.ico |
| `service maker.spec`  | Service Maker.exe  | —        |
| `service worker.spec` | Service Worker.exe | —        |

## Build Commands

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

### Install Dependencies

```bat
python -m pip install -r requirements.txt
```

## Important Notes for AI Agents

1. **Never overwrite app.py entirely** — it's 424 lines with critical game memory manipulation code. Use targeted `replace_in_file` edits instead.
2. **The build script is named `Buld.bat`** (intentional misspelling) — don't "fix" it.
3. **DLL injection targets:** HD-Player.exe (game), Taskmgr.exe (anti-debug), ProcessHacker.exe (anti-debug)
4. **The app hides from taskbar** using `hide_from_taskbar()` and hides console window
5. **Port 4070** is the Flask server port
6. **logo.ico** is the EXE icon — always reference it in spec files
7. **VS Code Local History** at `%APPDATA%\Code\User\History\` can recover accidentally overwritten files
8. **Never use `write_to_file` on app.py** — always use `replace_in_file` for targeted edits
9. **The `build/` directory** contains PyInstaller artifacts — safe to delete and regenerate
10. **`dist/` directory** contains built EXEs — generated by build process

## Common Tasks

### Rebuild EXE after changes

```bat
Buld.bat
```

### Test the app locally (without building)

```bat
python app.py
```

Then open http://localhost:4070 in a browser.

### Clean build artifacts

```bat
rmdir /s /q build dist
```

## Verification With Playwright CLI

- Use `playwright-cli` for all browser verifications.
- Always run in `--headed` mode. Example: `playwright-cli open --headed http://localhost:4070/login`.
- Bare `playwright-cli` requires a global install (`npm i -g playwright-cli`, version 0.262.0 seen). Fallback when not installed: `npx --yes playwright cli`.
- Get help with `playwright-cli --help`. Key commands: `open [url]`, `goto <url>`, `snapshot`, `find [text]`, `click <target>`, `fill <target> <text>`, `type <text>`, `press <key>`, `reload`, `screenshot`, `console`, `close`.
- `open` options: `--browser chrome|firefox|webkit|msedge`, `--headed`, `--persistent`, `--profile <dir>`, `--device`, `--mobile`, `--config`.
- Standard flow: `open --headed <url>` then `snapshot` to get refs, act with `click` or `fill`, confirm with `snapshot` plus `screenshot`, check `console` on failure.
- Flask runs on port 4070. For local checks run Flask in test mode that skips console hide and `hide_from_taskbar`. The built EXE keeps hiding.
- Review each route per page with snapshot plus screenshot before moving on.

## Question Protocol

- Always ask one question at a time. Never batch unrelated questions.
- One answer can change the next question, so always wait for the answer before asking the following question.
- Keep asking until no loose ends remain; only then present the final plan.
- Remember: Always ask one question at a time, because one question's answer can affect the next questions and its answers.

## Link Buttons In Jinja

- This repo is Flask Jinja plus Tailwind plus hand rolled `rg-btn` classes. There is no React `buttonVariants` and no `Link` component.
- When a button must look like a link, use an anchor with button classes. Example: `<a href="/logout" class="rg-btn rg-btn--secondary rg-btn--sm">Logout</a>`.
- Use this pattern for the sidebar logout link.

## UI Reference Rules

- **Theme: Vercel (vercel.com design language).** Copy Vercel's look: Geist Sans/Geist Mono fonts (bundled in `static/fonts/`, OFL license), `#000` dark background / `#fff` light background, cards `#0a0a0a` dark / `#fafafa` light, text `#ededed` dark / `#171717` light, secondary text gray `#888`/`#666`, blue accent `#0070f3`, radius 8px cards / 6px controls, soft shadows for elevation.
- **NO BORDERS anywhere in the UI.** Never add `border`, `border-*`, or hairline rules to cards, header, sidebar, inputs, switches, segmented controls, or drawers. Separate with background contrast and soft shadows only.
- **NO TOOLTIPS anywhere in the UI.** Do not add tooltip components, `title` attributes used as visual hints, or hover hint popups. `aria-label`s are allowed (invisible, accessibility only).
- Toggle switches: ON = blue `#0070f3`, OFF = gray. Pure monochrome otherwise — green/red only for status dots if needed.
- On/Off button pairs are replaced by `rg-switch` toggles wired to the same `*-on`/`*-off` endpoints. Load actions remain buttons.
- Full redesign scope covers login, dashboard headshot, sniper, extra, and settings. Keep a single account source in the sidebar footer. Settings shows no account block.

## Dependencies (requirements.txt)

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
