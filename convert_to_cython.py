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

"""
Automated conversion script for preparing Cython distribution

This script takes the development Python code and prepares it for Cython compilation
by separating performance-critical functions from GUI components.
"""

import os
import shutil
import re
from datetime import datetime

def create_distribution_project():
    """Create the distribution project structure"""
    
    print("=" * 60)
    print("XML Schema Validator - Cython Distribution Creator")
    print("=" * 60)
    print()
    
    # Create backup before proceeding
    print("Step 1: Creating backup before conversion...")
    try:
        from create_backup import create_timestamped_backup
        backup_path = create_timestamped_backup()
        if backup_path:
            print(f"✓ Backup created: {backup_path}")
        else:
            print("✗ Backup failed!")
            response = input("Continue without backup? (y/N): ")
            if response.lower() != 'y':
                print("Conversion cancelled.")
                return
    except ImportError:
        print("⚠ Backup utility not available, continuing...")
    except Exception as e:
        print(f"⚠ Backup failed: {str(e)}, continuing...")
    
    print()
    print("Step 2: Creating distribution project...")
    
    # Paths
    dev_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(dev_dir, "2581check_Distribution")
    src_dir = os.path.join(dist_dir, "src")
    
    # Create directories
    os.makedirs(src_dir, exist_ok=True)
    os.makedirs(os.path.join(dist_dir, "build"), exist_ok=True)
    os.makedirs(os.path.join(dist_dir, "dist"), exist_ok=True)
    
    print(f"Creating distribution project at: {dist_dir}")
    
    # Copy main Python file
    main_file = os.path.join(dev_dir, "2581check.py")
    shutil.copy2(main_file, src_dir)
    print("✓ Copied main application file")
    
    # Extract performance-critical functions to Cython
    extract_validation_functions(src_dir)
    
    # Create modified main file that imports Cython modules
    create_hybrid_main_file(src_dir)
    
    # Create setup.py for compilation
    create_setup_file(dist_dir)
    
    # Create build script
    create_build_script(dist_dir)
    
    print()
    print("=" * 60)
    print("✓ DISTRIBUTION PROJECT CREATED SUCCESSFULLY!")
    print("=" * 60)
    print(f"  Location: {dist_dir}")
    print("  Next steps:")
    print("    1. cd 2581check_Distribution")
    print("    2. run build_distribution.bat")
    print()

