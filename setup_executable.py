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
    
    # Check if requests is installed (needed for location features)
    try:
        import requests
        has_requests = True
        print("Requests is installed.")
    except ImportError:
        has_requests = False
        print("Warning: Requests is not installed. Location-based organization will be limited.")
        install_requests = input("Would you like to install Requests now? (y/n): ")
        if install_requests.lower() == 'y':
            subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
            has_requests = True
    
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
    
    # Fix for PIL/_tkinter_finder issue
    if has_pillow:
        # Add necessary hidden imports for PIL
        pyinstaller_cmd.extend([
            "--hidden-import=PIL._tkinter_finder",
            "--hidden-import=PIL._imagingtk",
            "--hidden-import=PIL._imaging",
            "--hidden-import=PIL.ImageTk",
            "--hidden-import=PIL.Image",
            "--hidden-import=PIL.ExifTags",
        ])
        
        # Add collect-all for PIL to ensure all submodules are included
        pyinstaller_cmd.append("--collect-all=PIL")
    
    # Add hidden imports for requests if installed
    if has_requests:
        pyinstaller_cmd.extend([
            "--hidden-import=requests",
            "--hidden-import=urllib3",
        ])
    
    # Additional platform-specific options
    if platform.system() == "Linux":
        pyinstaller_cmd.append("--hidden-import=PIL._tkinter_finder")
    
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
    else:
        print(f"\nWarning: Executable not found at expected path: {executable_path}")
        print("Please check the PyInstaller output for errors.")

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
