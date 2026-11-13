# 2581check IPC-2581 XML Schema Validator

[![Release](https://img.shields.io/github/v/release/cisco-ospo/oss-template?display_name=tag)](CHANGELOG.md)
[![Lint](https://github.com/cisco-ospo/oss-template/actions/workflows/lint.yml/badge.svg?branch=main)](https://github.com/marketplace/actions/super-linter)
[![Contributor-Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-fbab2c.svg)](CODE_OF_CONDUCT.md)
[![Maintainer](https://img.shields.io/badge/Maintainer-Cisco-00bceb.svg)](https://opensource.cisco.com)


## About The Project

The 2581check project is an IPC-2581 XML validation tool with unlimited line support.  It shows where the xml data does not match the schema with clickable links to the lines in question.

### Features

- ✅ Validate XML files against XSD schemas
- ✅ Handle XML files with millions of lines (no line limit!)
- ✅ Accurate line number detection for errors beyond line 65,535
- ✅ Clickable error messages that jump to exact XML location
- ✅ Real-time error filtering by category
- ✅ Configurable font sizes for all UI elements
- ✅ Configurable per-type error display limit (session-only)
- ✅ Persistent settings (remembers your files and preferences)
- ✅ Copy XML content to clipboard (Ctrl+C)
- ✅ Search functionality in error messages
- ✅ Resizable line numbers panel

## Getting Started

To get a local copy up and running follow these simple steps.

### Prerequisites

- Python 3.7 or higher
- PyQt5 5.15.0 or higher
- lxml 4.9.0 or higher

### Installation

1. Download/clone this repository to a project folder

### Setup option 1: Using pip (Recommended)

2. Install Python 3.7+ from https://www.python.org/downloads/

3. Open Command Prompt or Terminal and run:
```bash
pip install PyQt5 lxml
```

### Setup option 2: Using requirements.txt

2. Open Command Prompt in the application folder and run:
```bash
pip install -r requirements.txt
```

### Setup option 3: Using setup.bat (Windows only)

2. Double-click `setup.bat`
3. Follow the on-screen instructions


## Running the Application

### Windows
```bash
python 2581check.py
```

Or double-click `run.bat` for a convenient launcher.

Or double-click `2581check.py` if Python is associated with .py files.

### Linux/Mac
```bash
python3 2581check.py
```


## Building the Cython Version (Windows .exe)

The Cython path is optional and focuses on performance-critical validation code.
It compiles `validation_core.pyx` and packages a Windows executable.

### What Gets Built

- Compiled extension module: `validation_core*.pyd`
- Standalone Windows executable: `2581check_Distribution/dist/2581check.exe`

### Prerequisites

1. Python 3.11+ recommended on Windows
2. Runtime dependencies:
```bash
pip install -r requirements.txt
```
3. Build dependencies:
```bash
pip install Cython pyinstaller
```
4. Microsoft C++ Build Tools (MSVC toolset + Windows SDK)

Notes:
- The PowerShell build script tries to initialize the Visual Studio developer environment automatically.
- If C/C++ compilation fails, verify `cl.exe` and SDK headers are installed.

### Build Steps

1. From the repository root, generate distribution project files:
```bash
python convert_to_cython.py
```

2. Build the compiled module and create the executable:
```powershell
cd .\2581check_Distribution
.\build_distribution.bat
```

Alternative:
```powershell
cd .\2581check_Distribution
powershell -ExecutionPolicy Bypass -File .\build_distribution.ps1
```

### Running the Cython Build

After build completion:

```powershell
.\2581check_Distribution\dist\2581check.exe
```

## Python vs Cython Version

Both versions provide the same user-facing workflow and UI. The difference is in how validation internals are executed.

### Advantages of the Cython Version

- Faster performance for large XML workloads, especially line lookup and error-mapping paths.
- Better throughput when processing many schema validation errors.
- Distributed as a packaged `.exe`, which is convenient for Windows users who do not want to run Python directly.

### Differences and Tradeoffs

- Python version:
	- Run directly from source (`python 2581check.py`)
	- Simplest for development and debugging
	- No native compile toolchain required

- Cython version:
	- Requires one-time native build setup (Cython, PyInstaller, MSVC build tools)
	- Uses a compiled validation engine for performance-critical logic
	- Produces a distributable Windows executable


## Usage

Use this space to show useful examples of how a project can be used. Additional
screenshots, code examples and demos work well in this space. You may also link
to more resources.

_For more examples, please refer to the [Documentation](https://example.com) or
the [Wiki](https://github.com/github.com/cisco-open/2581check/wiki)_

### Basic Validation

1. **Select XSD Schema File**: Click the button and choose your .xsd file
2. **Select XML Data File**: Click the button and choose your .xml file
3. **Validate**: Click "Validate XML" to start validation
4. **View Errors**: Errors will appear in the "Validation Errors" panel
5. **Load XML**: Click "Load XML File" to view the XML content with line numbers
6. **Click Line Numbers**: Click on blue line numbers in errors to jump to that location in the XML viewer

### Error Filtering

- Error types are automatically categorized (e.g., "Missing child element", "Invalid value")
- Use checkboxes in the "Error Filters" panel to show/hide specific error types
- Click "All" to select all error types
- Click "None" to deselect all error types
- Filters update in real-time as you check/uncheck them

### Adjusting Display Settings

**Max Errors/type**
- Controls how many errors are shown per error category
- Defaults to 5 on every application startup
- Enter a number in the "Max Errors/type" field and press Enter
- Set to 0 for unlimited display per type (may be slow with thousands of errors)
- This setting is not persisted to config and is reset each launch

**Font Sizes**
- Adjust font sizes for different UI elements
- **Text**: Error messages and XML viewer (default: 9)
- **Buttons**: All buttons and labels (default: 9)
- **Line #**: Line number display (default: 8)
- **Headers**: Panel titles (default: 9)
- Enter values and press Enter to apply
- Valid range: 6-24 points

### Copy XML Content

- **Copy All**: Click "Copy XML" button to copy entire XML file to clipboard
- **Copy Selection**: Select text in XML viewer, then press Ctrl+C or click "Copy XML"
- Works even with very large files (millions of lines)

### Search Errors

1. Enter search term in the "Search" field
2. Click "Find" or press Enter
3. Use "Next" and "Previous" buttons to navigate through matches
4. Click "Clear" to clear search highlights

### Save Error Log

- Click "Save Errors to Log" to save all errors to a text file
- File is saved as `[your-xml-filename].log` in the same directory

### Configuration

Settings are automatically saved to `2581check_config.json` including:
- Last selected XSD and XML files
- Window size and position
- Panel sizes (splitter positions)
- Font sizes for all UI elements

Note: `Max Errors/type` is intentionally session-only and always defaults to 5 on startup.

### Handling Large Files

#### XML Files with 65,535+ Lines

The application automatically detects when error line numbers are truncated at 65,535 and searches the XML content to find the actual line numbers. Look for:

- **Blue links**: Exact line numbers found
- **Orange links**: Estimated line numbers (shows as "65535+ (est: ~123456)")

#### Very Large XML Files

- Files over 50MB will prompt a confirmation before loading
- The line number panel is resizable - drag the divider to adjust
- For files with 1M+ lines, line numbers are generated in chunks for better performance

### Keyboard Shortcuts

- **Ctrl+C** (when XML viewer has focus): Copy XML content to clipboard
- **Enter** (in any text field): Apply the setting or execute the action

### Troubleshooting

#### "No module named 'PyQt5'"
Install PyQt5: `pip install PyQt5`

#### "No module named 'lxml'"
Install lxml: `pip install lxml`

#### Application crashes or freezes
- Try reducing the "Max errors" setting if dealing with thousands of errors
- For very large XML files (100MB+), consider validating first, then loading the XML only if needed

#### Line numbers show as estimated (orange)
- This happens when the exact line cannot be found in the XML content
- The estimated location is usually close to the actual error
- Load the XML file and use the search feature to find the specific content mentioned in the error

#### Error filters don't work
- Make sure at least one error type is checked
- If all types are unchecked, you'll see "All error types are filtered out"
- Click "All" to re-enable all error types

### Tips & Tricks

1. **Persistent File Selection**: The app remembers your last XSD and XML files - just click "Validate XML" on restart
2. **Custom Window Layout**: Resize panels to your preference - settings are saved automatically
3. **Filter Workflows**: Use filters to focus on one error type at a time when fixing validation issues
4. **Font Customization**: Adjust fonts to match your monitor and vision needs
5. **Error Log**: Save errors to a log file for documentation or sharing with team members


## Roadmap

See the [open issues](https://github.com/github.com/cisco-open/2581check/issues) for a list
of proposed features (and known issues).

## Contributing

Contributions are what make the open source community such an amazing place to
learn, inspire, and create. Any contributions you make are **greatly
appreciated**. For detailed contributing guidelines, please see
[CONTRIBUTING.md](CONTRIBUTING.md)

## License

Distributed under the `Apache 2.0` License. See [LICENSE](LICENSE) for more
information.

## Contact

Terry Hoffman - terhoffm@ciso.com - email

Project Link:
[https://github.com/cisco-open/2581check](https://github.com/cisco-open/2581check)

