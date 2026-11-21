![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-VSL--1.0-orange)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

# Volatility 3 GUI

**Point-and-click memory forensics.** A fast, asynchronous desktop interface for the [Volatility 3](https://github.com/volatilityfoundation/volatility3) framework — analyze memory dumps without touching the command line.

## Why this exists

Volatility 3 is powerful but entirely CLI-driven, which means remembering plugin names, flags, and profile detection every time. This wraps it in a real desktop app: drag in an image, let it auto-detect the OS, pick a plugin from a searchable list, and export results — all without leaving the GUI.

## Features

- **Direct Python API integration** — no subprocess/CLI calls under the hood, so it's fast and stable
- **Drag-and-drop image loading** for `.vmem`, `.img`, `.raw`, `.mem`, `.dmp`, `.bin`, `.lime`, `.dd`
- **Automatic OS detection** — no manual profile guessing
- **120+ searchable plugins** with dynamic configuration forms
- **Asynchronous execution** — the UI never freezes mid-analysis
- **Export to JSON/CSV** for reporting or further processing
- **Color-coded logging** for at-a-glance status

## Install

```bash
git clone https://github.com/saeedjamalhussains/Volatility_3_GUI
cd Volatility_3_GUI
pip install -r requirements.txt
python main.py
```

## Usage

1. Launch the app and drag in a memory image (or use File → Open)
2. Wait for automatic OS/profile detection
3. Search or browse the plugin list, configure options if needed
4. Run — results stream in live, color-coded by status
5. Export findings to JSON or CSV

## Tech stack

Python · PySide6 · Volatility 3

## Contributing

Issues and PRs welcome — this is an active project and forensics workflows vary a lot between analysts, so real-world feedback is genuinely useful.

## License

<!-- Add your license here, e.g. MIT — repos without a license are technically "all rights reserved," which quietly discourages contributors. -->