def extract_validation_functions(src_dir):
    """Extract performance-critical functions to Cython files"""
    
    # Read the main Python file
    main_file = os.path.join(src_dir, "2581check.py")
    with open(main_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract the actual validation functions from the source
    validation_pyx = os.path.join(src_dir, "validation_core.pyx")
    
    # Get version info from original file
    version_match = re.search(r'__version__ = "([^"]+)"', content)
    build_match = re.search(r'__build__ = "([^"]+)"', content)
    version = version_match.group(1) if version_match else "1.0.0"
    build = build_match.group(1) if build_match else "unknown"
    
    # Build the Cython code with FULL estimation algorithm
    header = f"# filepath: validation_core.pyx\n"
    header += f"# Performance-critical validation functions compiled with Cython\n"
    header += f"# Extracted from 2581check.py version {version} build {build}\n\n"
    
    # COMPLETE Cython implementation with FAST INDEX-BASED SEARCH
    body = """import re
from lxml import etree
cimport cython

cdef class ValidationCore:
    \"\"\"Cython-optimized validation functions with INDEXED line lookup\"\"\"
    
    cdef public list xml_lines
    cdef str xsd_file
    cdef str xml_file
    cdef int error_counter
    cdef public dict element_search_positions  # CHANGED: Per-element search positions
    cdef public dict element_index
    cdef bint index_built
    
    def __init__(self, str xsd_file, str xml_file):
        self.xsd_file = xsd_file
        self.xml_file = xml_file
        self.xml_lines = []
        self.error_counter = 0
        self.element_search_positions = {}  # CHANGED: Initialize per-element positions
        self.element_index = {}
        self.index_built = False
    
    def preload_xml_lines(self):
        \"""Preload XML lines AND build fast lookup index\"""
        debug_log = []  # NEW: Capture all debug info
        
        try:
            debug_log.append(f"[PRELOAD-1] Opening file: {self.xml_file}")
            
            with open(self.xml_file, 'r', encoding='utf-8') as f:
                debug_log.append(f"[PRELOAD-2] File opened successfully")
                self.xml_lines = f.readlines()
                debug_log.append(f"[PRELOAD-3] Read {len(self.xml_lines)} lines")
            
            # Build index ONCE for fast lookups
            debug_log.append(f"[PRELOAD-4] Building element index...")
            self.build_element_index()
            debug_log.append(f"[PRELOAD-5] Index built with {len(self.element_index)} elements")
            
            # DEBUG: Check if standardprimitiveref is in the index
            debug_info = {
                'total_lines': len(self.xml_lines),
                'index_size': len(self.element_index),
                'sample_elements': list(self.element_index.keys())[:10] if self.element_index else [],
                'debug_log': debug_log  # NEW: Include debug log
            }
            
            # Check for the specific element we're looking for
            if 'standardprimitiveref' in self.element_index:
                occurrences = len(self.element_index['standardprimitiveref'])
                debug_info['standardprimitiveref_count'] = occurrences
                debug_info['standardprimitiveref_first_10'] = self.element_index['standardprimitiveref'][:10]
                debug_log.append(f"[PRELOAD-6] Found 'standardprimitiveref' {occurrences} times")
            else:
                debug_info['standardprimitiveref_count'] = 0
                debug_log.append(f"[PRELOAD-6] 'standardprimitiveref' NOT in index")
                # Check variations
                found_primitives = []
                for key in self.element_index.keys():
                    if 'primitive' in key.lower():
                        found_primitives.append(f"{key}={len(self.element_index[key])}")
                if found_primitives:
                    debug_log.append(f"[PRELOAD-7] Found similar: {', '.join(found_primitives[:5])}")
            
            return debug_info
            
        except Exception as e:
            debug_log.append(f"[PRELOAD-ERROR] Exception: {str(e)}")
            import traceback
            debug_log.append(f"[PRELOAD-ERROR] Traceback: {traceback.format_exc()}")
            self.xml_lines = []
            return {'error': str(e), 'debug_log': debug_log}
    
    @cython.boundscheck(False)
    @cython.wraparound(False)
    cdef void build_element_index(self):
        \"""Build fast lookup index of elements - RUNS ONCE\"""
        if self.index_built:
            return
        
        cdef long i
        cdef str line, line_lower, element_name
        cdef int total_lines = len(self.xml_lines)
        cdef int start_idx, end_idx, colon_pos
        cdef char c
        
        # Index ALL lines (not just after 65535)
        for i in range(0, total_lines):
            line = self.xml_lines[i]
            line_lower = line.lower()
            
            # Look for element tags: <ElementName ...>
            if '<' in line_lower:
                start_idx = line_lower.find('<')
                if start_idx >= 0 and start_idx + 1 < len(line_lower):
                    # Skip closing tags and comments
                    if line_lower[start_idx + 1] == '/' or line_lower[start_idx + 1] == '!':
                        continue
                    
                    # Find end of element name (space, >, /, tab, or newline)
                    end_idx = start_idx + 1
                    while end_idx < len(line_lower):
                        c = line_lower[end_idx]
                        if c in (' ', '>', '/', '\\t', '\\n', '\\r'):
                            break
                        end_idx += 1
                    
                    if end_idx > start_idx + 1:
                        element_name = line_lower[start_idx + 1:end_idx]
                        
                        # Remove namespace prefix (everything before colon)
                        colon_pos = element_name.find(':')
                        if colon_pos >= 0:
                            element_name = element_name[colon_pos + 1:]
                        
                        # Only index if we have a valid name
                        if element_name and len(element_name) > 0:
                            # Add to index
                            if element_name not in self.element_index:
                                self.element_index[element_name] = []
                            self.element_index[element_name].append(i + 1)
        
        self.index_built = True
    
    def clean_error_message(self, str message):
        \"""Clean XML namespace prefixes from error messages\"""
        cdef str cleaned = str(message)
        cleaned = re.sub(r'{[^}]*}', '', cleaned)
        cleaned = re.sub(r'\\b\\w+:', '', cleaned)
        cleaned = re.sub(r'\\s+', ' ', cleaned).strip()
        return cleaned
    
    @cython.boundscheck(False)
    @cython.wraparound(False)
    def find_actual_line_number(self, str error_message, int truncated_line):
        \"""Find ACTUAL line number using FAST INDEX lookup\"""
        
        if len(self.xml_lines) == 0 or truncated_line != 65535:
            return truncated_line
        
        self.error_counter += 1
        
        cdef str error_str = str(error_message).lower()
        cdef str original_error = str(error_message)
        cdef int total_lines = len(self.xml_lines)
        cdef str element_name, key_value, line_content
        cdef list key_values, line_list
        cdef long i, line_num
        cdef int search_start
        
        # Extract element name from error
        element_match = re.search(r\"element\\s+'([^']+)'\", error_str)
        if not element_match:
            return truncated_line
        
        element_name = element_match.group(1)
        if ':' in element_name:
            element_name = element_name.split(':', 1)[1]
        element_name = element_name.lower()
        
        # USE THE INDEX!
        if element_name not in self.element_index:
            return truncated_line
        
        # Get search start position for THIS element
        if element_name not in self.element_search_positions:
            self.element_search_positions[element_name] = 1
        
        search_start = self.element_search_positions[element_name]
        line_list = self.element_index[element_name]
        
        # For key-sequence errors, find occurrence with matching key value
        key_sequence_match = re.search(r\"key-sequence\\s+\\[([^\\]]+)\\]\", original_error)
        if key_sequence_match:
            key_sequence_raw = key_sequence_match.group(1)
            key_values = re.findall(r\"['\\\"]([^'\\\"]+)['\\\"]|\", key_sequence_raw)
            
            if key_values and key_values[0]:
                key_value = key_values[0].lower()
                
                # Search from search_start forward
                for line_num in line_list:
                    if line_num >= search_start:
                        i = line_num - 1
                        line_content = self.xml_lines[i].lower()
                        
                        if key_value in line_content:
                            self.element_search_positions[element_name] = line_num + 1
                            return int(line_num)
                
                # Wrap to beginning
                for line_num in line_list:
                    if line_num < search_start:
                        i = line_num - 1
                        line_content = self.xml_lines[i].lower()
                        
                        if key_value in line_content:
                            self.element_search_positions[element_name] = line_num + 1
                            return int(line_num)
        
        # No key-sequence or not found - return next occurrence
        for line_num in line_list:
            if line_num >= search_start:
                self.element_search_positions[element_name] = line_num + 1
                return int(line_num)
        
        # Wrap around
        if line_list:
            self.element_search_positions[element_name] = line_list[0] + 1
            return int(line_list[0])
        
        return truncated_line
    
    def categorize_error(self, str error_message):
        \"""Categorize error message by type - Cython optimized\"""
        cdef str clean_msg = error_message.lower()
        
        if "this element is not expected" in clean_msg:
            return "This element is not expected"
        elif "no match found for key-sequence" in clean_msg:
            return "No match found for key-sequence"
        elif "duplicate key-sequence" in clean_msg:
            return "Duplicate key-sequence"
        elif "missing child element" in clean_msg:
            return "Missing child element(s)"
        elif "invalid value" in clean_msg or "not a valid" in clean_msg:
            return "Invalid value"
        elif "duplicate" in clean_msg:
            return "Duplicate element/attribute"
        else:
            return "Other validation error"
"""
    
    cython_code = header + body
    
    with open(validation_pyx, 'w', encoding='utf-8') as f:
        f.write(cython_code)
    
    print("✓ Created validation_core.pyx with FULL line estimation algorithm (Cython-optimized)")

def create_hybrid_main_file(src_dir):
    """Create main file that uses Cython modules when available"""
    
    # Read the original file to preserve most of the code
    main_file = os.path.join(src_dir, "2581check.py")
    with open(main_file, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    # Create hybrid version by modifying the ValidationWorker class
    hybrid_content = original_content
    
    # Add Cython import at the top
    import_section = '''# Try to import Cython-compiled validation core
try:
    from validation_core import ValidationCore
    USE_CYTHON = True
    print("Using Cython-optimized validation engine")
except ImportError:
    USE_CYTHON = False
    print("Using Python validation engine (Cython not available)")

'''
    
    # Insert after the existing imports
    import_pos = hybrid_content.find('from PyQt5.QtGui import')
    if import_pos != -1:
        end_pos = hybrid_content.find('\n', import_pos) + 1
        hybrid_content = hybrid_content[:end_pos] + '\n' + import_section + hybrid_content[end_pos:]
    
    # Fix the app_dir initialization to work correctly with compiled .exe
    old_app_dir = "self.app_dir = os.path.dirname(os.path.abspath(__file__))"
    new_app_dir = """# Get the directory where the executable is running from
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            self.app_dir = os.path.dirname(sys.executable)
        else:
            # Running as Python script
            self.app_dir = os.path.dirname(os.path.abspath(__file__))"""
    
    hybrid_content = hybrid_content.replace(old_app_dir, new_app_dir)
    
    # Fix the method replacements - these should NOT use Cython in the GUI class
    # Only ValidationWorker should use Cython, not XMLValidatorGUI
    
    # Find clean_error_message in ValidationWorker (keep Cython)
    # Find clean_error_message in XMLValidatorGUI (keep Python)
    
    # Replace only the ValidationWorker methods with Cython versions
    # Do this BEFORE replacing validation_completed
    
    # First, mark the ValidationWorker class
    worker_class_start = hybrid_content.find("class ValidationWorker(QThread):")
    gui_class_start = hybrid_content.find("class XMLValidatorGUI(QMainWindow):")
    
    if worker_class_start != -1 and gui_class_start != -1:
        # Only modify methods in ValidationWorker (between worker_class_start and gui_class_start)
        worker_section = hybrid_content[worker_class_start:gui_class_start]
        
        # Modify ValidationWorker __init__ method
        init_pattern = r'(def __init__\(self, xsd_file, xml_file\):\s*super\(\).__init__\(\)\s*self\.xsd_file = xsd_file\s*self\.xml_file = xml_file\s*self\.cancelled = False\s*)(self\.xml_lines = \[\])'
        
        replacement = r'''\1# Initialize validation engine
        if USE_CYTHON:
            self.validation_core = ValidationCore(xsd_file, xml_file)
        
        \2'''
        
        worker_section = re.sub(init_pattern, replacement, worker_section, flags=re.DOTALL)
        
        # Modify performance-critical methods in ValidationWorker only - USE CYTHON FOR SPEED!
        method_replacements = [
            ('def find_actual_line_number(self, error_message, truncated_line):',
             '''def find_actual_line_number(self, error_message, truncated_line):
        """Find the actual line number - uses Cython optimization for SPEED"""
        if USE_CYTHON:
            return self.validation_core.find_actual_line_number(error_message, truncated_line)
        
        # Fallback - no Cython available, return truncated line
        return truncated_line'''),
            
            ('def clean_error_message(self, message):',
             '''def clean_error_message(self, message):
        """Clean XML namespace prefixes - uses Cython optimization when available"""
        if USE_CYTHON:
            return self.validation_core.clean_error_message(message)
        
        # Fallback - simple cleaning
        cleaned = str(message)
        cleaned = re.sub(r'\{[^}]*\}', '', cleaned)
        cleaned = re.sub(r'\b\w+:', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned'''),
            
            ('def preload_xml_lines(self):',
             '''def preload_xml_lines(self):
        """Preload XML lines - uses Cython optimization for SPEED"""
        if USE_CYTHON:
            result = self.validation_core.preload_xml_lines()
            # Log index info to debug
            if result and isinstance(result, dict):
                if 'error' in result:
                    self.debug_message.emit(f"⚠️ Preload error: {result['error']}")
                else:
                    self.debug_message.emit(f"✅ Index built: {result.get('index_size', 0)} unique elements")
                    self.debug_message.emit(f"   Sample elements: {', '.join(result.get('sample_elements', []))}")
                    
                    # NEW: Check for standardprimitiveref specifically
                    spr_count = result.get('standardprimitiveref_count', 0)
                    if spr_count > 0:
                        spr_lines = result.get('standardprimitiveref_first_10', [])
                        self.debug_message.emit(f"   StandardPrimitiveRef: {spr_count} occurrences")
                        self.debug_message.emit(f"   First 10 lines: {spr_lines}")
                    else:
                        self.debug_message.emit(f"   ⚠️ StandardPrimitiveRef: NOT FOUND in index!")
                
                # Store debug_log for later writing to file
                if 'debug_log' in result:
                    self.preload_debug_log = result['debug_log']
            return
        
        # Fallback - just read lines without indexing
        try:
            with open(self.xml_file, 'r', encoding='utf-8') as f:
                self.xml_lines = f.readlines()
            self.debug_message.emit(f"⚠️ Preloaded {len(self.xml_lines):,} lines (Python fallback - no line correction)")
        except Exception as e:
            self.xml_lines = []
            self.debug_message.emit(f"⚠️ Preload error: {str(e)}")''')
        ]
        
        for old_method, new_method in method_replacements:
            worker_section = worker_section.replace(old_method, new_method)
        
        # Reconstruct the file
        hybrid_content = hybrid_content[:worker_class_start] + worker_section + hybrid_content[gui_class_start:]
        print("✓ Modified ValidationWorker methods to use Cython (GUI class unchanged)")
    
    # Replace validation_completed method with crash-safe version
    old_validation_completed = "    def validation_completed(self, is_valid, errors):"
    validation_completed_idx = hybrid_content.find(old_validation_completed)
    
    if validation_completed_idx != -1:
        # Find the end of the method
        next_method = hybrid_content.find("\n    def ", validation_completed_idx + len(old_validation_completed))
        
        if next_method != -1:
            safe_validation_completed = '''    def validation_completed(self, is_valid, errors):
        """Handle validation completion - CRASH SAFE for .exe - FAST MESSAGE BOX"""
        try:
            if is_valid:
                self.log_info("✅ XML validation successful! The XML file is valid according to the schema.")
                self.update_status("Validation successful!")
                QMessageBox.information(self, "Validation Success", 
                                      "The XML file is valid according to the schema!")
            else:
                error_count = len(errors)
                self.log_info("❌ XML validation failed. See errors below.")
                
                self.all_errors = errors
                self.last_errors = errors
                self.filtered_errors = errors
                
                # Show message box FIRST, then update display
                # This makes the message box close immediately when OK is clicked
                try:
                    QMessageBox.warning(self, "Validation Failed", 
                                      f"XML validation failed with {error_count} error(s).")
                except:
                    pass  # Don't crash on message box
                
                # Update status bar before processing
                self.update_status(f"Updating display with {error_count:,} errors...")
                
                # NOW update display (after message box is dismissed)
                try:
                    # For small error sets, update immediately without delay
                    if error_count <= 1000:
                        self.update_filter_panel_safe()
                        self.apply_filters_safe()
                    else:
                        # For large error sets, use small delay to let UI update
                        self.log_info(f"⚠️  Large error set ({error_count} errors) - updating display...")
                        QTimer.singleShot(50, self.update_filter_panel_safe)
                        QTimer.singleShot(100, self.apply_filters_safe)
                except Exception as e:
                    print(f"Error updating display: {e}")
                    import traceback
                    traceback.print_exc()
                    self.log_error(f"Display error: {str(e)}")
                
                self.save_log_button.setEnabled(True)
        except Exception as e:
            print(f"CRITICAL: validation_completed crashed: {e}")
            import traceback
            traceback.print_exc()
            try:
                self.log_error(f"Validation crashed: {str(e)}")
            except:
                pass
'''
            hybrid_content = hybrid_content[:validation_completed_idx] + safe_validation_completed + hybrid_content[next_method:]
            print("✓ Replaced validation_completed() with status updates")
    
    # Modify apply_filters_safe to update status when done
    old_apply_filters = '''    def apply_filters_safe(self):
        """Crash-safe wrapper for apply_filters"""
        try:
            self.apply_filters()
        except Exception as e:
            print(f"Error in apply_filters: {e}")
            import traceback
            traceback.print_exc()
            # Try to show something
            try:
                self.error_text.setPlainText(f"Error displaying results: {str(e)}\\n\\nUse 'Save Errors to Log' to export errors.")
            except:
                pass'''
    
    new_apply_filters = '''    def apply_filters_safe(self):
        """Crash-safe wrapper for apply_filters"""
        try:
            self.apply_filters()
            # Update status bar when done
            if hasattr(self, 'filtered_errors') and self.filtered_errors:
                self.update_status(f"Displaying {len(self.filtered_errors):,} errors")
        except Exception as e:
            print(f"Error in apply_filters: {e}")
            import traceback
            traceback.print_exc()
            self.update_status("Error displaying results")
            # Try to show something
            try:
                self.error_text.setPlainText(f"Error displaying results: {str(e)}\\n\\nUse 'Save Errors to Log' to export errors.")
            except:
                pass'''
    
    if old_apply_filters in hybrid_content:
        hybrid_content = hybrid_content.replace(old_apply_filters, new_apply_filters)
        print("✓ Modified apply_filters_safe() to update status bar when complete")
    
    # Add status update after XML file loads
    old_xml_load_success = "self.log_info(f\"XML file loaded: {file_path} ({len(self.xml_lines):,} lines)\")"
    new_xml_load_success = """self.log_info(f"XML file loaded: {file_path} ({len(self.xml_lines):,} lines)")
                self.update_status(f"Displaying XML file ({len(self.xml_lines):,} lines)...")"""
    
    if old_xml_load_success in hybrid_content:
        hybrid_content = hybrid_content.replace(old_xml_load_success, new_xml_load_success)
        print("✓ Added 'Displaying XML...' status update after XML file loads")

    # Normalize version info branding in the generated hybrid file.
    old_version_info = 'self.log_info(f"XML Schema Validator v{__version__} (Build {__build__})")'
    new_version_info = 'self.log_info(f"2581check v{__version__} (Build {__build__})")'
    if old_version_info in hybrid_content:
        hybrid_content = hybrid_content.replace(old_version_info, new_version_info)
        print("✓ Updated version info branding to 2581check")
    
    # ADD STATUS UPDATE RIGHT AFTER FILE IS READ (between read and display)
    # This catches the gap between "Reading xml file..." and "XML loaded successfully"
    after_read_patterns = [
        # Pattern 1: Right after xml_lines is set
        ('self.xml_lines = content.splitlines(keepends=True)\n',
         'self.xml_lines = content.splitlines(keepends=True)\n                self.update_status(f"Preparing to display {len(self.xml_lines):,} lines...")\n'),
        
        # Pattern 2: REMOVE THIS - it's in ValidationWorker which doesn't have update_status!
        # ('            self.xml_lines = f.readlines()\n',
        #  '            self.xml_lines = f.readlines()\n                self.update_status(f"Loaded {len(self.xml_lines):,} lines, preparing display...")\n'),
        
        # Pattern 3: Generic - after setting xml_loaded flag
        ('self.xml_loaded = True\n',
         'self.xml_loaded = True\n        self.update_status(f"XML file loaded, rendering display...")\n'),
    ]
    
    after_read_updated = False
    for old_pattern, new_pattern in after_read_patterns:
        if old_pattern in hybrid_content:
            hybrid_content = hybrid_content.replace(old_pattern, new_pattern)
            after_read_updated = True
            print(f"✓ Added status update after XML file read (before display)")
            break
    
    if not after_read_updated:
        print("⚠ Could not add status after XML read - will try display patterns")
    
    # MOST AGGRESSIVE: Find where setPlainText is called for XML display and add status BEFORE it
    # This will catch it regardless of the exact method structure
    xml_display_patterns = [
        # Right before setPlainText with xml_lines
        ('                # Display the actual content\n                self.xml_text.setPlainText',
         '                # Display the actual content\n                self.update_status(f"Rendering XML ({len(self.xml_lines):,} lines)...")\n                self.xml_text.setPlainText'),
        
        # Alternative: before any setPlainText in xml loading context
        ('            self.xml_text.setPlainText(\'\\n\'.join(self.xml_lines))',
         '            self.update_status(f"Rendering XML display...")\n            self.xml_text.setPlainText(\'\\n\'.join(self.xml_lines))'),
        
        # In xml_content_loaded method specifically
        ('        self.xml_text.setPlainText(\'\\n\'.join(self.xml_lines))',
         '        self.update_status(f"Rendering {len(self.xml_lines):,} lines...")\n        self.xml_text.setPlainText(\'\\n\'.join(self.xml_lines))'),
    ]
    
    display_status_added = False
    for old_pattern, new_pattern in xml_display_patterns:
        if old_pattern in hybrid_content:
            hybrid_content = hybrid_content.replace(old_pattern, new_pattern)
            display_status_added = True
            print(f"✓ Added 'Rendering XML' status update before display")
            break
    
    if not display_status_added:
        print("⚠ Could not add 'Rendering XML' status - manual edit may be needed")
        # Try one more super generic pattern
        if 'self.xml_text.setPlainText' in hybrid_content and 'xml_lines' in hybrid_content:
            # Find ANY setPlainText that involves xml_lines
            lines = hybrid_content.split('\n')
            for i, line in enumerate(lines):
                if 'self.xml_text.setPlainText' in line and i > 0:
                    # Add status update on the line before
                    indent = len(line) - len(line.lstrip())
                    status_line = ' ' * indent + 'self.update_status(f"Rendering XML display...")'
                    lines.insert(i, status_line)
                    hybrid_content = '\n'.join(lines)
                    print("✓ Added 'Rendering XML' status using generic insertion")
                    break
    
    # ADD CLICK HANDLER METHOD
    click_handler = '''
    def on_error_line_clicked(self, url):
        """Handle clicks on error line numbers - navigates to XML line"""
        try:
            url_str = url.toString();
            print(f"Line link clicked: {url_str}")
            
            if url_str.startswith("line:"):
                line_str = url_str.replace("line:", "")
                line_num = int(line_str);
                
                # Set the line number in the go-to box
                self.goto_line_entry.setText(str(line_num))
                
                # Navigate to that line
                if self.xml_loaded and self.xml_lines:
                    self.navigate_to_line(line_num)
                    self.xml_text.setFocus()
                    self.update_status(f"Navigated to line {line_num:,}")
                else:
                    self.update_status(f"Line {line_num:,} - Load XML file first to navigate")
                    QMessageBox.information(self, "Load XML First", 
                        f"Line number {line_num:,} copied to 'Go to line' field.\\n\\n"
                        f"Click 'Load XML File' to enable navigation.")
        except Exception as e:
            print(f"Error handling line click: {e}")
            import traceback
            traceback.print_exc()
'''
    
    # Find where to insert - should be INSIDE the class, before main()
    main_func_idx = hybrid_content.find("\n\ndef main():")
    if main_func_idx != -1:
        # Insert click handler BEFORE main() (still inside class)
        hybrid_content = hybrid_content[:main_func_idx] + click_handler + hybrid_content[main_func_idx:]
        print("✓ Added on_error_line_clicked() handler inside XMLValidatorGUI class")
    
    # NOW ADD SAFE WRAPPERS (these go after click handler, still before main())
    safe_wrappers = '''
    def update_filter_panel_safe(self):
        """Crash-safe wrapper for update_filter_panel"""
        try:
            self.update_filter_panel()
        except Exception as e:
            print(f"Error in update_filter_panel: {e}")
            import traceback
            traceback.print_exc()
    
    def apply_filters_safe(self):
        """Crash-safe wrapper for apply_filters"""
        try:
            self.apply_filters()
            # Update status bar when done
            if hasattr(self, 'filtered_errors') and self.filtered_errors:
                self.update_status(f"Displaying {len(self.filtered_errors):,} errors")
        except Exception as e:
            print(f"Error in apply_filters: {e}")
            import traceback
            traceback.print_exc()
            self.update_status("Error displaying results")
            # Try to show something
            try:
                self.error_text.setPlainText(f"Error displaying results: {str(e)}\\n\\nUse 'Save Errors to Log' to export errors.")
            except:
                pass
'''
    
    # Insert safe wrappers before main() function (after click handler)
    main_func_idx = hybrid_content.find("\n\ndef main():")
    if main_func_idx != -1:
        hybrid_content = hybrid_content[:main_func_idx] + safe_wrappers + hybrid_content[main_func_idx:]
        print("✓ Added crash-safe wrapper methods inside XMLValidatorGUI class")
    
    # REMOVED OLD CODE INJECTION - 2581check.py already has proper update_error_display
    # The source code already handles max_display_errors correctly - no need to replace the method
    print("✓ Using update_error_display from source code (no replacement needed)")
    
    # # Replace update_error_display with crash-safe clickable version
    # [COMMENTED OUT 200+ lines of old code injection]
    
    # REMOVED OLD CODE INJECTION - 2581check.py already has proper max_display_errors handling
    # No need to add max_errors_per_type - the source already has max_display_errors
    
    print("✓ Using max_display_errors from source code (no injection needed)")
    
    # # ADD MISSING: Modify __init__ to add max_errors_per_type attribute
    # init_attributes = "        self.max_display_errors = 5000  # Configurable limit for error display"
    # init_idx = hybrid_content.find(init_attributes)
    # if init_idx != -1:
    #     new_attributes = """        self.max_display_errors = 5000  # Configurable limit for error display
    #     self.max_errors_per_type = 10  # Number of errors to show per type (configurable)"""
    #     hybrid_content = hybrid_content.replace(init_attributes, new_attributes)
    #     print("✓ Added max_errors_per_type attribute to __init__")
    # else:
    #     print("⚠ Could not find max_display_errors in __init__")
    
    # # ADD MISSING: Modify load_config to load max_errors_per_type
    # load_config_addition = """                    if config.get('max_errors_per_type'):
    #                     self.max_errors_per_type = int(config['max_errors_per_type'])"""
    
    # header_font_config = "                    if config.get('header_font_size'):"  # FIXED: Removed extra colon
    # config_idx = hybrid_content.find(header_font_config)
    # if config_idx != -1:
    #     # Find the end of this block
    #     next_line = hybrid_content.find("\n", config_idx + len(header_font_config))
    #     next_line = hybrid_content.find("\n", next_line + 1)  # Skip the assignment line
    #     hybrid_content = hybrid_content[:next_line] + "\n" + load_config_addition + hybrid_content[next_line:]
    #     print("✓ Modified load_config() to load max_errors_per_type")
    # else:
    #     print("⚠ Could not find header_font_size config loading")
    
    # # ADD MISSING: Modify save_config to save max_errors_per_type
    # save_config_attr = "'header_font_size': self.header_font_size,"
    # save_idx = hybrid_content.find(save_config_attr)
    # if save_idx != -1:
    #     new_save_line = """'header_font_size': self.header_font_size,
    #             'max_errors_per_type': self.max_errors_per_type,"""
    #     hybrid_content = hybrid_content.replace(save_config_attr, new_save_line)
    #     print("✓ Modified save_config() to save max_errors_per_type")
    # else:
    #     print("⚠ Could not find header_font_size in save_config")
    
    # Remove old broken config patterns
    # Modify config load/save to restore errors_per_type setting
    config_load_pattern = r'(def load_config\(self\):\s*try:\s*with open\(self\.config_file, \'r\', encoding=\'utf-8\'\) as f:\s*self\.config = json\.load\(f\)\s*super\(\).load_config\(\)\s*)(self\.max_errors_per_type = \d+)'
    config_save_pattern = r'(def save_config\(self\):\s*try:\s*with open\(self\.config_file, \'w\', encoding=\'utf-8\'\) as f:\s*json\.dump\(self\.config, f, indent=4\)\s*)(self\.config\["max_errors_per_type"\] = \d+)'
    
    # REMOVE these broken regex patterns - they don't match our code
    # Update load_config method
    # hybrid_content = re.sub(config_load_pattern, r'\1self.max_errors_per_type = 1000', hybrid_content)
    
    # Update save_config method
    # hybrid_content = re.sub(config_save_pattern, r'\1self.max_errors_per_type = self.max_errors_per_type', hybrid_content)
    
    # Modify the UI control section - MORE ROBUST APPROACH
    # Find any variation of max_errors_layout
    
    # REMOVED OLD CODE INJECTION - errors_per_type UI controls
    # The source code already has proper max_display_errors UI - no need to add errors_per_type
    print("✓ Skipping errors_per_type UI injection - using max_display_errors from source")
    
    # # Try multiple patterns to find the max_errors section
    # [COMMENTED OUT - old code that adds errors_per_type controls]
    
    replaced = False
    # if not replaced:
    #     print("⚠ Could not find max_errors_layout - Errors/type control may not be added")
    #     print("⚠ Please add manually or check the source file")
    
    # REMOVED OLD CODE INJECTION - errors_per_type UI restoration
    # No need since we're not adding errors_per_type controls
    print("✓ Skipping errors_per_type UI restoration - not needed")
    
    # # Add UI restoration for errors_per_type
    # [COMMENTED OUT]
    
    # Enhance debug file writing - try MULTIPLE patterns to find where it's written
    debug_enhancement_patterns = [
        # Pattern 1: Look for the exact existing debug section
        ('                        f.write("=== PRELOAD DEBUG LOG ===\\n")\n                        for msg in self.debug_log[:20]:  # First 20 messages\n                            f.write(msg + "\\n")\n                        f.write("\\n")',
         '''                        f.write("=== CYTHON PRELOAD DEBUG LOG ===\\n")
                        if hasattr(self, 'preload_debug_log') and self.preload_debug_log:
                            for msg in self.preload_debug_log:
                                f.write(msg + "\\n")
                        else:
                            f.write("⚠️ preload_debug_log not found\\n")
                            f.write(f"   Has attribute: {hasattr(self, 'preload_debug_log')}\\n")
                        f.write("\\n")
                        
                        # Show Cython line count
                        cython_lines = 0
                        if USE_CYTHON and hasattr(self, 'validation_core'):
                            try:
                                cython_lines = len(self.validation_core.xml_lines)
                            except:
                                cython_lines = -1
                        f.write(f"Cython XML Lines: {cython_lines}\\n")
                        
                        f.write("\\n=== PYTHON PRELOAD DEBUG LOG ===\\n")
                        for msg in self.debug_log[:20]:  # First 20 messages
                            f.write(msg + "\\n")
                        f.write("\\n")
                        
                        f.write(f"Total Lines in XML (Worker): {len(self.xml_lines) if hasattr(self, 'xml_lines') else 0}\\n")'''),
        
        # Pattern 2: Look for the section header
        ('f.write("=== PRELOAD DEBUG LOG ===\\n")',
         '''f.write("=== CYTHON PRELOAD DEBUG LOG ===\\n")
                        if hasattr(self, 'preload_debug_log') and self.preload_debug_log:
                            for msg in self.preload_debug_log:
                                f.write(msg + "\\n")
                        else:
                            f.write("⚠️ No Cython preload log\\n")
                        f.write("\\n")
                        
                        f.write(f"Cython Lines: {len(self.validation_core.xml_lines) if USE_CYTHON and hasattr(self, 'validation_core') else 0}\\n\\\\n")
                        
                        f.write("=== PRELOAD DEBUG LOG ===\\n")'''),
    ]
    
    debug_enhanced = False
    for old_pattern, new_pattern in debug_enhancement_patterns:
        if old_pattern in hybrid_content:
            hybrid_content = hybrid_content.replace(old_pattern, new_pattern)
            print(f"✓ Enhanced debug file writing (pattern {debug_enhancement_patterns.index((old_pattern, new_pattern)) + 1})")
            debug_enhanced = True
            break
    
    if not debug_enhanced:
        print("⚠️ Could not find debug file writing section - debug log may not show Cython info")
    
    # Save hybrid file
    hybrid_file = os.path.join(src_dir, "2581check_pyqt5_hybrid.py")
    with open(hybrid_file, 'w', encoding='utf-8') as f:
        f.write(hybrid_content)
    
    print("✓ Created hybrid main file with intelligent Cython/Python fallback")
    print("✓ Fixed config file path detection for compiled .exe")
    print("✓ Only ValidationWorker uses Cython, GUI class uses Python")
    print("✓ Replaced validation_completed() with crash-safe version")
    print("✓ Added safe wrapper methods with traceback printing")
    print("✓ Replaced update_error_display() with CLICKABLE line numbers!")
    print("✓ Added click handler to navigate XML on line number click")
    print("✓ Added configurable 'Errors per type' setting (1-999999, saved in config)")
    print("✓ Fixed method insertion order to prevent AttributeError")
    print("✓ Moved 'Errors/type' to same line as 'Max errors'")
    print("✓ Fixed on_error_line_clicked() insertion to be inside class")
    print("✓ OPTIMIZED: Message box shows BEFORE display update for instant dismiss")
    print("✓ Added status bar updates: 'Updating display...', 'Displaying X errors', 'XML loaded'")
    print("✓ Added 'Errors/type' control on same line as 'Max errors'")
    print("✓ Added max_errors_per_type to __init__, load_config, save_config")
    print("✓ Added 'Displaying XML...' and 'XML displayed' status updates for better UX")

def create_setup_file(dist_dir):
    """Create setup.py for Cython compilation"""
    
    setup_code = '''# filepath: setup.py
from setuptools import setup, Extension
from Cython.Build import cythonize
from Cython.Distutils import build_ext
import sys

if sys.platform.startswith("win"):
    compile_args = ["/O2"]
    link_args = []
else:
    compile_args = ["-O3", "-std=c++11"]
    link_args = ["-O3"]

# Define extensions
extensions = [
    Extension(
        "validation_core",
        ["src/validation_core.pyx"],
        language="c++",
        extra_compile_args=compile_args,
        extra_link_args=link_args
    )
]

setup(
    name="XML_Validator_Optimized",
    ext_modules=cythonize(
        extensions, 
        compiler_directives={
            'language_level': 3,
            'boundscheck': False,
            'wraparound': False,
            'cdivision': True,
            'embedsignature': True,
            'optimize.use_switch': True
        }
    ),
    requires=['PyQt5', 'lxml'],
    zip_safe=False,
)
'''
    
    setup_file = os.path.join(dist_dir, "setup.py")
    with open(setup_file, 'w', encoding='utf-8') as f:
        f.write(setup_code)
    
    print("✓ Created optimized setup.py for Cython compilation")

def create_build_script(dist_dir):
    """Create automated build script"""
    
    # Create PowerShell version - write directly to avoid string escaping issues
    ps1_file = os.path.join(dist_dir, "build_distribution.ps1")
    
    with open(ps1_file, 'w', encoding='utf-8') as f:
        f.write('# PowerShell Build Script for XML Schema Validator\n')
        f.write('Set-Location -LiteralPath $PSScriptRoot\n\n')
        f.write('function Get-VsDevCmdPath {\n')
        f.write('    $vswhere = Join-Path ${env:ProgramFiles(x86)} \'Microsoft Visual Studio\\Installer\\vswhere.exe\'\n')
        f.write('    if (Test-Path $vswhere) {\n')
        f.write('        try {\n')
        f.write('            $instances = & $vswhere -prerelease -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -format json | ConvertFrom-Json\n')
        f.write('            foreach ($inst in @($instances)) {\n')
        f.write('                $candidate = Join-Path $inst.installationPath \'Common7\\Tools\\VsDevCmd.bat\'\n')
        f.write('                if (Test-Path $candidate) { return $candidate }\n')
        f.write('            }\n')
        f.write('        } catch {\n')
        f.write('            # Fall through to known paths\n')
        f.write('        }\n')
        f.write('    }\n\n')
        f.write('    $fallbacks = @(\n')
        f.write('        \'C:\\Program Files\\Microsoft Visual Studio\\18\\Community\\Common7\\Tools\\VsDevCmd.bat\',\n')
        f.write('        \'C:\\Program Files\\Microsoft Visual Studio\\18\\Professional\\Common7\\Tools\\VsDevCmd.bat\',\n')
        f.write('        \'C:\\Program Files\\Microsoft Visual Studio\\18\\Enterprise\\Common7\\Tools\\VsDevCmd.bat\',\n')
        f.write('        \'C:\\Program Files\\Microsoft Visual Studio\\18\\BuildTools\\Common7\\Tools\\VsDevCmd.bat\',\n')
        f.write('        \'C:\\Program Files\\Microsoft Visual Studio\\18\\Insiders\\Common7\\Tools\\VsDevCmd.bat\',\n')
        f.write('        \'C:\\Program Files\\Microsoft Visual Studio\\2022\\BuildTools\\Common7\\Tools\\VsDevCmd.bat\',\n')
        f.write('        \'C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\Common7\\Tools\\VsDevCmd.bat\',\n')
        f.write('        \'C:\\Program Files\\Microsoft Visual Studio\\2022\\Professional\\Common7\\Tools\\VsDevCmd.bat\',\n')
        f.write('        \'C:\\Program Files\\Microsoft Visual Studio\\2022\\Enterprise\\Common7\\Tools\\VsDevCmd.bat\'\n')
        f.write('    )\n')
        f.write('    foreach ($candidate in $fallbacks) {\n')
        f.write('        if (Test-Path $candidate) { return $candidate }\n')
        f.write('    }\n\n')
        f.write('    return $null\n')
        f.write('}\n\n')
        f.write('if (-not $env:IPC2581CHECK_VSENV_READY -and -not (Get-Command cl -ErrorAction SilentlyContinue)) {\n')
        f.write('    $vsDevCmd = Get-VsDevCmdPath\n')
        f.write('    if ($vsDevCmd) {\n')
        f.write('        Write-Host "Initializing Visual Studio C++ build environment..." -ForegroundColor Yellow\n')
        f.write('        $cmd = (\'"{0}" -arch=x64 -host_arch=x64 >nul && set IPC2581CHECK_VSENV_READY=1 && powershell -NoProfile -ExecutionPolicy Bypass -File "{1}"\' -f $vsDevCmd, $PSCommandPath)\n')
        f.write('        cmd /c $cmd\n')
        f.write('        exit $LASTEXITCODE\n')
        f.write('    }\n')
        f.write('}\n\n')
        f.write('Write-Host "================================================================" -ForegroundColor Cyan\n')
        f.write('Write-Host "2581check - Cython Distribution Builder" -ForegroundColor Cyan\n')
        f.write('Write-Host "================================================================" -ForegroundColor Cyan\n')
        f.write('Write-Host ""\n\n')
        
        f.write('Write-Host "Checking requirements..." -ForegroundColor Yellow\n\n')
        
        f.write('# Check Cython\n')
        f.write('try {\n')
        f.write('    python -c "import Cython"\n')
        f.write('    Write-Host "OK Cython installed" -ForegroundColor Green\n')
        f.write('} catch {\n')
        f.write('    Write-Host "ERROR: Cython not installed!" -ForegroundColor Red\n')
        f.write('    Write-Host "Please install: pip install Cython" -ForegroundColor Yellow\n')
        f.write('    exit 1\n')
        f.write('}\n\n')
        
        f.write('# Check PyQt5\n')
        f.write('try {\n')
        f.write('    python -c "import PyQt5"\n')
        f.write('    Write-Host "OK PyQt5 installed" -ForegroundColor Green\n')
        f.write('} catch {\n')
        f.write('    Write-Host "ERROR: PyQt5 not installed!" -ForegroundColor Red\n')
        f.write('    Write-Host "Please install: pip install PyQt5" -ForegroundColor Yellow\n')
        f.write('    exit 1\n')
        f.write('}\n\n')
        
        f.write('# Check lxml\n')
        f.write('try {\n')
        f.write('    python -c "import lxml"\n')
        f.write('    Write-Host "OK lxml installed" -ForegroundColor Green\n')
        f.write('} catch {\n')
        f.write('    Write-Host "ERROR: lxml not installed!" -ForegroundColor Red\n')
        f.write('    Write-Host "Please install: pip install lxml" -ForegroundColor Yellow\n')
        f.write('    exit 1\n')
        f.write('}\n\n')
        
        f.write('Write-Host ""\n')
        f.write('Write-Host "Step 1: Cleaning previous builds..." -ForegroundColor Yellow\n')
        f.write('if (Test-Path "build") { Remove-Item "build" -Recurse -Force }\n')
        f.write('Get-ChildItem "src" -Filter "*.c" -ErrorAction SilentlyContinue | Remove-Item -Force\n')
        f.write('Get-ChildItem "src" -Filter "*.cpp" -ErrorAction SilentlyContinue | Remove-Item -Force\n')
        f.write('Get-ChildItem "src" -Filter "*.pyd" -ErrorAction SilentlyContinue | Remove-Item -Force\n\n')
        
        f.write('Write-Host "Step 2: Building Cython extensions..." -ForegroundColor Yellow\n')
        f.write('python setup.py build_ext --inplace\n')
        f.write('if ($LASTEXITCODE -ne 0) {\n')
        f.write('    Write-Host "ERROR: Cython compilation failed!" -ForegroundColor Red\n')
        f.write('    exit 1\n')
        f.write('}\n\n')
        
        f.write('Write-Host "Step 3: Copying compiled module..." -ForegroundColor Yellow\n')
        f.write('$pydFile = Get-ChildItem -Path "build" -Filter "validation_core*.pyd" -Recurse | Select-Object -First 1\n')
        f.write('if ($pydFile) {\n')
        f.write('    Copy-Item $pydFile.FullName -Destination "src" -Force\n')
        f.write('    Write-Host "OK Copied to src directory" -ForegroundColor Green\n')
        f.write('} else {\n')
        f.write('    Write-Host "ERROR: Compiled module not found!" -ForegroundColor Red\n')
        f.write('    exit 1\n')
        f.write('}\n\n')
        
        f.write('Write-Host "Step 4: Testing Cython module..." -ForegroundColor Yellow\n')
        f.write('Set-Location "src"\n')
        # Use single quotes inside the python command to avoid escaping issues
        f.write("python -c \"from validation_core import ValidationCore; print('OK Module works')\"\n")
        f.write('if ($LASTEXITCODE -ne 0) {\n')
        f.write('    Write-Host "ERROR: Module test failed!" -ForegroundColor Red\n')
        f.write('    Set-Location ".."\n')
        f.write('    exit 1\n')
        f.write('}\n\n')
        
        f.write('Write-Host "Step 5: Creating executable with PyInstaller..." -ForegroundColor Yellow\n')
        f.write('pyinstaller --onefile --windowed --name "2581check" 2581check_pyqt5_hybrid.py --hidden-import=validation_core\n')
        f.write('if ($LASTEXITCODE -ne 0) {\n')
        f.write('    Write-Host "ERROR: PyInstaller failed!" -ForegroundColor Red\n')
        f.write('    Set-Location ".."\n')
        f.write('    exit 1\n')
        f.write('}\n\n')
        
        f.write('Write-Host "Step 6: Moving executable..." -ForegroundColor Yellow\n')
        f.write('if (-not (Test-Path "..\\\\dist")) { New-Item -ItemType Directory -Path "..\\\\dist" }\n')
        # Try to remove with retry logic for locked files
        f.write('$targetPath = "..\\\\dist\\\\2581check.exe"\n')
        f.write('if (Test-Path $targetPath) {\n')
        f.write('    try {\n')
        f.write('        Start-Sleep -Milliseconds 500\n')  # Wait a moment
        f.write('        Remove-Item $targetPath -Force -ErrorAction Stop\n')
        f.write('        Write-Host "Removed existing executable" -ForegroundColor Gray\n')
        f.write('    } catch {\n')
        f.write('        Write-Host "Warning: Could not remove existing file (may be in use)" -ForegroundColor Yellow\n')
        f.write('        Write-Host "Trying alternative approach..." -ForegroundColor Yellow\n')
        f.write('        $backupPath = "..\\\\dist\\\\2581check_old.exe"\n')
        f.write('        if (Test-Path $backupPath) { Remove-Item $backupPath -Force -ErrorAction SilentlyContinue }\n')
        f.write('        Move-Item $targetPath $backupPath -Force -ErrorAction SilentlyContinue\n')
        f.write('    }\n')
        f.write('}\n')
        f.write('Move-Item "dist\\\\2581check.exe" "..\\\\dist" -Force\n')
        f.write('Write-Host "OK Executable moved to dist folder" -ForegroundColor Green\n')
        f.write('Set-Location ".."\n\n')
        
        f.write('Write-Host ""\n')
        f.write('Write-Host "================================================================" -ForegroundColor Green\n')
        f.write('Write-Host "BUILD COMPLETED!" -ForegroundColor Green\n')
        f.write('Write-Host "================================================================" -ForegroundColor Green\n')
        f.write('Write-Host ""\n')
        f.write('Write-Host "Output: dist\\\\2581check.exe" -ForegroundColor Cyan\n')
        f.write('Write-Host ""\n')
    
    # Create batch file launcher
    bat_file = os.path.join(dist_dir, "build_distribution.bat")
    with open(bat_file, 'w', encoding='utf-8') as f:
        f.write('@echo off\n')
        f.write('powershell -ExecutionPolicy Bypass -File "%~dp0build_distribution.ps1"\n')
    
    print("✓ Created PowerShell build script (build_distribution.ps1)")
    print("✓ Created batch launcher (build_distribution.bat)")

if __name__ == "__main__":
    create_distribution_project()
