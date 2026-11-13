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
Version checker for 2581check

Run this script to display current version information.
"""

import sys
import os

# Read version info directly from the main application file
def get_version_from_main():
    """Extract version info from 2581check.py"""
    try:
        with open('2581check.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        import re
        version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        build_match = re.search(r'__build__\s*=\s*["\']([^"\']+)["\']', content)
        release_match = re.search(r'__release__\s*=\s*["\']([^"\']+)["\']', content)
        author_match = re.search(r'__author__\s*=\s*["\']([^"\']+)["\']', content)
        
        return {
            'version': version_match.group(1) if version_match else 'Unknown',
            'build': build_match.group(1) if build_match else 'Unknown',
            'release': release_match.group(1) if release_match else 'Unknown',
            'author': author_match.group(1) if author_match else 'Unknown'
        }
    except Exception as e:
        return {
            'version': 'Unknown',
            'build': 'Unknown',
            'release': 'Unknown',
            'author': 'Unknown'
        }

def main():
    """Main function to display version information"""
    info = get_version_from_main()
    
    print("=" * 60)
    print("2581check - VERSION INFORMATION")
    print("=" * 60)
    print()
    print(f"Application: 2581check")
    print(f"Version:     {info['version']}")
    print(f"Build:       {info['build']}")
    print(f"Release:     {info['release']}")
    print(f"Author:      {info['author']}")
    print()
    print(f"Description: IPC-2581 XML validation tool with unlimited line support")
    print()
    
    # Check if main application file exists
    main_file = "2581check.py"
    if os.path.exists(main_file):
        print(f"✓ Main application found: {main_file}")
    else:
        print(f"✗ Main application NOT found: {main_file}")
    
    print()
    print("Checking dependencies...")
    
    # Check PyQt5
    try:
        from PyQt5.QtCore import QT_VERSION_STR
        print(f"✓ PyQt5 version: {QT_VERSION_STR}")
    except ImportError:
        print("✗ PyQt5 not installed")
    
    # Check lxml
    try:
        import lxml.etree
        print(f"✓ lxml version: {lxml.etree.__version__}")
    except ImportError:
        print("✗ lxml not installed")
    
    print()

if __name__ == "__main__":
    main()

