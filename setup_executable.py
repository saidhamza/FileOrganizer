#!/usr/bin/env python3
"""
Setup script to create executable for File Organizer

This script creates a standalone executable for Linux systems
using PyInstaller.

Requirements:
- PyInstaller
- All dependencies of the main application

Usage:
python setup_executable.py
"""

import os
import sys
import subprocess
import platform

def main():
    """Check requirements and build the executable"""
    print("Setting up File Organizer executable...")
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print("PyInstaller is installed.")
    except ImportError:
        print("PyInstaller is not installed. Installing now...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Check if Pillow is installed (optional dependency)
    try:
        import PIL
        has_pillow = True
        print("Pillow is installed.")
    except ImportError:
        has_pillow = False
        print("Warning: Pillow is not installed. EXIF data extraction will be disabled.")
        install_pillow = input("Would you like to install Pillow now? (y/n): ")
        if install_pillow.lower() == 'y':
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
            has_pillow = True
    
    # Define PyInstaller command with options
    pyinstaller_cmd = [
        "pyinstaller",
        "--name=FileOrganizer",
        "--onefile",                       # Create a single executable file
        "--windowed",                      # Hide the console window on Windows
        "--add-data=LICENSE:.",            # Include LICENSE file
        "--add-data=README.md:.",          # Include README file
    ]
    
    # Add icon if available
    icon_path = os.path.join(os.getcwd(), "icon.png")
    if os.path.exists(icon_path):
        pyinstaller_cmd.append(f"--icon={icon_path}")
    
    # Add the main script
    pyinstaller_cmd.append("file_organizer.py")
    
    # Execute PyInstaller
    print("\nBuilding executable with PyInstaller...")
    print(f"Command: {' '.join(pyinstaller_cmd)}")
    subprocess.check_call(pyinstaller_cmd)
    
    print("\nBuild complete!")
    print("You can find the executable in the 'dist' directory")
    
    # Check the executable
    dist_dir = os.path.join(os.getcwd(), "dist")
    executable_path = os.path.join(dist_dir, "FileOrganizer")
    
    if os.path.exists(executable_path):
        print(f"\nExecutable created successfully: {executable_path}")
        print("You can run it with: ./dist/FileOrganizer")
        
        # Make executable
        os.chmod(executable_path, 0o755)
        
        # Suggest desktop integration
        if platform.system() == "Linux":
            desktop_file = create_desktop_file(executable_path)
            print(f"\nDesktop file created: {desktop_file}")
            print("To install the desktop entry system-wide, copy it to /usr/share/applications/")
            print("For personal use, copy it to ~/.local/share/applications/")

def create_desktop_file(executable_path):
    """Create a desktop entry file for Linux"""
    desktop_entry = f"""[Desktop Entry]
Type=Application
Name=File Organizer
Comment=Organize your files automatically by type, date, or category
Exec={executable_path}
Icon={os.path.abspath('icon.png') if os.path.exists('icon.png') else ''}
Terminal=false
Categories=Utility;FileTools;
"""
    
    # Create desktop file
    desktop_file_path = os.path.join(os.getcwd(), "FileOrganizer.desktop")
    with open(desktop_file_path, "w") as f:
        f.write(desktop_entry)
    
    # Make it executable
    os.chmod(desktop_file_path, 0o755)
    
    return desktop_file_path

if __name__ == "__main__":
    main()
