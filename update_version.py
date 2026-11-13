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
Version update utility for 2581check

Use this script to update version numbers before releasing.
"""

import re
import os
import sys
import subprocess
from datetime import datetime


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def update_main_file_version(major=None, minor=None, patch=None, release_type=None):
    """Update version numbers directly in 2581check.py"""
    
    main_file = os.path.join(SCRIPT_DIR, "2581check.py")
    if not os.path.exists(main_file):
        print(f"Error: {main_file} not found!")
        return False
    
    # Read current file
    with open(main_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract current version
    version_match = re.search(r'__version__\s*=\s*["\'](\d+)\.(\d+)\.(\d+)["\']', content)
    if not version_match:
        print("Error: Could not find version in main file!")
        return False
    
    current_major, current_minor, current_patch = map(int, version_match.groups())
    
    # Update version components if provided
    if major is not None:
        current_major = int(major)
    if minor is not None:
        current_minor = int(minor)
    if patch is not None:
        current_patch = int(patch)
    
    new_version = f"{current_major}.{current_minor}.{current_patch}"
    content = re.sub(r'__version__\s*=\s*["\'][^"\']+["\']', 
                     f'__version__ = "{new_version}"', content)
    
    # Update build date and number
    today = datetime.now().strftime('%Y%m%d')
    build_match = re.search(r'__build__\s*=\s*["\'](\d{8})-(\d{3})["\']', content)
    
    if build_match:
        current_build_num = int(build_match.group(2))
        new_build_num = f"{current_build_num + 1:03d}"
    else:
        new_build_num = "001"
    
    new_build = f"{today}-{new_build_num}"
    content = re.sub(r'__build__\s*=\s*["\'][^"\']+["\']', 
                     f'__build__ = "{new_build}"', content)
    
    # Update release type if provided
    if release_type:
        content = re.sub(r'__release__\s*=\s*["\'][^"\']+["\']', 
                        f'__release__ = "{release_type}"', content)
    
    # Write updated file
    with open(main_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Updated {os.path.basename(main_file)}")
    print(f"  Version: {new_version}")
    print(f"  Build:   {new_build}")
    if release_type:
        print(f"  Release: {release_type}")
    return True

def main():
    print("2581check - Version Update Utility")
    print("=" * 50)
    
    print("Current version:")
    check_version_script = os.path.join(SCRIPT_DIR, "check_version.py")
    subprocess.run([sys.executable, check_version_script], check=False)
    
    print("\nUpdate options:")
    print("1. Patch release (x.x.N)")
    print("2. Minor release (x.N.0)")
    print("3. Major release (N.0.0)")
    print("4. Change release type only")
    print("5. Just increment build number")
    print("q. Quit without changes")
    
    choice = input("\nSelect option (1-5, q): ").strip().lower()
    
    if choice == "q":
        print("No changes made. Exiting.")
        return
    elif choice == "1":
        # Patch release
        patch = input("New patch number: ")
        update_main_file_version(patch=patch)
    elif choice == "2":
        # Minor release
        minor = input("New minor number: ")
        update_main_file_version(minor=minor, patch=0)
    elif choice == "3":
        # Major release
        major = input("New major number: ")
        update_main_file_version(major=major, minor=0, patch=0)
    elif choice == "4":
        # Release type only
        release = input("New release type (Alpha/Beta/RC/Stable): ")
        update_main_file_version(release_type=release)
    elif choice == "5":
        # Just build number
        update_main_file_version()
    else:
        print("Invalid choice!")
        return
    
    print("\nUpdated version:")
    subprocess.run([sys.executable, check_version_script], check=False)

if __name__ == "__main__":
    main()

