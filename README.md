# Volatility 3 GUI

A premium desktop application for **Volatility 3** memory forensics analysis, built with **Python + PySide6**.

## Features

- 🔬 **Full Volatility 3 integration** — uses the Python API directly (no subprocess)
- 📂 **Drag-and-drop** memory image loading (`.vmem`, `.img`, `.raw`, `.mem`, `.dmp`, etc.)
- 🖥️ **Automatic OS detection** — Windows, Linux, macOS
- 🔌 **120+ plugins** — searchable, grouped by OS
- ⚙️ **Dynamic plugin options** — auto-generated form from plugin requirements
- 📊 **Sortable results table** — based on Volatility's TreeGrid output
- 📋 **Color-coded log panel** — INFO/WARNING/ERROR/DEBUG
- ⬇️ **Export** results as JSON or CSV
- 🔄 **Asynchronous execution** — UI never freezes during analysis

## Installation

```bash
# 1. Install dependencies
pip install PySide6 volatility3

# 2. (Optional) Install symbol packs for Windows analysis
#    Place windows.zip in the volatility3/symbols directory

# 3. Launch
python main.py
```

## Project Structure

Volatality_GUI/
├── main.py                         # Entry point
├── requirements.txt
├── backend/
│   ├── volatility_runner.py        # Core Volatility 3 engine
│   ├── plugin_manager.py           # Plugin discovery & metadata
│   ├── plugin_runner.py            # Async QThread workers
│   ├── os_detector.py              # OS fingerprinting
│   └── exporters.py                # JSON / CSV export
├── frontend/
│   ├── main_window.py              # QMainWindow
│   └── widgets/
│       ├── file_panel.py
│       ├── plugin_panel.py
│       ├── options_panel.py
│       ├── results_panel.py
│       ├── log_panel.py
│       └── progress_widget.py
├── models/
│   └── table_model.py              # QAbstractTableModel
├── utils/
│   └── threading.py                # BaseWorker / WorkerSignals
└── assets/
    └── main.qss                    # Dark neon stylesheet

## Usage

1. **Open a memory image** — drag it onto the drop zone or use File → Open
2. **Wait for OS detection** — the OS badge updates automatically
3. **Select a plugin** — double-click from the plugin tree (e.g. `windows.pslist.PsList`)
4. **Configure options** — fill in any optional parameters in the form
5. **Run** — click ▶ Run Plugin
6. **Export** — use the toolbar buttons to save as JSON or CSV

## Supported Memory Formats

`.vmem` `.img` `.raw` `.mem` `.dmp` `.bin` `.lime` `.dd`

## Notes

- Windows symbol tables are auto-downloaded on first use (requires internet)
- Linux/macOS symbol tables must be manually generated with [dwarf2json](https://github.com/volatilityfoundation/dwarf2json)
- Plugin availability depends on the memory image OS
