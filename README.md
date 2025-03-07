# File Organizer

A Python desktop application that helps you organize your files automatically by different criteria.

## Features

- **Organize by File Type**: Sort files into folders based on their extensions
- **Organize by Date**: Sort files into folders based on their creation or modification date
- **Organize by Category**: Sort files into predefined categories (Images, Documents, Videos, etc.)
- **Preview Changes**: See what will happen before applying any changes
- **Support for Network Paths**: Access and organize files on network drives
- **Enhanced Network Support**: Improved interface for SMB/CIFS network shares
- **Date Extraction**: Extract dates from filenames, EXIF data, or file timestamps
- **Customizable Date Format**: Organize by year, month, or day
- **Empty Folder Cleanup**: Option to delete empty folders after organization
- **Recent Folders**: Quick access to recently used folders

## Requirements

- Python 3.6+
- Tkinter (usually included with Python)
  - On Ubuntu/Debian: `sudo apt-get install python3-tk`
  - On Fedora/RHEL: `sudo dnf install python3-tkinter`
  - On Windows/macOS: Already included with Python
- Pillow (optional, for EXIF data extraction)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/saidhamza/FileOrganizer.git
   cd file-organizer
   ```

2. Install dependencies:
   ```
   # If Tkinter is not already installed:
   # Ubuntu/Debian:
   sudo apt-get install python3-tk
   
   # Fedora/RHEL:
   sudo dnf install python3-tkinter
   
   # Install optional Pillow for EXIF support:
   pip install pillow
   ```

3. Run the application:
   ```
   python file_organizer.py
   ```

## Usage

1. **Select a folder** to organize using the "Browse" button
   - Choose from local folders, network shares, or recent locations
   - Network shares can be entered in formats like `//server/share` or `\\server\share`
2. **Choose your organization method**:
   - "Preview by Type" to organize by file extension
   - "Preview by Date" to organize by date (choose date source and format)
   - "Preview by Category" to organize by predefined categories
3. **Review the changes** in the preview window
4. **Click "Execute"** to apply the changes

## Network Share Access

The application supports accessing SMB/CIFS network shares in several ways:

1. Direct entry of network paths:
   - Windows format: `\\server\share`
   - Unix format: `//server/share` 
   - With credentials: `//username:password@server/share`

2. Comprehensive help is available via the "Network Path Help" button, including:
   - Platform-specific mounting instructions (Windows, Linux, macOS)
   - Troubleshooting tips for common network connectivity issues
   - SMB protocol version compatibility information

## Categories

Files will be organized into these categories when using "Preview by Category":
- Images (.jpg, .png, .gif, etc.)
- Documents (.pdf, .docx, .txt, etc.)
- Videos (.mp4, .mov, .avi, etc.)
- Audio (.mp3, .wav, .flac, etc.)
- Archives (.zip, .rar, .7z, etc.)
- Code (.py, .js, .html, etc.)
- Executables (.exe, .app, .bat, etc.)
- Other (unrecognized file types)

## License

GNU General Public License v3.0

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

See the [LICENSE](LICENSE) file for details.
