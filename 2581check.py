#!/usr/bin/python
# SPDX-License-Identifier: Apache-2.0
# Copyright 2025 Cisco Systems, Inc. and its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import os
import json
import re
from datetime import datetime
from lxml import etree
import urllib.request
import tempfile
import webbrowser  # NEW: For opening URLs in browser

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QSplitter, QGroupBox, QLabel, QPushButton, 
                           QTextEdit, QPlainTextEdit, QTextBrowser, QLineEdit, QProgressBar, 
                           QFileDialog, QMessageBox, QCheckBox, QScrollArea)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QTextCursor, QTextCharFormat, QKeySequence


# Version information
__version__ = "1.2.2"
__build__ = "20261110-013"
__release__ = "Stable"
__author__ = "Terry Hoffman @ Cisco"


class ValidationWorker(QThread):
    """Worker thread for XML validation"""
    progress_updated = pyqtSignal(int, str)
    validation_completed = pyqtSignal(bool, list)
    error_occurred = pyqtSignal(str)
    debug_message = pyqtSignal(str)
    
    def __init__(self, xsd_file, xml_file):
        super().__init__()
        self.xsd_file = xsd_file
        self.xml_file = xml_file
        self.cancelled = False
        self.xml_lines = []
        self.error_counter = 0
        self.debug_log = []
        self.preload_error = None
        self.element_search_positions = {}
        self.USE_CYTHON_OVERRIDE = False
        self.temp_xsd_file = None  # NEW: Track temp file for cleanup
    
    def cancel(self):
        self.cancelled = True
    
    def preload_xml_lines(self):
        """Preload XML lines for accurate line number tracking"""
        preload_log = []  # Local log to ensure we capture everything
        try:
            # Log what we're trying to open
            preload_log.append(f"[1] Starting preload...")
            preload_log.append(f"[2] XML file path: {self.xml_file}")
            
            # Check if file exists
            if not os.path.exists(self.xml_file):
                self.preload_error = f"File not found: {self.xml_file}"
                preload_log.append(f"[3] ERROR: File does not exist!")
                self.xml_lines = []
                self.debug_log.extend(preload_log)
                return
            
            preload_log.append(f"[3] File exists: ✓")
            
            # Check file size
            file_size = os.path.getsize(self.xml_file)
            preload_log.append(f"[4] File size: {file_size:,} bytes ({file_size / 1024 / 1024:.1f} MB)")
            
            # Read the file
            preload_log.append(f"[5] Opening file for reading...")
            with open(self.xml_file, 'r', encoding='utf-8') as f:
                preload_log.append(f"[6] File opened successfully, calling readlines()...")
                self.xml_lines = f.readlines()
                preload_log.append(f"[7] readlines() completed")
            
            # Verify we got data
            line_count = len(self.xml_lines)
            preload_log.append(f"[8] Lines read: {line_count:,}")
            
            if line_count == 0:
                self.preload_error = "File read successfully but returned 0 lines!"
                preload_log.append(f"[9] ERROR: {self.preload_error}")
            else:
                preload_log.append(f"[9] SUCCESS: Preloaded {line_count:,} lines")
            
        except Exception as e:
            self.preload_error = f"Preload exception: {str(e)}"
            preload_log.append(f"[ERROR] EXCEPTION: {self.preload_error}")
            import traceback
            preload_log.append(f"[ERROR] Traceback: {traceback.format_exc()}")
            self.xml_lines = []
        
        finally:
            # ALWAYS add to debug log
            self.debug_log.extend(preload_log)
            
            # ALSO write directly to a temp file to debug timing issues
            try:
                import tempfile
                temp_log = os.path.join(tempfile.gettempdir(), "2581check_preload_debug.txt")
                with open(temp_log, 'w') as f:
                    f.write("=== PRELOAD DIRECT LOG ===\n")
                    for msg in preload_log:
                        f.write(msg + "\n")
                    f.write(f"\nFinal xml_lines count: {len(self.xml_lines)}\n")
            except:
                pass  # Ignore errors writing temp file

    def clean_error_message(self, message):
        """Clean XML namespace prefixes from error messages"""
        cleaned = str(message)
        cleaned = re.sub(r'\{[^}]*\}', '', cleaned)
        cleaned = re.sub(r'\b\w+:', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned
    
    def find_actual_line_number(self, error_message, truncated_line):
        """Find the actual line number by searching the XML content"""
        if not self.xml_lines or truncated_line != 65535:
            return truncated_line
        
        # Increment counter for each 65535+ error
        self.error_counter += 1
        
        error_str = str(error_message).lower()
        original_error = str(error_message)
        total_lines = len(self.xml_lines)
        
        # Extract element name from error message
        element_match = re.search(r"element\s+'([^']+)'", error_str)
        if not element_match:
            # No element - use simple increment with default position
            if 'default' not in self.element_search_positions:
                self.element_search_positions['default'] = 1
            estimated = min(self.element_search_positions['default'], total_lines)
            self.element_search_positions['default'] += 1
            return estimated
        
        element_name = element_match.group(1)
        element_name = self.clean_error_message(element_name)
        if ':' in element_name:
            element_name = element_name.split(':', 1)[1]
        
        # Initialize search position for this element if not exists
        if element_name not in self.element_search_positions:
            self.element_search_positions[element_name] = 1
        
        search_start = self.element_search_positions[element_name]
        
        # For key-sequence errors, try to find exact match with key value
        key_sequence_match = re.search(r"key-sequence\s+\[([^\]]+)\]", original_error)
        if key_sequence_match:
            key_sequence_raw = key_sequence_match.group(1)
            key_values = re.findall(r"['\"]([^'\"]+)['\"]", key_sequence_raw)
            
            if key_values:
                key_value = key_values[0]  # Use first key value
                
                # Search from search_start forward for this element + key combination
                for i in range(search_start - 1, total_lines):
                    if self.cancelled:
                        break
                    line_content = self.xml_lines[i].lower()
                    
                    # Check if element is in this line
                    if f"<{element_name.lower()}" in line_content:
                        # Check if key value is in this line or next few lines
                        search_end = min(i + 3, total_lines)
                        context = ''.join(self.xml_lines[i:search_end]).lower()
                        
                        if key_value.lower() in context:
                            # Found it! Update search position for THIS element
                            self.element_search_positions[element_name] = i + 2
                            return i + 1
        
        # If key-sequence search failed OR no key-sequence, search for just the element
        for i in range(search_start - 1, total_lines):
            if self.cancelled:
                break
            line_content = self.xml_lines[i].lower()
            
            if f"<{element_name.lower()}" in line_content:
                # Found element! Update search position for THIS element
                self.element_search_positions[element_name] = i + 2
                return i + 1
        
        # Still not found - maybe we need to wrap around
        for i in range(0, search_start - 1):
            if self.cancelled:
                break
            line_content = self.xml_lines[i].lower()
            
            if f"<{element_name.lower()}" in line_content:
                # Found it earlier in file! Update search position
                self.element_search_positions[element_name] = i + 2
                return i + 1
        
        # Really couldn't find it - use fallback estimation
        estimated = min(search_start, total_lines)
        self.element_search_positions[element_name] += 1
        return f"65535+ (est: ~{estimated:,})"
    
    def download_schema(self, url):
        """Download XSD schema from URL to temporary file"""
        try:
            self.progress_updated.emit(5, f"Downloading schema from {url}...")
            
            # Create temporary file
            temp_fd, temp_path = tempfile.mkstemp(suffix='.xsd', prefix='schema_')
            os.close(temp_fd)
            
            # Download the schema
            urllib.request.urlretrieve(url, temp_path)
            
            self.temp_xsd_file = temp_path
            self.progress_updated.emit(10, "Schema downloaded successfully")
            return temp_path
            
        except Exception as e:
            raise Exception(f"Failed to download schema from URL: {str(e)}")
    
    def run(self):
        try:
            self.progress_updated.emit(0, "Starting validation...")
            
            if self.cancelled:
                return
            
            # Check if XSD is a URL or local file
            xsd_path = self.xsd_file
            if self.xsd_file.startswith('http://') or self.xsd_file.startswith('https://'):
                xsd_path = self.download_schema(self.xsd_file)
            
            if self.cancelled:
                return
            
            self.progress_updated.emit(5, "Preloading XML for line number tracking...")
            self.preload_xml_lines()
            
            if self.cancelled:
                return
            
            self.progress_updated.emit(20, "Parsing XSD schema file...")
            xsd_doc = etree.parse(xsd_path)  # Use xsd_path instead of self.xsd_file
            xsd = etree.XMLSchema(xsd_doc)
            
            if self.cancelled:
                return
            
            self.progress_updated.emit(40, "Parsing XML data file...")
            xml = etree.parse(self.xml_file)
            
            if self.cancelled:
                return
            
            self.progress_updated.emit(60, "Validating XML against schema...")
            is_valid = xsd.validate(xml)
            
            if self.cancelled:
                return
            
            self.progress_updated.emit(80, "Processing validation results...")
            
            if is_valid:
                self.progress_updated.emit(100, "✅ Validation completed successfully!")
                self.validation_completed.emit(True, [])
            else:
                error_log = xsd.error_log
                total_errors = len(error_log)
                processed_errors = []
                
                self.progress_updated.emit(85, f"Processing {total_errors} error(s)...")
                
                # Track ALL errors to see what's happening
                error_line_stats = []
                
                for idx, error in enumerate(error_log):
                    if self.cancelled:
                        return
                    
                    # Log errors 48755-48765 to see what's happening
                    if 48754 <= idx <= 48764:
                        error_line_stats.append(f"Error #{idx+1}: original line={error.line}, msg={str(error.message)[:80]}")
                    
                    if error.line == 65535:
                        actual_line = self.find_actual_line_number(str(error.message), error.line)
                        
                        fixed_error = type('FixedError', (), {
                            'line': actual_line,
                            'column': error.column,
                            'message': error.message,
                            'type_name': getattr(error, 'type_name', None),
                            'filename': error.filename,
                            'level_name': getattr(error, 'level_name', 'ERROR')
                        })()
                        processed_errors.append(fixed_error)
                    else:
                        processed_errors.append(error)
                    
                    if idx % 10 == 0:
                        progress = 85 + int((idx / total_errors) * 15)
                        self.progress_updated.emit(progress, f"Processing error {idx + 1} of {total_errors}...")
                
                # ALWAYS write debug file
                try:
                    xml_dir = os.path.dirname(os.path.abspath(self.xml_file))
                    xml_base = os.path.basename(self.xml_file)
                    xml_name = os.path.splitext(xml_base)[0]
                    debug_file = os.path.join(xml_dir, f"{xml_name}_DEBUG.txt")
                    
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write("=== LINE NUMBER CALCULATION DEBUG ===\n")
                        f.write(f"XML File: {self.xml_file}\n")
                        f.write(f"XML File Exists: {os.path.exists(self.xml_file)}\n")
                        f.write(f"XML Directory: {xml_dir}\n")
                        f.write(f"Debug File: {debug_file}\n")
                        f.write("\n")
                        
                        # Show ALL debug log messages from preload
                        f.write("=== PRELOAD DEBUG LOG ===\n")
                        for msg in self.debug_log[:20]:  # First 20 messages
                            f.write(msg + "\n")
                        f.write("\n")
                        
                        # Show preload error if any
                        if self.preload_error:
                            f.write(f"⚠️ PRELOAD ERROR: {self.preload_error}\n\n")
                        
                        f.write(f"Total Lines in XML: {len(self.xml_lines):,}\n")
                        f.write(f"Total Errors: {total_errors}\n")
                        f.write(f"Total 65535+ Errors: {self.error_counter}\n")
                        f.write(f"Debug Log Entries: {len(self.debug_log)}\n")
                        f.write("\n")
                        
                        # Show error line stats for errors 48755-48765
                        if error_line_stats:
                            f.write("=== ERRORS 48755-48765 (to see when 65535 appears) ===\n")
                            for stat in error_line_stats:
                                f.write(stat + "\n")
                            f.write("\n")
                        
                        if self.error_counter > 0:
                            # Show first few calculations if any
                            calc_msgs = [m for m in self.debug_log if "Error #" in m]
                            if calc_msgs:
                                f.write("=== DEBUG CALCULATIONS ===\n")
                                for msg in calc_msgs[:20]:
                                    f.write(msg + "\n")
                    
                    msg = f"✅ Debug file: {debug_file}"
                    self.debug_message.emit(msg)
                    self.progress_updated.emit(95, f"Debug: {xml_name}_DEBUG.txt")
                    
                except Exception as e:
                    error_msg = f"⚠️ Debug file error: {str(e)}"
                    self.debug_message.emit(error_msg)
                
                error_count = len(processed_errors)
                self.progress_updated.emit(100, f"❌ Validation failed with {error_count} error(s)")
                self.validation_completed.emit(False, processed_errors)
        
        except etree.XMLSyntaxError as e:
            if not self.cancelled:
                self.error_occurred.emit(f"XML Syntax Error: {str(e)}")
        except etree.XMLSchemaParseError as e:
            if not self.cancelled:
                self.error_occurred.emit(f"XSD Schema Parse Error: {str(e)}")
        except FileNotFoundError as e:
            if not self.cancelled:
                self.error_occurred.emit(f"File Not Found: {str(e)}")
        except Exception as e:
            if not self.cancelled:
                self.error_occurred.emit(f"Unexpected Error: {str(e)}")
        finally:
            # Clean up temporary schema file if it was downloaded
            if self.temp_xsd_file and os.path.exists(self.temp_xsd_file):
                try:
                    os.remove(self.temp_xsd_file)
                except:
                    pass  # Ignore cleanup errors


class XMLLoader(QThread):
    """Worker thread for loading large XML files"""
    progress_updated = pyqtSignal(int, str)
    content_loaded = pyqtSignal(str, list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, xml_file):
        super().__init__()
        self.xml_file = xml_file
        self.cancelled = False
    
    def cancel(self):
        self.cancelled = True
    
    def run(self):
        try:
            self.progress_updated.emit(0, "Loading XML file...")
            
            file_size = os.path.getsize(self.xml_file)
            self.progress_updated.emit(10, f"Reading file ({file_size / 1024 / 1024:.1f}MB)...")
            
            if self.cancelled:
                return
            
            with open(self.xml_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if self.cancelled:
                return
            
            self.progress_updated.emit(50, "Processing lines...")
            lines = content.splitlines()
            
            # Add progress update about preparing to display
            self.progress_updated.emit(75, f"Preparing to display {len(lines):,} lines...")
            
            self.progress_updated.emit(100, f"XML loaded successfully ({len(lines):,} lines)")
            self.content_loaded.emit(content, lines)
            
        except Exception as e:
            if not self.cancelled:
                self.error_occurred.emit(f"Error loading XML file: {str(e)}")


class XMLValidatorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"2581check v{__version__}")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize attributes
        # Get the directory where the script is located
        self.app_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(self.app_dir, "2581check_config.json")
        
        self.xsd_file = None
        self.xsd_is_url = False  # NEW: Track if XSD is a URL
        self.xml_file = None
        
        self.xml_content = ""
        self.xml_lines = []
        self.xml_loaded = False
        self.large_file_mode = False
        self.should_refresh_errors = True
        self.max_display_errors = 5  # Default errors per type (session-only, not persisted)
        
        # Font size settings
        self.text_pane_font_size = 9
        self.button_font_size = 9
        self.line_numbers_font_size = 8
        self.header_font_size = 9
        
        # Error management
        self.all_errors = []
        self.filtered_errors = []
        self.last_errors = []
        self.error_filters = {}
        
        # Search functionality
        self.search_matches = []
        self.current_match = -1
        self.last_search_term = ""
        
        # Worker threads
        self.validation_worker = None
        self.xml_loader = None
        
        # Load configuration and setup UI
        self.load_config()
        self.setup_ui()
        self.setup_connections()
        
        # Restore window geometry and splitter sizes
        self.restore_window_state()
        
        # Update UI with loaded config values
        if hasattr(self, 'errors_per_type_entry'):
            self.errors_per_type_entry.setText(str(self.max_display_errors))
        if hasattr(self, 'text_font_size_entry'):
            self.text_font_size_entry.setText(str(self.text_pane_font_size))
            self.button_font_size_entry.setText(str(self.button_font_size))
            self.line_numbers_font_size_entry.setText(str(self.line_numbers_font_size))
            self.header_font_size_entry.setText(str(self.header_font_size))
            self.apply_font_sizes()
        
        # Show initial status with version
        self.log_info(f"2581check v{__version__} (Build {__build__})")
        self.log_info(f"Author: {__author__}")
        self.log_info(f"Release: {__release__}")
        self.log_info(f"Config file: {self.config_file}")
        self.log_info("")
    
    def setup_ui(self):
        """Setup the main user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Create main splitter (horizontal)
        self.main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.main_splitter)
        
        # Left panel (main content)
        content_widget = self.create_content_panel()
        self.main_splitter.addWidget(content_widget)
        
        # Right panel (file selection + filters)
        right_panel_widget = self.create_right_panel()
        self.main_splitter.addWidget(right_panel_widget)
        
        # Set splitter proportions
        self.main_splitter.setSizes([900, 200])
        
        # Status bar
        self.status_bar = self.statusBar()
        self.status_label = QLabel("Ready - 2581check")
        self.status_bar.addWidget(self.status_label, 1)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
    
    def create_content_panel(self):
        """Create the main content panel"""
        content_widget = QWidget()
        layout = QVBoxLayout()
        content_widget.setLayout(layout)
        
        # Create vertical splitter for information, errors, and XML viewer
        self.content_splitter = QSplitter(Qt.Vertical)
        
        # Information panel
        info_group = QGroupBox("Information")
        info_layout = QVBoxLayout()
        info_group.setLayout(info_layout)
        
        # Font size controls
        font_controls_layout = QHBoxLayout()
        font_controls_layout.addWidget(QLabel("Font sizes:"))
        
        font_controls_layout.addWidget(QLabel("Text:"))
        self.text_font_size_entry = QLineEdit()
        self.text_font_size_entry.setText(str(self.text_pane_font_size))
        self.text_font_size_entry.setMaximumWidth(40)
        self.text_font_size_entry.setToolTip("Font size for text panes (info, errors, XML)")
        font_controls_layout.addWidget(self.text_font_size_entry)
        
        font_controls_layout.addWidget(QLabel("Buttons:"))
        self.button_font_size_entry = QLineEdit()
        self.button_font_size_entry.setText(str(self.button_font_size))
        self.button_font_size_entry.setMaximumWidth(40)
        self.button_font_size_entry.setToolTip("Font size for buttons and controls")
        font_controls_layout.addWidget(self.button_font_size_entry)
        
        font_controls_layout.addWidget(QLabel("Line #:"))
        self.line_numbers_font_size_entry = QLineEdit()
        self.line_numbers_font_size_entry.setText(str(self.line_numbers_font_size))
        self.line_numbers_font_size_entry.setMaximumWidth(40)
        self.line_numbers_font_size_entry.setToolTip("Font size for line numbers")
        font_controls_layout.addWidget(self.line_numbers_font_size_entry)
        
        font_controls_layout.addWidget(QLabel("Headers:"))
        self.header_font_size_entry = QLineEdit()
        self.header_font_size_entry.setText(str(self.header_font_size))
        self.header_font_size_entry.setMaximumWidth(40)
        self.header_font_size_entry.setToolTip("Font size for pane headers")
        font_controls_layout.addWidget(self.header_font_size_entry)
        
        font_controls_layout.addStretch()
        
        info_layout.addLayout(font_controls_layout)
        
        self.info_text = QTextEdit()
        self.info_text.setMaximumHeight(120)
        self.info_text.setReadOnly(True)
        info_layout.addWidget(self.info_text)
        
        # Error panel with search
        error_group = QGroupBox("Validation Errors/Warnings")
        error_layout = QVBoxLayout()
        error_group.setLayout(error_layout)
        
        # Search controls
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_entry = QLineEdit()
        self.search_button = QPushButton("Find")
        self.search_next_button = QPushButton("Next")
        self.search_prev_button = QPushButton("Previous")
        self.search_clear_button = QPushButton("Clear")
        self.search_status = QLabel("")
        
        search_layout.addWidget(self.search_entry)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.search_next_button)
        search_layout.addWidget(self.search_prev_button)
        search_layout.addWidget(self.search_clear_button)
        search_layout.addWidget(self.search_status, 1)
        error_layout.addLayout(search_layout)
        
        # Max errors per type display setting
        max_errors_layout = QHBoxLayout()
        max_errors_layout.addWidget(QLabel("Max Errors/type:"))
        self.errors_per_type_entry = QLineEdit()
        self.errors_per_type_entry.setText(str(self.max_display_errors))
        self.errors_per_type_entry.setMaximumWidth(80)
        self.errors_per_type_entry.setToolTip("Maximum number of errors to display per type (0 = no limit)")
        max_errors_layout.addWidget(self.errors_per_type_entry)
        max_errors_layout.addWidget(QLabel("Enter 0 for All"))
        
        max_errors_layout.addStretch()
        error_layout.addLayout(max_errors_layout)
        
        # Error text display
        self.error_text = QTextBrowser()
        self.error_text.setReadOnly(True)
        self.error_text.setOpenLinks(False)
        self.error_text.setOpenExternalLinks(False)
        error_layout.addWidget(self.error_text)
        
        # XML Viewer panel
        xml_group = QGroupBox("XML File Viewer")
        xml_layout = QVBoxLayout()
        xml_group.setLayout(xml_layout)
        
        # XML viewer controls
        xml_controls = QHBoxLayout()
        self.load_xml_button = QPushButton("Load XML File")
        self.goto_line_label = QLabel("Go to line:")
        self.goto_line_entry = QLineEdit()
        self.goto_line_entry.setMaximumWidth(160)
        self.goto_button = QPushButton("Go")
        self.copy_xml_button = QPushButton("Copy XML")
        self.copy_xml_button.setToolTip("Copy XML content to clipboard (Ctrl+C)")
        
        xml_controls.addWidget(self.load_xml_button)
        xml_controls.addWidget(self.goto_line_label)
        xml_controls.addWidget(self.goto_line_entry)
        xml_controls.addWidget(self.goto_button)
        xml_controls.addWidget(self.copy_xml_button)
        xml_controls.addStretch()
        xml_layout.addLayout(xml_controls)
        
        # XML content with line numbers - use horizontal splitter
        xml_splitter = QSplitter(Qt.Horizontal)
        
        # Line numbers display
        self.line_numbers = QPlainTextEdit()
        self.line_numbers.setReadOnly(True)
        self.line_numbers.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.line_numbers.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # XML content display
        self.xml_text = QPlainTextEdit()
        self.xml_text.setReadOnly(True)
        
        # Add widgets to splitter
        xml_splitter.addWidget(self.line_numbers)
        xml_splitter.addWidget(self.xml_text)
        
        # Configure splitter properties
        xml_splitter.setSizes([80, 800])
        xml_splitter.setStretchFactor(0, 0)
        xml_splitter.setStretchFactor(1, 1)
        
        # Set minimum and maximum widths for line numbers
        self.line_numbers.setMinimumWidth(50)
        self.line_numbers.setMaximumWidth(200)
        
        xml_layout.addWidget(xml_splitter)
        
        # Add panels to content splitter
        self.content_splitter.addWidget(info_group)
        self.content_splitter.addWidget(error_group)
        self.content_splitter.addWidget(xml_group)
        
        # Set splitter proportions
        self.content_splitter.setSizes([80, 150, 250])
        
        layout.addWidget(self.content_splitter)
        
        return content_widget
    
    def create_right_panel(self):
        """Create the right panel with file selection and filters"""
        right_widget = QWidget()
        layout = QVBoxLayout()
        right_widget.setLayout(layout)
        
        # Version info at top
        version_group = QGroupBox("Version Information")
        version_layout = QVBoxLayout()
        version_group.setLayout(version_layout)
        
        version_label = QLabel(f"v{__version__} (Build {__build__})")
        version_label.setStyleSheet("font-weight: bold; color: #2E8B57;")
        version_layout.addWidget(version_label)
        
        release_label = QLabel(f"Release: {__release__}")
        version_layout.addWidget(release_label)
        
        author_label = QLabel(f"Release: {__author__}")
        author_label.setStyleSheet("font-size: 8pt; color: #666;")
        version_layout.addWidget(author_label)
        
        layout.addWidget(version_group)
        
        # File selection group
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout()
        file_group.setLayout(file_layout)
        
        # XSD file selection - MODIFIED to support URLs
        xsd_label_header = QLabel("XSD Schema:")
        xsd_label_header.setStyleSheet("font-weight: bold;")
        file_layout.addWidget(xsd_label_header)
        
        # URL input option
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("URL:"))
        self.xsd_url_entry = QLineEdit()
        self.xsd_url_entry.setPlaceholderText("https://webstds.ipc.org/2581")
        
        # Set default URL or restore from config
        if self.xsd_file and self.xsd_is_url:
            self.xsd_url_entry.setText(self.xsd_file)  # Restore URL from config
        else:
            self.xsd_url_entry.setText("https://webstds.ipc.org/2581")  # Default URL
        
        self.xsd_url_button = QPushButton("Use URL")
        self.xsd_url_browse_button = QPushButton("Browse URL")
        self.xsd_url_browse_button.setToolTip("Open URL in web browser to find schema file")
        self.xsd_url_download_button = QPushButton("Download Schema")  # NEW
        self.xsd_url_download_button.setToolTip("Download schema from URL to local file")
        url_layout.addWidget(self.xsd_url_entry, 1)
        url_layout.addWidget(self.xsd_url_button)
        url_layout.addWidget(self.xsd_url_browse_button)
        url_layout.addWidget(self.xsd_url_download_button)  # NEW
        file_layout.addLayout(url_layout)
        
        # File selection option
        file_xsd_layout = QHBoxLayout()
        file_xsd_layout.addWidget(QLabel("File:"))
        self.xsd_button = QPushButton("Browse...")
        self.xsd_label = QLabel("No XSD file selected")
        self.xsd_label.setWordWrap(True)
        if self.xsd_file:
            if self.xsd_is_url:
                self.xsd_label.setText(f"URL: {self.xsd_file}")
            else:
                self.xsd_label.setText(os.path.basename(self.xsd_file))
        file_xsd_layout.addWidget(self.xsd_button)
        file_xsd_layout.addWidget(self.xsd_label, 1)
        file_layout.addLayout(file_xsd_layout)
        
        # Add separator
        file_layout.addWidget(QLabel(""))
        
        # XML file selection (unchanged)
        xml_label_header = QLabel("XML Data File:")
        xml_label_header.setStyleSheet("font-weight: bold;")
        file_layout.addWidget(xml_label_header)
        
        xml_layout = QHBoxLayout()
        self.xml_button = QPushButton("Select XML Data File")
        self.xml_label = QLabel("No XML file selected")
        if self.xml_file:
            self.xml_label.setText(os.path.basename(self.xml_file))
        xml_layout.addWidget(self.xml_button)
        xml_layout.addWidget(self.xml_label, 1)
        file_layout.addLayout(xml_layout)
        
        # Control buttons - row 1: Validate, Cancel, Save
        control_layout = QHBoxLayout()
        self.validate_button = QPushButton("Validate XML")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.save_log_button = QPushButton("Save Errors/Warnings to Log")
        self.save_log_button.setEnabled(False)

        control_layout.addWidget(self.validate_button)
        control_layout.addWidget(self.cancel_button)
        control_layout.addWidget(self.save_log_button)
        file_layout.addLayout(control_layout)

        # Control buttons - row 2: Check buttons
        check_layout = QHBoxLayout()
        self.check_other_button = QPushButton("Check for Other")
        self.check_other_button.setToolTip("Search for type='OTHER' comment='' patterns")
        self.check_nonstandard_button = QPushButton("Check for NonstandardAttribute")
        self.check_nonstandard_button.setToolTip("Search for NonstandardAttribute elements and categorize by name and value")

        check_layout.addWidget(self.check_other_button)
        check_layout.addWidget(self.check_nonstandard_button)
        check_layout.addStretch()
        file_layout.addLayout(check_layout)
        
        layout.addWidget(file_group)
        
        # Add the filter panel
        filter_widget = self.create_filter_panel()
        layout.addWidget(filter_widget)
        
        return right_widget
    
    def create_filter_panel(self):
        """Create the error filter panel"""
        filter_widget = QWidget()
        layout = QVBoxLayout()
        filter_widget.setLayout(layout)
        
        # Filter controls
        filter_group = QGroupBox("Error/Warning Filters")
        filter_layout = QVBoxLayout()
        filter_group.setLayout(filter_layout)
        
        # Control buttons
        control_layout = QHBoxLayout()
        self.select_all_button = QPushButton("All")
        self.clear_all_button = QPushButton("None") 
        
        control_layout.addWidget(self.select_all_button)
        control_layout.addWidget(self.clear_all_button)
        control_layout.addStretch()  # Add stretch to push buttons to the left
        filter_layout.addLayout(control_layout)
        
        # Scrollable area for filter checkboxes
        self.filter_scroll = QScrollArea()
        self.filter_widget = QWidget()
        self.filter_layout = QVBoxLayout()
        self.filter_widget.setLayout(self.filter_layout)
        self.filter_scroll.setWidget(self.filter_widget)
        self.filter_scroll.setWidgetResizable(True)
        filter_layout.addWidget(self.filter_scroll)
        
        layout.addWidget(filter_group)
        
        # Initial empty state
        empty_label = QLabel("No errors to filter")
        self.filter_layout.addWidget(empty_label)
        self.filter_layout.addStretch()
        
        return filter_widget

    def setup_connections(self):
        """Setup signal-slot connections"""
        # File selection
        self.xsd_button.clicked.connect(self.select_xsd_file)
        self.xsd_url_button.clicked.connect(self.use_xsd_url)
        self.xsd_url_browse_button.clicked.connect(self.browse_xsd_url)
        self.xsd_url_download_button.clicked.connect(self.download_xsd_schema)  # NEW
        self.xsd_url_entry.returnPressed.connect(self.use_xsd_url)
        self.xml_button.clicked.connect(self.select_xml_file)
        
        # Validation
        self.validate_button.clicked.connect(self.validate_xml)
        self.check_other_button.clicked.connect(self.check_for_other)
        self.check_nonstandard_button.clicked.connect(self.check_for_nonstandard_attribute)
        self.cancel_button.clicked.connect(self.cancel_validation)
        self.save_log_button.clicked.connect(self.save_error_log)
        
        # Search
        self.search_button.clicked.connect(self.search_errors)
        self.search_next_button.clicked.connect(self.search_next)
        self.search_prev_button.clicked.connect(self.search_prev)
        self.search_clear_button.clicked.connect(self.clear_search)
        self.search_entry.returnPressed.connect(self.search_errors)
        
        # XML viewer
        self.load_xml_button.clicked.connect(self.load_xml_content)
        self.goto_button.clicked.connect(self.goto_line)
        self.goto_line_entry.returnPressed.connect(self.goto_line)
        self.copy_xml_button.clicked.connect(self.copy_xml_content)
        
        # Filter controls
        self.select_all_button.clicked.connect(self.select_all_filters)
        self.clear_all_button.clicked.connect(self.clear_all_filters)
        self.errors_per_type_entry.returnPressed.connect(self.update_max_errors)
        
        # Font size controls
        self.text_font_size_entry.returnPressed.connect(self.update_font_sizes)
        self.button_font_size_entry.returnPressed.connect(self.update_font_sizes)
        self.line_numbers_font_size_entry.returnPressed.connect(self.update_font_sizes)
        self.header_font_size_entry.returnPressed.connect(self.update_font_sizes)
        
        # Synchronize scrolling between line numbers and XML content
        self._sync_in_progress = False
        self.xml_text.verticalScrollBar().valueChanged.connect(self.sync_line_numbers_to_xml)
        self.line_numbers.verticalScrollBar().valueChanged.connect(self.sync_xml_to_line_numbers)
        
        # Save window state when splitters are moved
        self.main_splitter.splitterMoved.connect(self.on_splitter_moved)
        self.content_splitter.splitterMoved.connect(self.on_splitter_moved)

    def on_splitter_moved(self, pos, index):
        """Save config when splitters are moved"""
        # Use a timer to avoid saving too frequently during dragging
        if not hasattr(self, '_splitter_save_timer'):
            self._splitter_save_timer = QTimer()
            self._splitter_save_timer.setSingleShot(True)
            self._splitter_save_timer.timeout.connect(self.save_config)
        
        self._splitter_save_timer.stop()
        self._splitter_save_timer.start(500)  # Save 500ms after last movement

    def sync_line_numbers_to_xml(self, value):
        """Sync line numbers scrollbar to XML text scrollbar"""
        if self._sync_in_progress:
            return
        self._sync_in_progress = True
        self.line_numbers.verticalScrollBar().setValue(value)
        self._sync_in_progress = False

    def sync_xml_to_line_numbers(self, value):
        """Sync XML text scrollbar to line numbers scrollbar"""
        if self._sync_in_progress:
            return
        self._sync_in_progress = True
        self.xml_text.verticalScrollBar().setValue(value)
        self._sync_in_progress = False

    def force_scroll_sync(self):
        """Force synchronization between line numbers and XML text"""
        if self._sync_in_progress:
            return
        self._sync_in_progress = True
        xml_value = self.xml_text.verticalScrollBar().value()
        self.line_numbers.verticalScrollBar().setValue(xml_value)
        self._sync_in_progress = False
    
    def load_config(self):
        """Load previously selected files from config file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    
                    # Load XSD (check if it's a URL or file)
                    if config.get('xsd_file'):
                        xsd_value = config['xsd_file']
                        if xsd_value.startswith('http://') or xsd_value.startswith('https://'):
                            self.xsd_file = xsd_value
                            self.xsd_is_url = True
                        elif os.path.exists(xsd_value):
                            self.xsd_file = xsd_value
                            self.xsd_is_url = False
                    
                    if config.get('xml_file') and os.path.exists(config['xml_file']):
                        self.xml_file = config['xml_file']
                    
                    if config.get('text_pane_font_size'):
                        self.text_pane_font_size = int(config['text_pane_font_size'])
                    if config.get('button_font_size'):
                        self.button_font_size = int(config['button_font_size'])
                    if config.get('line_numbers_font_size'):
                        self.line_numbers_font_size = int(config['line_numbers_font_size'])
                    if config.get('header_font_size'):
                        self.header_font_size = int(config['header_font_size'])
                    
                    self.saved_geometry = config.get('window_geometry')
                    self.saved_main_splitter_sizes = config.get('main_splitter_sizes')
                    self.saved_content_splitter_sizes = config.get('content_splitter_sizes')
        except Exception as e:
            print(f"Error loading config: {e}")
    
    def save_config(self):
        """Save current file selections and window state to config file"""
        try:
            # Capture current window geometry
            current_geometry = [self.x(), self.y(), self.width(), self.height()]
            
            # Capture current splitter sizes
            current_main_splitter_sizes = None
            current_content_splitter_sizes = None
            
            if hasattr(self, 'main_splitter') and self.main_splitter:
                current_main_splitter_sizes = self.main_splitter.sizes()
            
            if hasattr(self, 'content_splitter') and self.content_splitter:
                current_content_splitter_sizes = self.content_splitter.sizes()
            
            config = {
                'xsd_file': self.xsd_file,  # Can be URL or file path
                'xml_file': self.xml_file,
                'text_pane_font_size': self.text_pane_font_size,
                'button_font_size': self.button_font_size,
                'line_numbers_font_size': self.line_numbers_font_size,
                'header_font_size': self.header_font_size,
                'window_geometry': current_geometry,
                'main_splitter_sizes': current_main_splitter_sizes,
                'content_splitter_sizes': current_content_splitter_sizes
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
            # Debug output to verify saving
            print(f"Saved window geometry: {current_geometry}")
            if current_main_splitter_sizes:
                print(f"Saved main splitter sizes: {current_main_splitter_sizes}")
            if current_content_splitter_sizes:
                print(f"Saved content splitter sizes: {current_content_splitter_sizes}")
                
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def restore_window_state(self):
        """Restore window geometry and splitter sizes from saved config"""
        try:
            # Restore window geometry
            if hasattr(self, 'saved_geometry') and self.saved_geometry:
                x, y, width, height = self.saved_geometry
                print(f"Restoring window geometry: x={x}, y={y}, w={width}, h={height}")
                self.setGeometry(x, y, width, height)
            
            # Use QTimer to restore splitter sizes after UI is fully initialized
            if hasattr(self, 'saved_main_splitter_sizes') and self.saved_main_splitter_sizes:
                print(f"Restoring main splitter sizes: {self.saved_main_splitter_sizes}")
                QTimer.singleShot(100, lambda: self.main_splitter.setSizes(self.saved_main_splitter_sizes))
            
            if hasattr(self, 'saved_content_splitter_sizes') and self.saved_content_splitter_sizes:
                print(f"Restoring content splitter sizes: {self.saved_content_splitter_sizes}")
                QTimer.singleShot(150, lambda: self.content_splitter.setSizes(self.saved_content_splitter_sizes))
                
        except Exception as e:
            print(f"Error restoring window state: {e}")
    
    def closeEvent(self, event):
        """Handle window close event to save configuration"""
        try:
            # Force save of current window state before closing
            self.save_config()
            event.accept()
        except Exception as e:
            print(f"Error during close: {e}")
            event.accept()  # Close anyway
    
    def use_xsd_url(self):
        """Use XSD schema from URL"""
        url = self.xsd_url_entry.text().strip()
        
        if not url:
            QMessageBox.warning(self, "No URL", "Please enter a URL for the XSD schema.")
            return
        
        # Validate URL format
        if not (url.startswith('http://') or url.startswith('https://')):
            QMessageBox.warning(self, "Invalid URL", 
                              "URL must start with http:// or https://")
            return
        # Save the URL FIRST (before validation)
        self.xsd_file = url
        self.xsd_is_url = True
        self.xsd_label.setText(f"URL: {url}")
        self.xsd_url_entry.setText(url)
        self.save_config()
        
        # Now test if URL is accessible (optional validation)
        try:
            self.update_status("Testing URL connection...")
            QApplication.processEvents()
            
            # Try to open the URL with a timeout
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                content_type = response.headers.get('Content-Type', '')
                
                # Check if it looks like XML
                if 'xml' not in content_type.lower() and not url.endswith('.xsd'):
                    reply = QMessageBox.question(self, "Warning",
                        f"URL may not be an XSD schema (Content-Type: {content_type}).\n\n"
                        "Continue anyway?",
                        QMessageBox.Yes | QMessageBox.No)
                    if reply != QMessageBox.Yes:
                        # URL is already saved, just clear displays
                        self.clear_displays()
                        self.log_info(f"Selected XSD schema from URL: {url} (not validated)")
                        self.update_status("XSD URL saved (validation skipped)")
                        return
            
            # Validation successful
            self.clear_displays()
            self.log_info(f"Selected XSD schema from URL: {url} (validated)")
            self.update_status("XSD URL set and validated successfully")
            
        except urllib.error.URLError as e:
            # URL validation failed, but URL is already saved
            self.clear_displays()
            self.log_info(f"Selected XSD schema from URL: {url}")
            self.log_info(f"⚠️ URL validation warning: {str(e)}")
            self.log_info("URL saved - validation will occur when you click 'Validate XML'")
            self.update_status("XSD URL saved (validation will occur during XML validation)")
            
            QMessageBox.warning(self, "URL Validation Warning", 
                               f"Cannot access URL for validation:\n{str(e)}\n\n"
                               "The URL has been saved and will be tested when you validate the XML.\n"
                               "If the URL is correct, you can proceed with validation.")
        except Exception as e:
            # Other errors - URL is still saved
            self.clear_displays()
            self.log_info(f"Selected XSD schema from URL: {url}")
            self.log_info(f"⚠️ URL test error: {str(e)}")
            self.update_status("XSD URL saved (validation will occur during XML validation)")
            
            QMessageBox.warning(self, "URL Test Warning", 
                               f"Error testing URL:\n{str(e)}\n\n"
                               "The URL has been saved and will be tested when you validate the XML.")

    def browse_xsd_url(self):
        """Open the XSD URL in web browser for browsing"""
        url = self.xsd_url_entry.text().strip()
        
        if not url:
            url = "https://webstds.ipc.org/2581"  # Default to IPC-2581 directory
            self.xsd_url_entry.setText(url)
        
        try:
            webbrowser.open(url)
            self.update_status(f"Opened {url} in web browser")
            self.log_info(f"Browse to find your schema file at: {url}")
            self.log_info("Copy the full URL of the .xsd file and paste it into the URL field")
        except Exception as e:
            QMessageBox.warning(self, "Browser Error", 
                              f"Could not open browser:\n{str(e)}")

    def select_xsd_file(self):
        """Select XSD schema file"""
        initial_dir = os.path.dirname(self.xsd_file) if self.xsd_file and not self.xsd_is_url else os.getcwd()
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select XSD Schema File", initial_dir,
            "XSD files (*.xsd);;All files (*.*)")
        
        if filename:
            self.xsd_file = filename
            self.xsd_is_url = False
            self.xsd_label.setText(os.path.basename(filename))
            self.xsd_url_entry.clear()  # Clear URL field
            self.clear_displays()
            self.log_info(f"Selected XSD schema file: {filename}")
            self.save_config()
    
    def select_xml_file(self):
        """Select XML data file"""
        initial_dir = os.path.dirname(self.xml_file) if self.xml_file else os.getcwd()
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select XML Data File", initial_dir,
            "XML files (*.xml);;All files (*.*)")
        
        if filename:
            self.xml_file = filename
            self.xml_label.setText(os.path.basename(filename))
            self.clear_displays()
            self.xml_loaded = False
            self.log_info(f"Selected XML data file: {filename}")
            self.save_config()
    
    def update_max_errors(self):
        """Update maximum display errors setting"""
        try:
            text = self.errors_per_type_entry.text().strip()
            if not text:
                return
            
            new_max = int(text)
            if new_max < 0:
                new_max = 0
            
            self.max_display_errors = new_max
            self.errors_per_type_entry.setText(str(new_max))
            
            # Update status
            if new_max == 0:
                self.update_status("Updated to show ALL errors (no limit)")
            else:
                self.update_status(f"Updated to show {new_max:,} errors per type")
            
            if hasattr(self, 'all_errors') and self.all_errors:
                self.apply_filters()
                
        except ValueError:
            self.errors_per_type_entry.setText(str(self.max_display_errors))
    
    def update_font_sizes(self):
        """Update font sizes from UI controls"""
        try:
            text_size = int(self.text_font_size_entry.text().strip())
            button_size = int(self.button_font_size_entry.text().strip())
            line_numbers_size = int(self.line_numbers_font_size_entry.text().strip())
            header_size = int(self.header_font_size_entry.text().strip())
            
            if not (6 <= text_size <= 24):
                raise ValueError("Text font size must be 6-24")
            if not (6 <= button_size <= 24):
                raise ValueError("Button font size must be 6-24")
            if not (6 <= line_numbers_size <= 24):
                raise ValueError("Line numbers font size must be 6-24")
            if not (6 <= header_size <= 24):
                raise ValueError("Header font size must be 6-24")
            
            self.text_pane_font_size = text_size
            self.button_font_size = button_size
            self.line_numbers_font_size = line_numbers_size
            self.header_font_size = header_size
            
            self.apply_font_sizes()
            self.save_config()
            
        except ValueError as e:
            self.text_font_size_entry.setText(str(self.text_pane_font_size))
            self.button_font_size_entry.setText(str(self.button_font_size))
            self.line_numbers_font_size_entry.setText(str(self.line_numbers_font_size))
            self.header_font_size_entry.setText(str(self.header_font_size))
            self.update_status(f"Invalid font size: {str(e)}")
    
    def apply_font_sizes(self):
        """Apply font sizes to all UI elements"""
        text_font = QFont("Courier New")
        text_font.setPointSize(self.text_pane_font_size)
        
        self.info_text.setFont(text_font)
        self.info_text.document().setDefaultFont(text_font)
        self.error_text.setFont(text_font)
        self.error_text.document().setDefaultFont(text_font)
        self.xml_text.setFont(text_font)
        self.xml_text.document().setDefaultFont(text_font)
        
        self.xml_text.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.xml_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        line_font = QFont("Courier New")
        line_font.setPointSize(self.text_pane_font_size)
        self.line_numbers.setFont(line_font)
        self.line_numbers.document().setDefaultFont(line_font)
        
        self.line_numbers.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.line_numbers.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.xml_text.document().setDocumentMargin(0)
        self.line_numbers.document().setDocumentMargin(0)

        button_font = QFont()
        button_font.setPointSize(self.button_font_size)
        
        for widget in self.findChildren(QPushButton):
            widget.setFont(button_font)
        for widget in self.findChildren(QLabel):
            widget.setFont(button_font)
        for widget in self.findChildren(QLineEdit):
            widget.setFont(button_font)
        for widget in self.findChildren(QCheckBox):
            widget.setFont(button_font)

        header_font = QFont()
        header_font.setPointSize(self.header_font_size)
        for widget in self.findChildren(QGroupBox):
            widget.setFont(header_font)
        
        self.update_status("Font sizes updated")

        # Scale the goto-line entry to fit 10 digits at the current button font size
        from PyQt5.QtGui import QFontMetrics
        fm = QFontMetrics(button_font)
        digit_width = fm.horizontalAdvance("0" * 10) + 12  # +12px for padding
        self.goto_line_entry.setFixedWidth(digit_width)
    
    def copy_xml_content(self):
        """Copy XML content to clipboard"""
        if not self.xml_loaded or not self.xml_content:
            QMessageBox.warning(self, "No XML Content", 
                              "No XML content loaded to copy. Please load an XML file first.")
            return
        
        try:
            clipboard = QApplication.clipboard()
            
            cursor = self.xml_text.textCursor()
            if cursor.hasSelection():
                selected_text = cursor.selectedText()
                clipboard.setText(selected_text)
                self.update_status(f"Copied {len(selected_text)} characters of selected XML to clipboard")
                self.log_info(f"Copied selected XML content ({len(selected_text)} characters) to clipboard")
            else:
                clipboard.setText(self.xml_content)
                self.update_status(f"Copied entire XML file ({len(self.xml_content)} characters) to clipboard")
                self.log_info(f"Copied entire XML file ({len(self.xml_lines)} lines, {len(self.xml_content)} characters) to clipboard")
            
        except Exception as e:
            error_msg = f"Error copying to clipboard: {str(e)}"
            self.log_error(error_msg)
            QMessageBox.critical(self, "Copy Error", error_msg)

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if (event.key() == Qt.Key_C and event.modifiers() == Qt.ControlModifier and 
            (self.xml_text.hasFocus() or self.line_numbers.hasFocus())):
            self.copy_xml_content()
            event.accept()
            return
        
        super().keyPressEvent(event)

    def validate_xml(self):
        """Start XML validation"""
        if not self.xsd_file or not self.xml_file:
            QMessageBox.critical(self, "Error", 
                               "Please select both XSD and XML files before validation.")
            return
        
        if self.validation_worker and self.validation_worker.isRunning():
            return
        
        self.update_status("Starting validation...")
        
        self.validate_button.setText("Validating...")
        self.validate_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        
        self.validation_worker = ValidationWorker(self.xsd_file, self.xml_file)
        self.validation_worker.progress_updated.connect(self.update_validation_progress)
        self.validation_worker.validation_completed.connect(self.validation_completed)
        self.validation_worker.error_occurred.connect(self.validation_error)
        self.validation_worker.debug_message.connect(self.log_info)  # NEW: Connect debug messages to log
        self.validation_worker.finished.connect(self.validation_finished)
        self.validation_worker.start()
    
    def check_for_other(self):
        """Check for type='OTHER' comment='' patterns in XML file"""
        if not self.xml_file:
            QMessageBox.warning(self, "No XML File", 
                              "Please select an XML file first.")
            return
        
        try:
            self.update_status("Checking for type='OTHER' patterns...")
            self.log_info("🔍 Checking for type='OTHER' comment='' patterns...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            QApplication.processEvents()

            # Read XML file
            with open(self.xml_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            total_lines = len(lines)
            # Search for pattern and extract comment content
            pattern = re.compile(r'type="OTHER"\s+comment="([^"]*)"')
            warnings = []
            report_interval = max(1, total_lines // 20)  # report every 5%

            for line_num, line in enumerate(lines, start=1):
                if line_num % report_interval == 0 or line_num == total_lines:
                    pct = int(line_num / total_lines * 100)
                    self.progress_bar.setValue(pct)
                    self.update_status(f"Checking for type='OTHER' patterns... {pct}% ({line_num}/{total_lines} lines)")
                    QApplication.processEvents()
                match = pattern.search(line)
                if match:
                    comment_content = match.group(1)
                    self.log_info(f"  ⚠️ Line {line_num}: type='OTHER' comment='{comment_content}'")
                    # Create a warning entry similar to error structure
                    warning = type('Warning', (), {
                        'line': line_num,
                        'column': line.find('type="OTHER"'),
                        'message': f'Found type="OTHER" comment="{comment_content}" pattern',
                        'comment': comment_content,
                        'type_name': 'WARNING',
                        'filename': self.xml_file,
                        'level_name': 'WARNING'
                    })()
                    warnings.append(warning)

            self.progress_bar.setValue(100)
            QApplication.processEvents()
            QTimer.singleShot(1000, lambda: self.progress_bar.setVisible(False))

            if warnings:
                warning_count = len(warnings)
                # self.log_info(f"Found {warning_count} warning(s) with type='OTHER' comment='' patterns")
                
                # Store warnings
                self.all_errors = warnings
                self.last_errors = warnings
                self.filtered_errors = warnings
                
                # Update filter panel and display
                self.update_filter_panel()
                self.apply_filters()
                
                # Enable save button
                self.save_log_button.setEnabled(True)
                
                # Show message with HTML formatting for better visibility
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Check Complete")
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setTextFormat(Qt.RichText)
                msg_box.setText(f"<p>Found <b>{warning_count}</b> occurrence(s) of type='OTHER' comment='' patterns.</p>"
                               "<p>These are flagged as warnings, not errors.</p>"
                               '<p style="color: #FF6600; font-weight: bold; background-color: white; padding: 8px; border-left: 4px solid #FF6600;">'
                               '⚠️ The "OTHER" keyword is a temporary workaround for missing IPC-2581 features and may not be interpreted correctly by all applications. '
                               "Before using it, please check if your required feature exists in a newer IPC-2581 version. "
                               "If it is still missing, please report it to support@ipc2581.com."
                               "</p>")
                msg_box.exec_()
            else:
                self.log_info("✅ No type='OTHER' comment='' patterns found")
                QMessageBox.information(self, "Check Complete", 
                                      "No type='OTHER' comment='' patterns found in the XML file.")
            
            self.update_status("Check for Other completed")
            
        except Exception as e:
            error_msg = f"Error checking for OTHER patterns: {str(e)}"
            self.log_error(error_msg)
            QMessageBox.critical(self, "Check Error", error_msg)
    
    def check_for_nonstandard_attribute(self):
        """Check for NonstandardAttribute elements in XML file, categorized by name and value"""
        if not self.xml_file:
            QMessageBox.warning(self, "No XML File",
                              "Please select an XML file first.")
            return

        try:
            self.update_status("Checking for NonstandardAttribute elements...")
            self.log_info("🔍 Checking for NonstandardAttribute elements...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            QApplication.processEvents()

            with open(self.xml_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            total_lines = len(lines)
            # Match <NonstandardAttribute ... name="..." ... value="..." .../> (attributes in any order)
            pattern = re.compile(r'<NonstandardAttribute\b([^>]*/?>)')
            name_pattern = re.compile(r'name="([^"]*)"')
            value_pattern = re.compile(r'value="([^"]*)"')
            type_pattern = re.compile(r'\btype="([^"]*)"')

            warnings = []
            # Track counts by (name, value) for summary
            from collections import Counter
            pair_counts = Counter()
            report_interval = max(1, total_lines // 20)  # report every 5%

            for line_num, line in enumerate(lines, start=1):
                if line_num % report_interval == 0 or line_num == total_lines:
                    pct = int(line_num / total_lines * 100)
                    self.progress_bar.setValue(pct)
                    self.update_status(f"Checking for NonstandardAttribute... {pct}% ({line_num}/{total_lines} lines)")
                    QApplication.processEvents()
                m = pattern.search(line)
                if m:
                    attr_str = m.group(1)
                    name_m = name_pattern.search(attr_str)
                    value_m = value_pattern.search(attr_str)
                    type_m = type_pattern.search(attr_str)
                    attr_name = name_m.group(1) if name_m else ''
                    attr_value = value_m.group(1) if value_m else ''
                    attr_type = type_m.group(1) if type_m else ''
                    pair_counts[(attr_name, attr_value)] += 1
                    self.log_info(f"  ⚠️ Line {line_num}: NonstandardAttribute name='{attr_name}' value='{attr_value}'")
                    msg = f'NonstandardAttribute name="{attr_name}" value="{attr_value}"'
                    if attr_type:
                        msg += f' type="{attr_type}"'
                    warning = type('Warning', (), {
                        'line': line_num,
                        'column': line.find('<NonstandardAttribute'),
                        'message': msg,
                        'type_name': 'WARNING',
                        'filename': self.xml_file,
                        'level_name': 'WARNING'
                    })()
                    warnings.append(warning)

            self.progress_bar.setValue(100)
            QApplication.processEvents()
            QTimer.singleShot(1000, lambda: self.progress_bar.setVisible(False))

            if warnings:
                warning_count = len(warnings)
                self.all_errors = warnings
                self.last_errors = warnings
                self.filtered_errors = warnings

                self.update_filter_panel()
                self.apply_filters()
                self.save_log_button.setEnabled(True)

                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Check Complete")
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setTextFormat(Qt.RichText)
                msg_box.setText(
                    f"<p>Found <b>{warning_count}</b> NonstandardAttribute occurrence(s).</p>"
                    "<p>These are flagged as warnings, not errors.</p>"
                    '<p style="color: #FF6600; font-weight: bold; background-color: white; padding: 8px; border-left: 4px solid #FF6600;">'
                    '⚠️ The use of NonstandardAttribute carries vendor-specific data not defined by IPC-2581 and may make the file unreadable or uninterpretable by other vendors\' software. '
                    'Before using it, please check if the required feature exists in a newer IPC-2581 version. '
                    'If it is still missing, please report it to support@ipc2581.com.'
                    '</p>'
                )
                msg_box.exec_()
            else:
                self.log_info("✅ No NonstandardAttribute elements found")
                QMessageBox.information(self, "Check Complete",
                                      "No NonstandardAttribute elements found in the XML file.")

            self.update_status("Check for NonstandardAttribute completed")

        except Exception as e:
            error_msg = f"Error checking for NonstandardAttribute: {str(e)}"
            self.log_error(error_msg)
            QMessageBox.critical(self, "Check Error", error_msg)

    def cancel_validation(self):
        """Cancel current validation"""
        if self.validation_worker:
            self.validation_worker.cancel()
            self.update_status("Cancelling validation...")
            self.log_info("❌ Validation cancelled by user")
    
    def update_validation_progress(self, progress, message):
        """Update validation progress"""
        self.progress_bar.setValue(progress)
        self.update_status(message)
    
    def validation_completed(self, is_valid, errors):
        """Handle validation completion"""
        if is_valid:
            self.log_info("✅ XML validation successful! The XML file is valid according to the schema.")
            QMessageBox.information(self, "Validation Success", 
                                  "The XML file is valid according to the schema!")
        else:
            error_count = len(errors)
            self.log_info("❌ XML validation failed. See errors below.")
            
            self.all_errors = errors
            self.last_errors = errors
            self.filtered_errors = errors
            
            if error_count > 1000:
                # self.log_info(f"Large error set ({error_count} errors) - updating display asynchronously...")
                QTimer.singleShot(100, self.update_filter_panel)
                QTimer.singleShot(200, self.apply_filters)
            else:
                self.update_filter_panel()
                self.apply_filters()
            
            self.save_log_button.setEnabled(True)
            
            QMessageBox.warning(self, "Validation Failed", 
                              f"XML validation failed with {error_count} error(s). "
                              f"Use the filter panel to focus on specific error types.")
    
    def validation_error(self, error_message):
        """Handle validation error"""
        self.log_error(error_message)
        QMessageBox.critical(self, "Validation Error", error_message)
    
    def validation_finished(self):
        """Reset UI after validation finishes"""
        self.validate_button.setText("Validate XML")
        self.validate_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        QTimer.singleShot(2000, lambda: self.progress_bar.setVisible(False))
    
    def load_xml_content(self):
        """Load XML content for viewing"""
        if not self.xml_file:
            QMessageBox.warning(self, "No XML File", 
                              "Please select an XML file first.")
            return
        
        if self.xml_loader and self.xml_loader.isRunning():
            return
        
        file_size = os.path.getsize(self.xml_file)
        if file_size > 50 * 1024 * 1024:
            reply = QMessageBox.question(self, "Large File Warning",
                f"The XML file is {file_size / 1024 / 1024:.1f}MB. "
                "Loading large files may take time and consume memory. Continue?",
                QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        
        self.update_status("Loading XML file...")
        self.progress_bar.setVisible(True)
        
        self.xml_loader = XMLLoader(self.xml_file)
        self.xml_loader.progress_updated.connect(self.update_validation_progress)
        self.xml_loader.content_loaded.connect(self.xml_content_loaded)
        self.xml_loader.error_occurred.connect(self.xml_loading_error)
        self.xml_loader.finished.connect(lambda: self.progress_bar.setVisible(False))
        self.xml_loader.start()
    
    def xml_content_loaded(self, content, lines):
        """Handle loaded XML content"""
        self.xml_content = content
        self.xml_lines = lines
        self.xml_loaded = True
        
        line_count = len(lines)
        
        # Update status before displaying - this should be visible
        self.update_status(f"Rendering XML display ({line_count:,} lines)...")
        QApplication.processEvents()  # Force UI update
        
        self.log_info(f"Generating line numbers for {line_count:,} lines...")
        
        # Display XML content
        self.xml_text.setPlainText(content)
        
        # Generate line numbers
        self.generate_line_numbers(line_count)
        QTimer.singleShot(100, self.force_scroll_sync)
        
        if self.all_errors:
            self.apply_filters()
        
        self.log_info(f"Loaded XML file: {os.path.basename(self.xml_file)} ({line_count:,} lines)")
        
        # Update final status
        self.update_status(f"XML displayed: {line_count:,} lines")
    
    def xml_loading_error(self, error_message):
        """Handle errors that occur during XML loading"""
        self.log_error(error_message)
        QMessageBox.critical(self, "Loading Error", error_message)
    
    def generate_line_numbers(self, total_lines):
        """Generate line numbers for the XML viewer"""
        if total_lines > 100000:
            self.log_info(f"Generating line numbers for large file ({total_lines:,} lines)...")
        
        if total_lines > 1000000:
            chunk_size = 100000
            line_number_chunks = []
            
            for start in range(0, total_lines, chunk_size):
                end = min(start + chunk_size, total_lines)
                chunk = '\n'.join(str(i) for i in range(start + 1, end + 1))
                line_number_chunks.append(chunk)
            
            line_numbers_text = '\n'.join(line_number_chunks)
        else:
            line_numbers_text = '\n'.join(str(i) for i in range(1, total_lines + 1))
        
        self.line_numbers.setPlainText(line_numbers_text)
        
        self.xml_text.document().setDocumentMargin(0)
        self.line_numbers.document().setDocumentMargin(0)
        
        from PyQt5.QtGui import QTextBlockFormat
        block_format = QTextBlockFormat()
        block_format.setLineHeight(1.0, QTextBlockFormat.SingleHeight)
        
        cursor_xml = self.xml_text.textCursor()
        cursor_xml.select(QTextCursor.Document)
        cursor_xml.mergeBlockFormat(block_format)
        
        cursor_line = self.line_numbers.textCursor()
        cursor_line.select(QTextCursor.Document) 
        cursor_line.mergeBlockFormat(block_format)
        
        if total_lines > 100000:
            self.log_info(f"Line number generation completed for {total_lines:,} lines")
    
    def goto_line(self):
        """Go to a specific line in the XML viewer"""
        try:
            line_num = int(self.goto_line_entry.text())
            if not self.xml_loaded or not self.xml_lines:
                QMessageBox.warning(self, "No XML Loaded", 
                                  "Please load an XML file first.")
                return
                
            if 1 <= line_num <= len(self.xml_lines):
                cursor = self.xml_text.textCursor()
                cursor.movePosition(QTextCursor.Start)
                
                document = self.xml_text.document()
                target_block = document.findBlockByLineNumber(line_num - 1)
                if target_block.isValid():
                    cursor.setPosition(target_block.position())
                    self.xml_text.setTextCursor(cursor)
                    self.xml_text.ensureCursorVisible()
                    self.force_scroll_sync()
                else:
                    for _ in range(line_num - 1):
                        cursor.movePosition(QTextCursor.Down)
                    self.xml_text.setTextCursor(cursor)
                    self.xml_text.ensureCursorVisible()
                    self.force_scroll_sync()
            else:
                QMessageBox.warning(self, "Invalid Line", 
                                  f"Line number must be between 1 and {len(self.xml_lines):,}")
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid line number")
    
    def navigate_to_line(self, line_number):
        """Navigate to a specific line in the XML viewer"""
        if not self.xml_loaded or not self.xml_lines:
            self.update_status("XML file not loaded - cannot navigate to line")
            return
        
        line_number = int(line_number)
        
        if 1 <= line_number <= len(self.xml_lines):
            document = self.xml_text.document()
            target_block = document.findBlockByLineNumber(line_number - 1)
            
            if target_block.isValid():
                cursor = self.xml_text.textCursor()
                cursor.setPosition(target_block.position())
                self.xml_text.setTextCursor(cursor)
                self.xml_text.ensureCursorVisible()
                self.force_scroll_sync()
                self.goto_line_entry.setText(str(line_number))
                self.update_status(f"Navigated to line {line_number:,}")
            else:
                cursor = self.xml_text.textCursor()
                cursor.movePosition(QTextCursor.Start)
                for _ in range(line_number - 1):
                    cursor.movePosition(QTextCursor.Down)
                self.xml_text.setTextCursor(cursor)
                self.xml_text.ensureCursorVisible()
                self.force_scroll_sync()
                self.goto_line_entry.setText(str(line_number))
                self.update_status(f"Navigated to line {line_number:,}")
        else:
            self.update_status(f"Line {line_number:,} is out of range (1-{len(self.xml_lines):,})")
    
    def categorize_error(self, error_message):
        """Categorize error message by type using the structured format"""
        clean_msg = error_message.lower()
        
        # Check for warnings from Check for Other functionality
        if 'type="other"' in clean_msg and 'comment=' in clean_msg:
            # Extract the comment value to create separate warning types
            comment_match = re.search(r'comment="([^"]*)"', error_message)
            if comment_match:
                comment_value = comment_match.group(1)
                if comment_value:
                    return f"⚠️ WARNING: type='OTHER' comment='{comment_value}'"
                else:
                    return "⚠️ WARNING: type='OTHER' comment=''"
            return "⚠️ WARNING: type='OTHER' pattern"

        # Check for warnings from Check for NonstandardAttribute functionality
        if error_message.startswith('NonstandardAttribute '):
            name_match = re.search(r'name="([^"]*)"', error_message)
            value_match = re.search(r'value="([^"]*)"', error_message)
            attr_name = name_match.group(1) if name_match else ''
            attr_value = value_match.group(1) if value_match else ''
            if attr_name.upper() == 'TEXT':
                attr_value = 'various'
            return f"⚠️ NonstandardAttribute: name='{attr_name}' value={attr_value}"
        
        # Extract the main error description after the colon
        # Format: "Line X, Column Y: Element 'Name': [Error Description]"
        colon_match = re.search(r':\s*(.+?)(?:\.|$)', error_message)
        if colon_match:
            main_description = colon_match.group(1).strip()
            
            # Look for specific patterns in the main description
            desc_lower = main_description.lower()
            
            # Pattern 1: "This element is not expected"
            if "this element is not expected" in desc_lower:
                return "This element is not expected"
            
            # Pattern 2: "No match found for key-sequence"
            elif "no match found for key-sequence" in desc_lower:
                return "No match found for key-sequence"
            
            # Pattern 3: "Duplicate key-sequence"
            elif "duplicate key-sequence" in desc_lower:
                return "Duplicate key-sequence"
            
            # Pattern 4: "The attribute ... is required but missing"
            elif "attribute" in desc_lower and ("required" in desc_lower or "missing" in desc_lower):
                return "Missing required attribute"
            
            # Pattern 5: "Missing child element"
            elif "missing child element" in desc_lower:
                return "Missing child element(s)"
            
            # Pattern 6: "Invalid value" or "not a valid"
            elif "invalid value" in desc_lower or "not a valid" in desc_lower:
                return "Invalid value"
            
            # Pattern 7: "The content of element ... is not complete"
            elif "content" in desc_lower and "not complete" in desc_lower:
                return "Incomplete element content"
            
            # Pattern 8: General duplicate detection
            elif "duplicate" in desc_lower:
                return "Duplicate element/attribute"
            
            # Pattern 9: Type-related errors
            elif "type" in desc_lower and "not found" in desc_lower:
                return "Type not found"
            
            # Pattern 10: Namespace issues
            elif "namespace" in desc_lower:
                return "Namespace issue"
            
            # Pattern 11: Schema validation
            elif "schema" in desc_lower:
                return "Schema validation error"
            
            # Pattern 12: Try to extract the main action/issue from the beginning
            else:
                # Look for common action words at the start
                action_patterns = [
                    (r'^the\s+attribute\s+.*\s+is\s+not\s+allowed', "Invalid attribute"),
                    (r'^element\s+.*\s+is\s+not\s+allowed', "Element not allowed"),
                    (r'^the\s+value\s+.*\s+is\s+not\s+valid', "Invalid value"),
                    (r'^expected\s+is', "Expected element missing"),
                    (r'^attribute\s+.*\s+has\s+invalid', "Invalid attribute value"),
                    (r'^text\s+content\s+is\s+not\s+allowed', "Text content not allowed"),
                    (r'^the\s+element\s+.*\s+has\s+incomplete', "Incomplete element"),
                ]
                
                for pattern, category in action_patterns:
                    if re.search(pattern, desc_lower):
                        return category
                
                # If we can't categorize it specifically, create a more descriptive "other" category
                # Extract the first few words to make it more useful
                words = main_description.split()[:4]  # First 4 words
                if len(words) >= 2:
                    return f"Other: {' '.join(words)}..."
                else:
                    return f"Other: {main_description[:30]}..."
        
        # Fallback to original categorization if pattern matching fails
        if "missing child element" in clean_msg or "missing required" in clean_msg:
            return "Missing child element(s)"
        elif "not expected" in clean_msg or "not allowed here" in clean_msg:
            return "This element is not expected"
        elif "duplicate key-sequence" in clean_msg:
            return "Duplicate key-sequence"
        elif "no match found for key" in clean_msg or ("key-sequence" in clean_msg and "no match found" in clean_msg):
            return "No match found for key-sequence"
        elif "invalid value" in clean_msg or "not a valid" in clean_msg:
            return "Invalid value"
        elif "duplicate" in clean_msg:
            return "Duplicate element/attribute"
        elif "not found" in clean_msg and "type" in clean_msg:
            return "Type not found"
        elif "attribute" in clean_msg and ("required" in clean_msg or "missing" in clean_msg):
            return "Missing required attribute"
        elif "attribute" in clean_msg and ("invalid" in clean_msg or "not allowed" in clean_msg):
            return "Invalid attribute"
        elif "namespace" in clean_msg:
            return "Namespace issue"
        elif "schema" in clean_msg:
            return "Schema validation error"
        else:
            return "Other validation error"
    
    def clean_error_message(self, message):
        """Clean XML namespace prefixes from error messages"""
        cleaned = str(message)
        cleaned = re.sub(r'\{[^}]*\}', '', cleaned)
        cleaned = re.sub(r'\b\w+:', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned
    
    def update_filter_panel(self):
        """Update the filter panel with current error types"""
        for i in reversed(range(self.filter_layout.count())):
            item = self.filter_layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                else:
                    self.filter_layout.removeItem(item)
        
        if not hasattr(self, 'all_errors') or not self.all_errors:
            empty_label = QLabel("No errors to filter")
            self.filter_layout.addWidget(empty_label)
            self.filter_layout.addStretch()
            return
        
        error_types = {}
        try:
            for error in self.all_errors:
                clean_message = self.clean_error_message(error.message)
                error_type = self.categorize_error(clean_message)
                if error_type not in error_types:
                    error_types[error_type] = 0
                error_types[error_type] += 1
        except Exception as e:
            empty_label = QLabel(f"Error processing filters: {str(e)}")
            self.filter_layout.addWidget(empty_label)
            self.filter_layout.addStretch()
            return
        
        self.error_filters = {}
        for error_type, count in sorted(error_types.items()):
            checkbox = QCheckBox(f"{error_type} ({count})")
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self.apply_filters)
            self.error_filters[error_type] = checkbox
            self.filter_layout.addWidget(checkbox)
        
        self.filter_layout.addStretch()
    
    def select_all_filters(self):
        """Select all error type filters"""
        for checkbox in self.error_filters.values():
            checkbox.setChecked(True)
        # REMOVED: Manual refresh - checkboxes already trigger apply_filters() via stateChanged signal

    def clear_all_filters(self):
        """Clear all error type filters"""
        for checkbox in self.error_filters.values():
            checkbox.setChecked(False)
        # REMOVED: Manual refresh - checkboxes already trigger apply_filters() via stateChanged signal

    def apply_filters(self):
        """Apply current filter settings to error display"""
        if not hasattr(self, 'all_errors') or not self.all_errors:
            return
        
        self.filtered_errors = []
        for error in self.all_errors:
            clean_message = self.clean_error_message(error.message)
            error_type = self.categorize_error(clean_message)
            
            if (error_type in self.error_filters and 
                self.error_filters[error_type].isChecked()):
                self.filtered_errors.append(error)
        
        self.update_error_display()
    
    def update_error_display(self):
        """Update the error text display with filtered errors - showing first 10 of each type"""
        if not hasattr(self, 'filtered_errors'):
            self.filtered_errors = []
        
        self.error_text.clear()
        
        if not self.filtered_errors:
            if hasattr(self, 'all_errors') and self.all_errors:
                self.error_text.append("All error/warning types are filtered out.\n"
                                     "Use the filter panel to enable error/warning types.")
            else:
                self.error_text.append("No errors/warnings to display.")
            return
        
        error_count = len(self.filtered_errors)
        
        # Get max display limit (0 = no limit)
        display_limit = self.max_display_errors if self.max_display_errors > 0 else None
        
        # Group errors by type and show based on max_display_errors setting
        errors_by_type = {}
        for error in self.filtered_errors:
            clean_message = self.clean_error_message(error.message)
            error_type = self.categorize_error(clean_message)
            
            if error_type not in errors_by_type:
                errors_by_type[error_type] = []
            errors_by_type[error_type].append(error)
        
        # Display summary
        self.error_text.append(f"📊 Total Errors/Warnings: {error_count:,}")
        self.error_text.append(f"📋 Error/Warning Types: {len(errors_by_type)}")
        self.error_text.append("")
        if display_limit:
            self.error_text.append(f"Showing first {display_limit:,} errors/warnings of each type:")
        else:
            self.error_text.append("Showing all errors/warnings of each type:")
        self.error_text.append("=" * 60)
        self.error_text.append("")
        
        html_content = []
        total_displayed = 0
        
        # Display errors grouped by type
        for error_type, errors in sorted(errors_by_type.items()):
            type_count = len(errors)
            
            # Calculate how many to display (None means show all)
            if display_limit is None:
                display_count = type_count
            else:
                display_count = min(display_limit, type_count)
            
            # Check if this is a warning or error
            is_warning = error_type.startswith("⚠️ WARNING")
            header_color = "#FF8C00" if is_warning else "#2E8B57"  # Orange for warnings, green for errors
            
            # Type header
            if display_limit is not None and type_count > display_limit:
                type_header = f'<b style="color: {header_color};">{error_type} ({type_count:,} items - showing first {display_limit:,})</b>'
            else:
                type_header = f'<b style="color: {header_color};">{error_type} ({type_count:,} item{"s" if type_count != 1 else ""})</b>'
            html_content.append(type_header)
            
            # Add warning note for type='OTHER' patterns
            if error_type.startswith("⚠️ WARNING") and "type='OTHER'" in error_type:
                html_content.append('<div style="color: #FF6600; font-weight: bold; background-color: white; padding: 6px; margin: 4px 0; border-left: 4px solid #FF6600;">'
                                  '⚠️ The "OTHER" keyword is a temporary workaround for missing IPC-2581 features and may not be interpreted correctly by all applications. '
                                  'Before using it, please check if your required feature exists in a newer IPC-2581 version. '
                                  'If it is still missing, please report it to support@ipc2581.com.'
                                  '</div>')
                
                # Add specific guidance based on the comment type
                error_type_lower = error_type.lower()
                if "comment='" in error_type_lower:
                    # Extract comment value to check its content
                    comment_match = re.search(r"comment='([^']*)'", error_type_lower)
                    if comment_match:
                        comment_content = comment_match.group(1)
                        if 'layer' in comment_content:
                            html_content.append('<div style="color: #CC0000; font-weight: bold; background-color: white; padding: 4px; margin: 2px 0; border-left: 4px solid #CC0000; font-size: 9pt;">'
                                              'Layers should be defined in CadData Layer elements.'
                                              '</div>')
                        if 'thickness' in comment_content:
                            html_content.append('<div style="color: #CC0000; font-weight: bold; background-color: white; padding: 4px; margin: 2px 0; border-left: 4px solid #CC0000; font-size: 9pt;">'
                                              'Thickness for layers should be defined in StackupLayer elements.'
                                              '</div>')
            
            # Display errors of this type (up to display_count)
            for error in errors[:display_count]:
                clean_message = self.clean_error_message(error.message)
                actual_line = getattr(error, 'line', 0)
                
                if self.xml_loaded:
                    if isinstance(actual_line, int):
                        line_text = f'<a href="goto:{actual_line}" style="color: blue; font-weight: bold;">→Line {actual_line:,}←</a>'
                    else:
                        est_match = re.search(r'est: ~(\d+)', str(actual_line))
                        if est_match:
                            est_line = int(est_match.group(1))
                            line_text = f'<a href="goto:{est_line}" style="color: orange; font-weight: bold;">→{actual_line}←</a>'
                        else:
                            line_text = f'<span style="color: orange;">{actual_line}</span>'
                else:
                    if isinstance(actual_line, int):
                        line_text = f'<span style="color: gray;">Line {actual_line:,}</span>'
                    else:
                        line_text = f'<span style="color: gray;">{actual_line}</span>'
                
                error_html = f"  {line_text}, Column {getattr(error, 'column', 0)}: {clean_message}"
                html_content.append(error_html)
                
                total_displayed += 1
            
            # Add spacing between types
            html_content.append("")
        
        formatted_html = '<br>'.join(html_content)
        self.error_text.append(formatted_html)
        
        # Summary footer
        self.error_text.append("")
        self.error_text.append("=" * 60)
        self.error_text.append(f"Displayed: {total_displayed:,} of {error_count:,} total errors/warnings")
        self.error_text.append("")
        
        if self.xml_loaded:
            help_text = f'<span style="color: darkgreen; font-size: {max(6, self.text_pane_font_size - 2)}pt;">💡 Click blue line numbers to navigate. Use "Save Errors/Warnings to Log" to export all errors/warnings.</span>'
        else:
            help_text = f'<span style="color: orange; font-size: {max(6, self.text_pane_font_size - 2)}pt;">💡 Click "Load XML File" to make line numbers clickable. Use "Save Errors/Warnings to Log" to export all errors/warnings.</span>'
        
        self.error_text.append(help_text)
        
        if not hasattr(self, '_anchor_connected'):
            self.error_text.anchorClicked.connect(self.on_error_link_clicked)
            self._anchor_connected = True
    
    def on_error_link_clicked(self, url):
        """Handle clicks on error line number links"""
        try:
            url_str = url.toString()
            
            if url_str.startswith("goto:"):
                line_number = int(url_str.split(":")[1])
                self.navigate_to_line(line_number)
                self.xml_text.setFocus()
                
        except Exception as e:
            self.update_status(f"Error navigating to line: {e}")
    
    def search_errors(self):
        """Search for text in error display"""
        search_term = self.search_entry.text().strip()
        if not search_term:
            return
        
        self.clear_search()
        
        content = self.error_text.toPlainText()
        if not content.strip():
            self.search_status.setText("No content to search")
            return
        
        self.search_matches = []
        self.last_search_term = search_term
        
        start = 0
        while True:
            index = content.lower().find(search_term.lower(), start)
            if index == -1:
                break
            self.search_matches.append((index, index + len(search_term)))
            start = index + 1
        
        if self.search_matches:
            self.current_match = 0
            self.highlight_current_match()
            self.search_status.setText(f"Found {len(self.search_matches)} matches")
        else:
            self.search_status.setText("No matches found")

    def search_next(self):
        """Go to next search match"""
        if not self.search_matches:
            return
        
        
        self.current_match = (self.current_match + 1) % len(self.search_matches)
        self.highlight_current_match()
    
    def search_prev(self):
        """Go to previous search match"""
        if not self.search_matches:
            return
        
        self.current_match = (self.current_match - 1) % len(self.search_matches)
        self.highlight_current_match()
    
    def highlight_current_match(self):
        """Highlight the current search match"""
        if not self.search_matches or self.current_match < 0:
            return
        
        start_pos, end_pos = self.search_matches[self.current_match]
        
        cursor = self.error_text.textCursor()
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
        
        self.error_text.setTextCursor(cursor)
        self.error_text.ensureCursorVisible()
        
        self.search_status.setText(f"Match {self.current_match + 1} of {len(self.search_matches)}")
    
    def clear_search(self):
        """Clear search highlights"""
        self.search_matches = []
        self.current_match = -1
        self.search_status.setText("")
    
    def save_error_log(self):
        """Save error messages to a log file"""
        if not self.xml_file or not self.last_errors:
            QMessageBox.warning(self, "No Errors", 
                              
                              "No errors to save or no XML file selected.")
            return
        
        # Save log file in the same directory as the XML file (not the app directory)
        xml_basename = os.path.splitext(self.xml_file)[0]
        log_filename = f"{xml_basename}.log"
        
        try:
            with open(log_filename, 'w', encoding='utf-8') as log_file:
                log_file.write(f"2581check Validation Error Log - Version {__version__}\n")
                log_file.write(f"Build: {__build__} ({__release__})\n")
                log_file.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                log_file.write(f"XML File: {self.xml_file}\n")
                log_file.write(f"XSD File: {self.xsd_file}\n")
                log_file.write(f"Total Errors: {len(self.last_errors)}\n")
                log_file.write("=" * 60 + "\n\n")
                
                for i, error in enumerate(self.last_errors, 1):
                    clean_message = self.clean_error_message(error.message)
                    actual_line = getattr(error, 'line', 0)
                    
                    log_file.write(f"Error {i}:\n")
                    log_file.write(f"  Line: {actual_line}\n")
                    log_file.write(f"  Column: {getattr(error, 'column', 0)}\n")
                    log_file.write(f"  Message: {clean_message}\n")
                    if hasattr(error, 'type_name') and error.type_name:
                        log_file.write(f"  Type: {error.type_name}\n")
                    log_file.write("\n")
            
            self.log_info(f"Errors saved to log file: {log_filename}")
            QMessageBox.information(self, "Log Saved", 
                                  f"Error log saved successfully to:\n{log_filename}")
            
        except Exception as e:
            error_msg = f"Error saving log file: {str(e)}"
            self.log_error(error_msg)
            QMessageBox.critical(self, "Save Error", error_msg)
    
    def clear_displays(self):
        """Clear all display areas"""
        self.info_text.clear()
        self.error_text.clear()
        self.xml_text.clear()
        self.all_errors = []
        self.filtered_errors = []
        self.last_errors = []
        self.save_log_button.setEnabled(False)
        self.clear_search()
        self.update_status("Ready - 2581check")
        self.update_filter_panel()
    
    def log_info(self, message):
        """Log info message"""
        self.info_text.append(message)
        cursor = self.info_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.info_text.setTextCursor(cursor)
    
    def log_error(self, message):
        """Log error message"""
        self.error_text.append(message)
        cursor = self.error_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.error_text.setTextCursor(cursor)
    
    def update_status(self, message):
        """Update status bar message"""
        self.status_label.setText(message)

    def download_xsd_schema(self):
        """Download XSD schema from URL to a local file chosen by user"""
        url = self.xsd_url_entry.text().strip()
        
        if not url:
            QMessageBox.warning(self, "No URL", "Please enter a URL for the XSD schema.")
            return
        
        # Validate URL format
        if not (url.startswith('http://') or url.startswith('https://')):
            QMessageBox.warning(self, "Invalid URL", 
                              "URL must start with http:// or https://")
            return
        
        # Suggest a filename from the URL
        suggested_filename = "schema.xsd"
        try:
            url_path = url.split('/')[-1]
            if url_path and '.' in url_path:
                suggested_filename = url_path
        except:
            pass
        
        # Ask user where to save the file
        initial_dir = os.getcwd()
        if self.xsd_file and not self.xsd_is_url and os.path.exists(self.xsd_file):
            initial_dir = os.path.dirname(self.xsd_file)
        
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save XSD Schema As", 
            os.path.join(initial_dir, suggested_filename),
            "XSD files (*.xsd);;All files (*.*)")
        
        if not save_path:
            return  # User cancelled
        
        # Download the schema
        try:
            self.update_status(f"Downloading schema from {url}...")
            QApplication.processEvents()
            
            # Download with custom headers to avoid 403 errors
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            with urllib.request.urlopen(req, timeout=30) as response:
                schema_content = response.read()
            
            # Save to file
            with open(save_path, 'wb') as f:
                f.write(schema_content)
            
            # Set as current XSD file
            self.xsd_file = save_path
            self.xsd_is_url = False
            self.xsd_label.setText(os.path.basename(save_path))
            self.xsd_url_entry.clear()  # Clear URL field
            self.clear_displays()
            self.save_config()
            
            file_size = len(schema_content)
            self.log_info(f"Downloaded schema from: {url}")
            self.log_info(f"Saved to: {save_path} ({file_size:,} bytes)")
            self.update_status(f"Schema downloaded successfully ({file_size:,} bytes)")
            
            QMessageBox.information(self, "Download Successful",
                                  f"Schema downloaded successfully!\n\n"
                                  f"Size: {file_size:,} bytes\n"
                                  f"Saved to: {save_path}")
            
        except urllib.error.HTTPError as e:
            error_msg = f"HTTP Error {e.code}: {e.reason}"
            self.log_info(f"❌ Download failed: {error_msg}")
            self.update_status("Schema download failed")
            
            QMessageBox.critical(self, "Download Failed",
                               f"Failed to download schema:\n{error_msg}\n\n"
                               f"URL: {url}\n\n"
                               "The server may be blocking automated downloads (403 Forbidden).\n"
                               "Try using 'Browse URL' to manually download the file from your browser.")
            
        except urllib.error.URLError as e:
            error_msg = str(e.reason)
            self.log_info(f"❌ Download failed: {error_msg}")
            self.update_status("Schema download failed")
            
            QMessageBox.critical(self, "Download Failed",
                               f"Failed to download schema:\n{error_msg}\n\n"
                               "Please check the URL and your internet connection.")
            
        except Exception as e:
            error_msg = str(e)
            self.log_info(f"❌ Download failed: {error_msg}")
            self.update_status("Schema download failed")
            
            QMessageBox.critical(self, "Download Failed",
                               f"Unexpected error during download:\n{error_msg}")


def main():
    app = QApplication(sys.argv)
    window = XMLValidatorGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()


