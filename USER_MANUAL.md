# Volatility 3 GUI – User Manual

Welcome to the **Volatility 3 GUI**, a professional desktop application for memory forensics. This application wraps the powerful Volatility 3 framework into a high-performance, asynchronous graphical interface, streamlining the process of analyzing raw memory dumps, crash dumps, and virtual machine snapshots.

---

## 1. Getting Started

### Launching the Application

Run the application by executing the `main.py` script from your command line:

```bash
python main.py
```

Upon startup, the application will initialize the Volatility 3 framework and load all available plugins in the background. The bottom status bar will indicate when the framework is ready and display the total number of loaded plugins.

---

## 2. Loading Evidence

The **EVIDENCE** panel is located in the top left corner.

**Supported Formats:**
Volatility 3 uses an "automagic" layer-stacking architecture, which means it attempts to detect the format automatically regardless of the file extension. You can load raw DD images (`.raw`, `.img`, `.bin`), VMware images (`.vmem`, `.vmss`), Windows crash dumps (`.dmp`), LiME images (`.lime`), QEMU/KVM images (`.qcow2`), Hyper-V images (`.vhd`, `.vhdx`), VirtualBox ELF files (`.elf`), and macOS RAM images (`.mddramimage`).

**How to Load:**

1. **Drag and Drop:** Drag your memory image file directly from your file explorer into the dashed box that says "DROP EVIDENCE FILE".
2. **Browse:** Click anywhere inside the dashed box to open a file browser and select your image.

Once loaded, the application will display the file name and size. Behind the scenes, it will automatically run an operating system detection task. Once detected, an OS badge (e.g., Windows, Linux, macOS) will appear below the file name.

---

## 3. Selecting a Plugin

The **PLUGINS** browser is located below the Evidence panel on the left.

* **Categorized Tree:** Plugins are grouped by operating system (`WINDOWS`, `LINUX`, `MACOS`, `OTHER`).
* **Instant Search:** Use the search bar at the top of the plugin panel to quickly filter plugins by name. The tree will instantly update to show only matching plugins.
* **Selection:** Click on a plugin (e.g., `pslist` under the Windows category). Its details and available options will automatically populate the central configuration area.

---

## 4. Configuring Plugin Options

When you select a plugin, the **PLUGIN CONFIGURATION** panel in the center of the screen updates dynamically.

* **Required vs Optional:** Required parameters are marked with a `*` and use bold text. Optional parameters are displayed in muted text.
* **Smart Inputs:** The interface provides native input controls for different parameter types (e.g., checkboxes for booleans, spinboxes for numbers, file pickers for URI paths).
* **Lists:** For parameters that expect multiple values (like multiple PIDs), type them as a comma-separated list (e.g., `4, 288, 1024`). Hex values (e.g., `0x1A4`) are supported for integer lists.
* **Informational Badges:** Sometimes a plugin requires complex internal components (like a Symbol Table or Translation Layer). These are resolved automatically by Volatility 3's "automagic" engine and will be displayed as grey, read-only badges at the bottom of the form so you are aware of them.

---

## 5. Running an Analysis

Once your evidence is loaded and the plugin is configured:

1. Click the **▶ RUN ANALYSIS** button.
2. The analysis runs in the background. You can monitor the progress via the compact progress bar located in the bottom status bar.
3. The interface remains fully responsive during the analysis. *Note: You cannot start a new analysis until the current one finishes.*

---

## 6. Reviewing Results

After the analysis completes, the data is populated in the **RESULTS** tab on the right side of the screen.

* **Sorting:** Click on any column header to instantly sort the data (ascending/descending). Numeric columns sort numerically, text columns alphabetically.
* **Row Count:** The upper right of the results panel displays a badge with the total number of returned rows.
* **Copying Data:**
  * You can select specific rows and press `Ctrl+C` (or right-click and select "Copy selected rows") to copy the data (including headers) to your clipboard, formatted cleanly with tabs.
  * You can also right-click a specific cell and choose "Copy cell".
* **Column Resizing:** Columns are automatically resized based on their content (up to a readable maximum width) but can be manually adjusted by dragging the column headers.

---

## 7. Exporting Data

You can save your forensic results for external reporting or processing.

Using the buttons in the top header bar:

* **Export JSON:** Saves the current table dataset as a structured JSON file.
* **Export CSV:** Saves the current table dataset as a Comma-Separated Values file.

*Tip: The header bar buttons are only enabled when there is data in the results table.*

---

## 8. The Analysis Console (Logs)

If you need deeper insight into what the framework is doing or why a plugin might have failed, switch to the **CONSOLE** tab.

* The console provides a timestamped, color-coded stream of log messages directly from the framework and the application backend.
* **Colors:** Grey (Debug), Blue (Info), Green (Success), Amber (Warning), Red (Error).
* If a plugin fails due to missing symbol tables or unsupported image formats, the console is the best place to view the detailed traceback.
* Use the **Copy** and **Clear** ghost buttons at the top right of the console to manage the log output.

---

## 9. Managing Your Session

* **Clear Data:** Use the **Clear** button in the top header to wipe the current results.
* **Session Timer:** The top right of the header bar continuously tracks your current session duration (`SESSION HH:MM:SS`).

---

*Thank you for using the Volatility 3 GUI.*
