# Ensure tkinter is installed: sudo apt-get install python3-tk
# Ensure tkinter is installed: sudo dnf install python3-tkinter
import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel, Text, ttk, scrolledtext
from datetime import datetime
import json
import re
import time
import platform
from pathlib import Path
import urllib.parse
import subprocess
import threading

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

class ToolTip:
    """Create a tooltip for a given widget"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        # Create top level window
        self.tooltip = tk.Toplevel(self.widget)
        # Remove window decorations
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(self.tooltip, text=self.text, background="#FFFFDD",
                     wraplength=250, font=("tahoma", 9), padx=5, pady=3)
        label.pack()
        
    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class FileOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File Organizer")
        self.root.geometry("650x700")  # Increased height for additional options
        self.root.minsize(600, 800)    # Increased minimum height
        self.root.resizable(True, True)

        # Config file path
        self.config_file = os.path.join(os.path.expanduser("~"), ".file_organizer_config.json")
        
        # Load config
        self.config = self.load_config()
        
        # File category definitions - moved here before UI initialization
        self.category_definitions = {
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".svg", ".heic"],
            "Documents": [".doc", ".docx", ".pdf", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"],
            "Videos": [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg", ".mts", ".m2ts", ".3gp"],
            "Audio": [".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a", ".wma", ".aiff"],
            "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"],
            "Code": [".py", ".js", ".html", ".css", ".java", ".c", ".cpp", ".php", ".rb", ".go", ".rs", ".ts", ".sh", ".json", ".xml"],
            "Executables": [".exe", ".msi", ".app", ".bat", ".sh", ".apk", ".deb", ".rpm"]
        }
        
        self.path = tk.StringVar()
        if "last_directory" in self.config and self.is_valid_path(self.config["last_directory"]):
            self.path.set(self.config["last_directory"])
            
        self.include_subfolders = tk.BooleanVar()
        if "include_subfolders" in self.config:
            self.include_subfolders.set(self.config["include_subfolders"])
        
        # Add delete empty folders option
        self.delete_empty_folders = tk.BooleanVar()
        if "delete_empty_folders" in self.config:
            self.delete_empty_folders.set(self.config["delete_empty_folders"])
        else:
            self.delete_empty_folders.set(False)  # Default to not deleting
        
        # Add date source option
        self.date_source = tk.StringVar()
        self.date_source.set(self.config.get("date_source", "all"))
        
        # Date format granularity option
        self.date_format = tk.StringVar()
        self.date_format.set(self.config.get("date_format", "day"))
        
        # Store last used directory
        self.last_directory = self.config.get("last_directory", os.path.expanduser("~"))
        
        # Recent folders list (keep top 5)
        self.recent_folders = self.config.get("recent_folders", [])

        # Create frames for better organization
        top_frame = tk.Frame(root)
        top_frame.pack(fill="x", padx=20, pady=10)

        recent_frame = tk.Frame(root)
        recent_frame.pack(fill="x", padx=20, pady=5)

        options_frame = tk.Frame(root)
        options_frame.pack(fill="x", padx=20, pady=10)
        
        date_options_frame = tk.Frame(root)
        date_options_frame.pack(fill="x", padx=20, pady=5)
        
        date_format_frame = tk.Frame(root)
        date_format_frame.pack(fill="x", padx=20, pady=5)

        buttons_frame = tk.Frame(root)
        buttons_frame.pack(fill="x", padx=20, pady=10)
        self.buttons_frame = buttons_frame  # Save reference

        # Top frame - folder selection
        tk.Label(top_frame, text="Choose Folder:").pack(side="left", padx=5)
        tk.Entry(top_frame, textvariable=self.path, width=50).pack(side="left", padx=5)
        tk.Button(top_frame, text="Browse", command=self.browse_folder).pack(side="left", padx=5)
        
        # Recent folders dropdown
        if self.recent_folders:
            tk.Label(recent_frame, text="Recent Folders:").pack(side="left", padx=5)
            self.recent_var = tk.StringVar()  # Make this an instance variable
            recent_dropdown = ttk.Combobox(recent_frame, textvariable=self.recent_var, width=50)
            recent_dropdown['values'] = self.recent_folders
            recent_dropdown.pack(side="left", padx=5)
            recent_dropdown.bind("<<ComboboxSelected>>", self.on_recent_folder_selected)

        # Options frame
        tk.Checkbutton(options_frame, text="Include Subfolders", variable=self.include_subfolders).pack(side="left", padx=5)
        
        # Delete empty folders option
        tk.Checkbutton(options_frame, text="Delete Empty Folders", variable=self.delete_empty_folders, 
                      command=self.confirm_delete_empty).pack(side="left", padx=5)
        
        # Replace the network folder button with simple instructions
        self.network_button = tk.Button(options_frame, text="Network Path Help", command=self.show_network_help)
        self.network_button.pack(side="left", padx=20)

        # Date source options frame
        date_label = tk.Label(date_options_frame, text="Date Source:", font=("Arial", 10))
        date_label.grid(row=0, column=0, sticky="w", pady=5)
        
        # Radio buttons with tooltips
        rb1 = tk.Radiobutton(date_options_frame, text="All Sources (Filename → EXIF → File Date)",
                      variable=self.date_source, value="all")
        rb1.grid(row=0, column=1, sticky="w")
        ToolTip(rb1, "Try to extract date first from filename, then from EXIF metadata, and finally from file creation date.")
        
        rb2 = tk.Radiobutton(date_options_frame, text="Filename Only",
                      variable=self.date_source, value="filename") 
        rb2.grid(row=1, column=1, sticky="w")
        ToolTip(rb2, "Only extract date from filename patterns like YYYY-MM-DD. Falls back to file creation date if no pattern is found.")
        
        rb3 = tk.Radiobutton(date_options_frame, text="EXIF Only",
                      variable=self.date_source, value="exif")
        rb3.grid(row=2, column=1, sticky="w")
        ToolTip(rb3, "Only extract date from image EXIF metadata. Falls back to file creation date if no EXIF data is found.")
        
        rb4 = tk.Radiobutton(date_options_frame, text="File Date Only",
                      variable=self.date_source, value="filedate")
        rb4.grid(row=3, column=1, sticky="w")
        ToolTip(rb4, "Use only the file's creation date/time for organization.")

        # Add a help button
        help_button = tk.Button(date_options_frame, text="?", width=2, command=self.show_date_help)
        help_button.grid(row=0, column=2, padx=5)
        
        # Date format options (granularity)
        date_format_label = tk.Label(date_format_frame, text="Date Sorting Level:", font=("Arial", 10))
        date_format_label.grid(row=0, column=0, sticky="w", pady=5)
        
        format_options = [
            ("By Year (YYYY)", "year", "%Y"),
            ("By Month (YYYY-MM)", "month", "%Y-%m"),
            ("By Day (YYYY-MM-DD)", "day", "%Y-%m-%d")
        ]
        
        for i, (text, value, _) in enumerate(format_options):
            rb = tk.Radiobutton(date_format_frame, text=text, variable=self.date_format, value=value)
            rb.grid(row=i, column=1, sticky="w")
        
        # Date format preview
        self.date_format_preview = tk.Label(date_format_frame, text="Example: " + self.get_date_format_example())
        self.date_format_preview.grid(row=0, column=2, rowspan=3, padx=20)
        
        # Update preview when format changes
        self.date_format.trace_add("write", lambda *args: self.update_date_format_preview())

        # Add another frame for category organization
        category_frame = tk.Frame(root)
        category_frame.pack(fill="x", padx=20, pady=5)
        
        category_label = tk.Label(category_frame, text="File Categories:", font=("Arial", 10, "bold"))
        category_label.pack(anchor="w", pady=(10, 5))
        
        category_info = tk.Label(category_frame, 
                               text="Files will be organized into these categories when 'Preview by Category' is used.",
                               font=("Arial", 8))
        category_info.pack(anchor="w")

        # Add category list display
        categories_text = ", ".join(list(self.category_definitions.keys()) + ["Other"])
        categories_display = tk.Label(category_frame, text=categories_text, font=("Arial", 9), 
                                     wraplength=550, justify="left")
        categories_display.pack(anchor="w", padx=10, pady=5)

        # Buttons frame - update with Category option
        preview_label = tk.Label(buttons_frame, text="Preview Options:", font=("Arial", 10, "bold"))
        preview_label.grid(row=0, column=0, columnspan=3, sticky="w", pady=10)

        tk.Button(buttons_frame, text="Preview by Type", command=self.preview_by_type, 
                  width=15, bg="#e0e0ff").grid(row=1, column=0, padx=10, pady=5)
        tk.Button(buttons_frame, text="Preview by Date", command=self.preview_by_date,
                  width=15, bg="#e0e0ff").grid(row=1, column=1, padx=10, pady=5)
        tk.Button(buttons_frame, text="Preview by Category", command=self.preview_by_category,
                  width=15, bg="#e0e0ff").grid(row=1, column=2, padx=10, pady=5)
                  
        # Log frame
        log_frame = tk.Frame(root)
        log_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        log_label = tk.Label(log_frame, text="Activity Log:", font=("Arial", 10, "bold"))
        log_label.pack(anchor="w")
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap=tk.WORD)
        self.log_text.pack(fill="both", expand=True)
        self.log_text.config(state="disabled")

        # Status bar
        status_frame = tk.Frame(root, bd=1, relief=tk.SUNKEN)
        status_frame.pack(fill="x", side="bottom")
        self.status_label = tk.Label(status_frame, text="Ready", anchor="w")
        self.status_label.pack(fill="x")

        self.preview = []
        
        # Bind window close event to save config
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Initial log message
        self.log("File Organizer started")
        if not HAS_PIL:
            self.log("WARNING: PIL/Pillow not installed. EXIF data extraction will not be available.")
        if self.path.get():
            self.log(f"Loaded last directory: {self.path.get()}")

    def is_valid_path(self, path):
        """Check if the path is valid and accessible"""
        try:
            if path.startswith("//") or path.startswith("\\\\"):  # SMB path
                # Just check if the path exists, but don't try to access it yet
                return True
            return os.path.exists(path)
        except:
            return False
    
    def get_date_format_example(self):
        """Get example of date format based on selection"""
        today = datetime.now()
        if self.date_format.get() == "year":
            return today.strftime("%Y")
        elif self.date_format.get() == "month":
            return today.strftime("%Y-%m")
        else:  # Default to day
            return today.strftime("%Y-%m-%d")
    
    def update_date_format_preview(self):
        """Update the date format preview label"""
        self.date_format_preview.config(text="Example: " + self.get_date_format_example())
            
    def on_recent_folder_selected(self, event):
        """Handle selection from recent folders dropdown"""
        folder = self.recent_var.get()
        self.select_recent_folder(folder)
        
    def select_recent_folder(self, folder):
        """Select a folder from the recent folders dropdown"""
        if folder and self.is_valid_path(folder):
            self.path.set(folder)
            self.last_directory = folder
            self.save_config()
            self.log(f"Selected recent folder: {folder}")
        else:
            self.log(f"Cannot access folder: {folder}")
            messagebox.showwarning("Invalid Path", f"The folder '{folder}' is not accessible.")
    
    def add_to_recent_folders(self, folder):
        """Add a folder to recent folders list, maintaining only the most recent 5"""
        if folder in self.recent_folders:
            self.recent_folders.remove(folder)
        self.recent_folders.insert(0, folder)
        # Keep only the 5 most recent folders
        self.recent_folders = self.recent_folders[:5]

    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
        return {}
        
    def save_config(self):
        """Save configuration to file"""
        try:
            config = {
                "last_directory": self.last_directory,
                "include_subfolders": self.include_subfolders.get(),
                "date_source": self.date_source.get(),
                "date_format": self.date_format.get(),
                "delete_empty_folders": self.delete_empty_folders.get(),
                "recent_folders": self.recent_folders
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
                
        except Exception as e:
            print(f"Error saving config: {e}")
            
    def on_closing(self):
        """Handle window closing event"""
        self.save_config()
        self.root.destroy()

    def log(self, message):
        """Add a message to the log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)  # Scroll to the end
        self.log_text.config(state="disabled")

    def browse_folder(self):
        """Enhanced browse folder that supports direct input of network paths"""
        initial_dir = self.last_directory
        if self.path.get():
            current_path = self.path.get()
            if os.path.isdir(current_path):
                initial_dir = current_path
        
        # Add a dropdown or button group for common sources
        source_dialog = Toplevel(self.root)
        source_dialog.title("Select Folder Source")
        source_dialog.geometry("400x250")
        source_dialog.grab_set()
        source_dialog.transient(self.root)
        source_dialog.resizable(False, False)
        
        # Center the dialog
        source_dialog.update_idletasks()
        x = (source_dialog.winfo_screenwidth() - source_dialog.winfo_width()) // 2
        y = (source_dialog.winfo_screenheight() - source_dialog.winfo_height()) // 2
        source_dialog.geometry(f"+{x}+{y}")
        
        # Header
        tk.Label(source_dialog, text="Choose a folder source:", font=("Arial", 12, "bold")).pack(pady=(15, 20))
        
        result = [None]  # To store the result
        
        def select_local():
            source_dialog.destroy()
            folder_selected = filedialog.askdirectory(initialdir=initial_dir)
            if folder_selected:
                result[0] = folder_selected
                self.on_folder_selected(folder_selected)
        
        def select_network():
            source_dialog.destroy()
            network_path = self.manual_network_path_input()
            if network_path:
                result[0] = network_path
                self.on_folder_selected(network_path)
        
        def select_recent():
            source_dialog.destroy()
            self.select_from_recent_list()
        
        # Create buttons with icons (text only if no icons available)
        btn_frame = tk.Frame(source_dialog)
        btn_frame.pack(fill="both", expand=True, padx=20)
        
        # Local folder button
        local_btn = tk.Button(btn_frame, text="Local Folder", width=25, height=2,
                            command=select_local, bg="#e0e0ff")
        local_btn.pack(pady=10)
        ToolTip(local_btn, "Browse your local file system for a folder to organize")
        
        # Network share button
        network_btn = tk.Button(btn_frame, text="Network Share (SMB)", width=25, height=2,
                              command=select_network, bg="#e0ffef")
        network_btn.pack(pady=10)
        ToolTip(network_btn, "Enter a network path like //server/share or \\\\server\\share")
        
        # Recent folders button
        if self.recent_folders:
            recent_btn = tk.Button(btn_frame, text="Recent Folders", width=25, height=2,
                                command=select_recent, bg="#fff0e0")
            recent_btn.pack(pady=10)
            ToolTip(recent_btn, "Select from your recently used folders")
        
        # Cancel button
        cancel_btn = tk.Button(source_dialog, text="Cancel", command=source_dialog.destroy, width=10)
        cancel_btn.pack(pady=15)
        
        # Wait for dialog to close
        self.root.wait_window(source_dialog)
    
    def on_folder_selected(self, folder):
        """Handle a selected folder from any source"""
        if folder and self.is_valid_path(folder):
            self.path.set(folder)
            self.last_directory = folder
            self.add_to_recent_folders(folder)
            self.save_config()
            self.status_label.config(text=f"Selected folder: {folder}")
            self.log(f"Selected folder: {folder}")
    
    def select_from_recent_list(self):
        """Show dialog to select from recent folders"""
        if not self.recent_folders:
            messagebox.showinfo("No Recent Folders", "You don't have any recent folders to select from.")
            return None
        
        recent_dialog = Toplevel(self.root)
        recent_dialog.title("Select Recent Folder")
        recent_dialog.geometry("500x300")
        recent_dialog.transient(self.root)
        recent_dialog.grab_set()
        
        # Center the dialog
        recent_dialog.update_idletasks()
        x = (recent_dialog.winfo_screenwidth() - recent_dialog.winfo_width()) // 2
        y = (recent_dialog.winfo_screenheight() - recent_dialog.winfo_height()) // 2
        recent_dialog.geometry(f"+{x}+{y}")
        
        tk.Label(recent_dialog, text="Select a recent folder:", font=("Arial", 11)).pack(pady=10)
        
        # Create listbox
        listbox_frame = tk.Frame(recent_dialog)
        listbox_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = tk.Listbox(listbox_frame, font=("Arial", 10), width=60, height=10)
        listbox.pack(side="left", fill="both", expand=True)
        
        # Configure scrollbar
        scrollbar.config(command=listbox.yview)
        listbox.config(yscrollcommand=scrollbar.set)
        
        # Add items
        for folder in self.recent_folders:
            listbox.insert(tk.END, folder)
        
        # Select first item
        if listbox.size() > 0:
            listbox.selection_set(0)
        
        result = [None]  # To store result
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                selected_folder = self.recent_folders[selection[0]]
                if self.is_valid_path(selected_folder):
                    result[0] = selected_folder
                    self.on_folder_selected(selected_folder)
                else:
                    messagebox.showwarning("Path Not Accessible", 
                        f"The selected path '{selected_folder}' is not accessible.\n\n"
                        "If it's a network path, make sure the share is mounted or accessible.")
            recent_dialog.destroy()
        
        def on_double_click(event):
            on_select()
        
        # Bind double click
        listbox.bind("<Double-1>", on_double_click)
        
        button_frame = tk.Frame(recent_dialog)
        button_frame.pack(fill="x", pady=10)
        
        tk.Button(button_frame, text="Cancel", command=recent_dialog.destroy, width=10).pack(side="right", padx=20)
        tk.Button(button_frame, text="Select", command=on_select, width=10).pack(side="right")
        
        # Wait for dialog to close
        self.root.wait_window(recent_dialog)
        
        return result[0]
    
    def manual_network_path_input(self):
        """Enhanced dialog for manual network path input"""
        dialog = Toplevel(self.root)
        dialog.title("Enter Network Share Path")
        dialog.geometry("500x250")
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - dialog.winfo_width()) // 2
        y = (dialog.winfo_screenheight() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        result = [None]  # Use list to store result from inner function
        
        # Header
        header_frame = tk.Frame(dialog)
        header_frame.pack(fill="x", padx=20, pady=(10, 5))
        
        tk.Label(header_frame, text="Enter Network Share Path:", 
                font=("Arial", 11, "bold")).pack(anchor="w")
        
        # Info text
        info_text = "Enter the path to a shared network folder (SMB/CIFS).\n" + \
                  "Example formats: //server/share or \\\\server\\share"
        tk.Label(dialog, text=info_text, justify="left").pack(padx=20, anchor="w")
        
        # Entry field
        path_var = tk.StringVar()
        entry_frame = tk.Frame(dialog)
        entry_frame.pack(fill="x", padx=20, pady=10)
        
        path_entry = tk.Entry(entry_frame, textvariable=path_var, width=50)
        path_entry.pack(side="left", fill="x", expand=True)
        path_entry.focus_set()
        
        # Path format help with examples
        examples_frame = tk.Frame(dialog)
        examples_frame.pack(fill="x", padx=20, pady=5)
        
        example_text = "• For Windows: \\\\server\\share or //server/share\n" + \
                     "• For Linux/macOS: //server/share\n" + \
                     "• With credentials: //username:password@server/share"
        tk.Label(examples_frame, text=example_text, justify="left", 
               font=("Arial", 9)).pack(anchor="w")
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(fill="x", padx=20, pady=(15, 10))
        
        def on_ok():
            path = path_var.get().strip()
            # Normalize path (replace backslashes with forward slashes)
            if path.startswith("\\\\"):
                path = "/" + path.replace("\\", "/")
            if path:
                result[0] = path
            dialog.destroy()
        
        def show_advanced_help():
            self.show_network_help()
        
        help_button = tk.Button(button_frame, text="Advanced Help", 
                             command=show_advanced_help)
        help_button.pack(side="left", padx=5)
        
        tk.Button(button_frame, text="Cancel", 
                command=dialog.destroy, width=8).pack(side="right", padx=5)
        tk.Button(button_frame, text="Connect", 
                command=on_ok, width=8, bg="#4CAF50", fg="white").pack(side="right", padx=5)
        
        # Wait for dialog to close
        dialog.wait_window()
        
        # Return the path if entered
        return result[0]

    def show_network_help(self):
        """Enhanced help for accessing network folders"""
        help_dialog = Toplevel(self.root)
        help_dialog.title("Network Share Help")
        help_dialog.geometry("600x450")
        
        # Make it transient to keep it on top of the main window
        help_dialog.transient(self.root)
        
        # Center the dialog
        help_dialog.update_idletasks()
        x = (help_dialog.winfo_screenwidth() - help_dialog.winfo_width()) // 2
        y = (help_dialog.winfo_screenheight() - help_dialog.winfo_height()) // 2
        help_dialog.geometry(f"+{x}+{y}")
        
        # Create a notebook with tabs
        notebook = ttk.Notebook(help_dialog)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # General tab
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="General")
        
        general_text = Text(general_frame, wrap=tk.WORD, padx=10, pady=10)
        general_text.pack(fill="both", expand=True)
        
        general_text.insert(tk.END, """Network Share Access - General Information

To access shared network folders (SMB/CIFS shares):

1. Direct Entry: You can type a network path directly in the format:
   • //server/share or \\\\server\\share

2. Path with credentials (if needed):
   • //username:password@server/share

3. Common network path issues:
   • Make sure the server is online and accessible from your network
   • Verify you have permission to access the shared folder
   • Some networks require you to be on the same LAN or VPN
   • Firewalls may block SMB/CIFS traffic (ports 139 and 445)

This application will attempt to access the path you provide. If connection 
fails, you may need to first mount/map the drive using your operating system's 
tools as described in the platform-specific tabs.
""")
        general_text.config(state="disabled")
        
        # Windows tab
        windows_frame = ttk.Frame(notebook)
        notebook.add(windows_frame, text="Windows")
        
        windows_text = Text(windows_frame, wrap=tk.WORD, padx=10, pady=10)
        windows_text.pack(fill="both", expand=True)
        
        windows_text.insert(tk.END, """Windows - Accessing Network Shares

Method 1: Map a Network Drive
1. Open File Explorer
2. Right-click on "This PC" and select "Map network drive..."
3. Choose a drive letter and enter the network path (\\\\server\\share)
4. Check "Connect using different credentials" if needed
5. Click "Finish" and enter credentials if prompted

Method 2: Direct Access
1. In File Explorer address bar, type \\\\server\\share
2. Press Enter
3. Enter credentials if prompted

Troubleshooting:
• Make sure Network Discovery is enabled
• Check Windows Defender Firewall settings
• Verify the remote computer is using SMB v1, v2, or v3 compatible with your Windows version
• Try accessing with full credentials: \\\\username:password@server\\share
""")
        windows_text.config(state="disabled")
        
        # Linux tab
        linux_frame = ttk.Frame(notebook)
        notebook.add(linux_frame, text="Linux")
        
        linux_text = Text(linux_frame, wrap=tk.WORD, padx=10, pady=10)
        linux_text.pack(fill="both", expand=True)
        
        linux_text.insert(tk.END, """Linux - Accessing Network Shares

Method 1: Mount using terminal
1. Create a mount point:
   sudo mkdir -p /mnt/networkshare

2. Mount the share:
   sudo mount -t cifs //server/share /mnt/networkshare -o username=user,password=pass

3. For permanent mounting, add to /etc/fstab:
   //server/share /mnt/networkshare cifs username=user,password=pass,uid=1000,gid=1000 0 0

Method 2: Using file manager
Most Linux file managers support entering network paths directly:
1. Open file manager (Nautilus, Dolphin, etc.)
2. Press Ctrl+L to edit location
3. Enter: smb://server/share
4. Enter credentials when prompted

Prerequisites:
• cifs-utils package must be installed:
   Ubuntu/Debian: sudo apt install cifs-utils
   Fedora/RHEL: sudo dnf install cifs-utils
""")
        linux_text.config(state="disabled")
        
        # macOS tab
        mac_frame = ttk.Frame(notebook)
        notebook.add(mac_frame, text="macOS")
        
        mac_text = Text(mac_frame, wrap=tk.WORD, padx=10, pady=10)
        mac_text.pack(fill="both", expand=True)
        
        mac_text.insert(tk.END, """macOS - Accessing Network Shares

Method 1: Using Finder
1. In Finder, click "Go" menu and select "Connect to Server..." (or press ⌘K)
2. Enter the server address: smb://server/share
3. Click "Connect"
4. Enter credentials when prompted

Method 2: Using Terminal
1. Create a mount point:
   mkdir -p ~/NetworkShares/myshare

2. Mount the share:
   mount -t smbfs //username:password@server/share ~/NetworkShares/myshare

Method 3: Auto-mount on login
1. Open System Preferences
2. Go to "Users & Groups"
3. Select your account and click "Login Items"
4. Add the network share to login items

Troubleshooting:
• Make sure SMB is enabled in Sharing settings
• Try different SMB versions: smb://server/share?SMB_VER=1.0
• Check your macOS Firewall settings
""")
        mac_text.config(state="disabled")
        
        # Add close button
        tk.Button(help_dialog, text="Close", command=help_dialog.destroy, width=10).pack(pady=10)

    def get_files(self, folder):
        files = []
        for root, _, filenames in os.walk(folder):
            for filename in filenames:
                files.append(os.path.join(root, filename))
            if not self.include_subfolders.get():
                break
        return files

    def show_preview(self, preview):
        self.preview = preview
        preview_window = Toplevel(self.root)
        preview_window.title("Preview")
        preview_window.geometry("700x500")

        # Add instructions
        tk.Label(preview_window, text="Review the changes below and click Execute to proceed", 
                 font=("Arial", 10)).pack(pady=10)

        # Create treeview with scrollbar
        frame = tk.Frame(preview_window)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        
        columns = ("Source", "Destination")
        tree = ttk.Treeview(frame, columns=columns, show='headings', yscrollcommand=scrollbar.set)
        scrollbar.config(command=tree.yview)
        
        tree.heading("Source", text="Source")
        tree.heading("Destination", text="Destination")
        tree.column("Source", width=350)
        tree.column("Destination", width=350)
        tree.pack(side="left", fill="both", expand=True)

        for src, dst in preview:
            tree.insert("", "end", values=(src, dst))

        # Button frame
        button_frame = tk.Frame(preview_window)
        button_frame.pack(fill="x", pady=10)
        
        # Add progress bar (initially hidden)
        progress_frame = tk.Frame(preview_window)
        progress_frame.pack(fill="x", padx=20, pady=10)
        progress_label = tk.Label(progress_frame, text="Progress:")
        progress_label.pack(side="left", padx=5)
        
        progress = ttk.Progressbar(progress_frame, orient="horizontal", 
                                  length=500, mode="determinate")
        progress.pack(side="left", fill="x", expand=True, padx=5)
        
        # Initially hide the progress bar
        progress_frame.pack_forget()
        
        # Store progress widgets in the instance for access from other methods
        self.progress_frame = progress_frame
        self.progress_bar = progress
        self.preview_window = preview_window
        
        cancel_button = tk.Button(button_frame, text="Cancel", command=preview_window.destroy)
        cancel_button.pack(side="right", padx=10)
        
        execute_button = tk.Button(button_frame, text="Execute", 
                           command=lambda: self.confirm_and_execute(preview_window, cancel_button, execute_button), 
                           bg="#4CAF50", fg="white")
        execute_button.pack(side="right", padx=10)
        
        # Save buttons for later access
        self.cancel_button = cancel_button
        self.execute_button = execute_button

        # Keep the preview window on top
        preview_window.attributes('-topmost', True)
        preview_window.transient(self.root)

    def confirm_and_execute(self, window, cancel_button, execute_button):
        """Show confirmation dialog as part of the preview window"""
        
        # Create a custom confirmation dialog within the preview window
        confirm_frame = tk.Frame(window, bd=2, relief="groove", bg="#f0f0f0")
        confirm_frame.place(relx=0.5, rely=0.5, anchor="center", width=350, height=150)
        
        # Add confirmation message
        tk.Label(confirm_frame, text="Are you sure you want to organize the files?", 
                 bg="#f0f0f0", font=("Arial", 11)).pack(pady=(20, 15))
        
        # Add buttons
        btn_frame = tk.Frame(confirm_frame, bg="#f0f0f0")
        btn_frame.pack(pady=10)
        
        def on_yes():
            confirm_frame.destroy()
            # Show progress bar
            self.progress_frame.pack(fill="x", padx=20, pady=10, before=self.cancel_button.master)
            self.progress_bar["maximum"] = len(self.preview)
            self.progress_bar["value"] = 0
            
            # Disable buttons during execution
            cancel_button.config(state="disabled")
            execute_button.config(state="disabled")
            
            # Run the organization in a separate thread to keep UI responsive
            self.log("Starting file organization...")
            threading.Thread(target=self.execute_organization_with_progress, 
                            args=(window,), daemon=True).start()
        
        def on_no():
            confirm_frame.destroy()
        
        tk.Button(btn_frame, text="Yes", command=on_yes, 
                 bg="#4CAF50", fg="white", width=10).pack(side="left", padx=10)
        tk.Button(btn_frame, text="No", command=on_no, 
                 bg="#f44336", fg="white", width=10).pack(side="left", padx=10)
        
        # Ensure the preview window stays on top during confirmation
        window.lift()
        window.focus_force()

    def execute_organization_with_progress(self, window):
        """Execute organization with progress updates"""
        if not self.preview:
            messagebox.showerror("Error", "Please preview the changes first!")
            return

        self.log(f"Starting organization of {len(self.preview)} files")
        success_count = 0
        skipped_count = 0
        progress_value = 0
        
        for src, dst in self.preview:
            try:
                # Skip if source and destination directories are the same
                if os.path.dirname(src) == os.path.dirname(dst):
                    skip_message = f"Skipped {os.path.basename(src)} - already in correct location"
                    self.status_label.config(text=skip_message)
                    self.log(skip_message)
                    skipped_count += 1
                else:
                    # Create destination directory if it doesn't exist
                    dst_dir = os.path.dirname(dst)
                    os.makedirs(dst_dir, exist_ok=True)
                    
                    # Get unique filename if needed
                    dst_filename = os.path.basename(dst)
                    if os.path.exists(dst):
                        dst_filename = self.generate_unique_filename(dst_dir, dst_filename)
                        self.log(f"Renamed {os.path.basename(dst)} to {dst_filename} to avoid conflict")
                    
                    # Move the file
                    final_dst = os.path.join(dst_dir, dst_filename)
                    shutil.move(src, final_dst)
                    self.log(f"Moved: {src} -> {final_dst}")
                    success_count += 1
            except Exception as e:
                error_message = f"Error moving {src}: {e}"
                self.log(f"ERROR: {error_message}")
                # Using after() to schedule messagebox from the main thread
                self.root.after(0, lambda: messagebox.showerror("Error", error_message))
            
            # Update progress
            progress_value += 1
            # Use after() to safely update the progress from the main thread
            self.root.after(0, lambda v=progress_value: self.update_progress(v))
            
            # Update every 10 files processed or give the UI a chance to update
            if progress_value % 10 == 0:
                time.sleep(0.01)  # Brief pause to allow UI to update

        # Delete empty folders if option is enabled
        if self.delete_empty_folders.get():
            self.log("Checking for empty folders to delete...")
            self.remove_empty_dirs(self.path.get())

        message = f"Successfully organized {success_count} of {len(self.preview)} files! Skipped {skipped_count} files."
        self.status_label.config(text=message)
        self.log(message)
        
        # Using after() to schedule messagebox from the main thread
        self.root.after(0, lambda: messagebox.showinfo("Success", 
                            f"Successfully organized {success_count} of {len(self.preview)} files!\n"
                            f"Skipped {skipped_count} files (already in correct location)"))
                            
        # Close the window after completion
        self.root.after(0, lambda: window.destroy())
        
        # Clear the preview
        self.preview = []

    def update_progress(self, value):
        """Update the progress bar"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar["value"] = value
            
            # Calculate percentage
            percentage = int((value / len(self.preview)) * 100)
            self.progress_bar.master.nametowidget(self.progress_bar.master.winfo_children()[0].winfo_name()).config(
                text=f"Progress: {percentage}%")
        
    def generate_unique_filename(self, destination, filename):
        """Generate a unique filename if the original file already exists at the destination"""
        base, ext = os.path.splitext(filename)
        counter = 1
        new_filename = filename
        
        while os.path.exists(os.path.join(destination, new_filename)):
            new_filename = f"{base} ({counter}){ext}"
            counter += 1
            
        return new_filename

    def preview_by_type(self):
        folder = self.path.get()
        if not folder:
            messagebox.showerror("Error", "Please select a folder first!")
            return

        self.log(f"Generating preview for organizing files by type in {folder}")
        preview = []
        for file_path in self.get_files(folder):
            if os.path.isfile(file_path):
                ext = os.path.splitext(file_path)[1][1:] or "NO_EXTENSION"
                ext_folder = os.path.join(folder, ext.upper())
                dest_path = os.path.join(ext_folder, os.path.basename(file_path))
                preview.append((file_path, dest_path))

        if not preview:
            message = "No files found to organize!"
            messagebox.showinfo("No Files", message)
            self.log(message)
            return
            
        self.show_preview(preview)
        message = f"Preview ready: {len(preview)} files to organize by type"
        self.status_label.config(text=message)
        self.log(message)

    def get_date_from_filename(self, filename):
        """Try to extract a date from filename patterns like YYYYMMDD, YYYY-MM-DD, etc."""
        # Common date patterns in filenames
        patterns = [
            # YYYY-MM-DD or YYYY_MM_DD
            r'(?P<year>\d{4})[-_](?P<month>\d{2})[-_](?P<day>\d{2})',
            # YYYYMMDD
            r'(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})',
            # DD-MM-YYYY or DD_MM_YYYY
            r'(?P<day>\d{2})[-_](?P<month>\d{2})[-_](?P<year>\d{4})',
            # MM-DD-YYYY or MM_DD_YYYY
            r'(?P<month>\d{2})[-_](?P<day>\d{2})[-_](?P<year>\d{4})',
            # Common camera/phone formats like IMG_20181216_140830
            r'IMG[_-](?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})[_-]',
            # Generic pattern for finding dates anywhere in the filename
            r'(?<!\d)(?P<year>20\d{2})(?P<month>0[1-9]|1[0-2])(?P<day>[0-3]\d)(?!\d)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                try:
                    year = int(match.group('year'))
                    month = int(match.group('month'))
                    day = int(match.group('day'))
                    
                    # Validate date components
                    if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                        try:
                            return datetime(year, month, day)
                        except ValueError:
                            # Invalid date like Feb 30
                            continue
                except:
                    continue
        return None

    def get_date_from_exif(self, file_path):
        """Extract date from image EXIF data if available"""
        if not HAS_PIL:
            return None
            
        try:
            if not file_path.lower().endswith(('.jpg', '.jpeg', '.tiff', '.png')):
                return None
                
            image = Image.open(file_path)
            if not hasattr(image, '_getexif') or image._getexif() is None:
                return None
                
            exif_data = {
                TAGS.get(tag, tag): value
                for tag, value in image._getexif().items()
            }
            
            # Try different date fields
            date_fields = ['DateTimeOriginal', 'DateTime', 'CreateDate', 'DateTimeDigitized']
            
            for field in date_fields:
                if field in exif_data and exif_data[field]:
                    # Format usually like "2020:01:30 14:31:26"
                    date_str = str(exif_data[field])
                    try:
                        return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        try:
                            # Try another common format
                            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            continue
            
            return None
        except Exception as e:
            self.log(f"Error reading EXIF data from {file_path}: {e}")
            return None
            
    def get_file_creation_date(self, file_path):
        """Get file creation date across different platforms"""
        try:
            # For Windows
            if platform.system() == 'Windows':
                return datetime.fromtimestamp(os.path.getctime(file_path))
            # For macOS
            elif platform.system() == 'Darwin':
                stat = os.stat(file_path)
                return datetime.fromtimestamp(stat.st_birthtime)
            # For Linux (note: Linux doesn't store creation time, so we use a workaround)
            else:
                # Use the earliest time between modification and access time as best approximation
                path = Path(file_path)
                stat = path.stat()
                return datetime.fromtimestamp(min(stat.st_mtime, stat.st_atime))
        except Exception as e:
            self.log(f"Error getting creation date for {file_path}: {e}")
            # Fall back to modification time if there's an error
            return datetime.fromtimestamp(os.path.getmtime(file_path))
        
    def get_file_date(self, file_path):
        """Get the best date for a file based on selected date source"""
        basename = os.path.basename(file_path)
        date_source = self.date_source.get()
        
        # Use filename date if selected or using all sources
        if date_source in ["filename", "all"]:
            date_from_name = self.get_date_from_filename(basename)
            if date_from_name:
                self.log(f"Using date from filename for {basename}: {date_from_name.strftime('%Y-%m-%d')}")
                return date_from_name
        
        # Use EXIF data if selected or using all sources
        if date_source in ["exif", "all"]:
            date_from_exif = self.get_date_from_exif(file_path)
            if date_from_exif:
                self.log(f"Using date from EXIF data for {basename}: {date_from_exif.strftime('%Y-%m-%d')}")
                return date_from_exif
        
        # Use file creation time
        date_from_file = self.get_file_creation_date(file_path)
        self.log(f"Using creation date for {basename}: {date_from_file.strftime('%Y-%m-%d')}")
        return date_from_file

    def preview_by_date(self):
        folder = self.path.get()
        if not folder:
            messagebox.showerror("Error", "Please select a folder first!")
            return

        self.log(f"Generating preview for organizing files by date in {folder}")
        preview = []
        
        # Get date format pattern based on selection
        date_format = {
            "year": "%Y",
            "month": "%Y-%m",
            "day": "%Y-%m-%d"
        }.get(self.date_format.get(), "%Y-%m-%d")
        
        for file_path in self.get_files(folder):
            if os.path.isfile(file_path):
                file_date = self.get_file_date(file_path)
                date_folder = os.path.join(folder, file_date.strftime(date_format))
                dest_path = os.path.join(date_folder, os.path.basename(file_path))
                preview.append((file_path, dest_path))

        if not preview:
            message = "No files found to organize!"
            messagebox.showinfo("No Files", message)
            self.log(message)
            return
            
        self.show_preview(preview)
        message = f"Preview ready: {len(preview)} files to organize by date"
        self.status_label.config(text=message)
        self.log(message)

    def execute_organization(self):
        if not self.preview:
            messagebox.showerror("Error", "Please preview the changes first!")
            return

        self.log(f"Starting organization of {len(self.preview)} files")
        success_count = 0
        skipped_count = 0
        for src, dst in self.preview:
            try:
                # Skip if source and destination directories are the same
                if os.path.dirname(src) == os.path.dirname(dst):
                    skip_message = f"Skipped {os.path.basename(src)} - already in correct location"
                    self.status_label.config(text=skip_message)
                    self.log(skip_message)
                    skipped_count += 1
                    continue
                
                # Create destination directory if it doesn't exist
                dst_dir = os.path.dirname(dst)
                os.makedirs(dst_dir, exist_ok=True)
                
                # Get unique filename if needed
                dst_filename = os.path.basename(dst)
                if os.path.exists(dst):
                    dst_filename = self.generate_unique_filename(dst_dir, dst_filename)
                    self.log(f"Renamed {os.path.basename(dst)} to {dst_filename} to avoid conflict")
                
                # Move the file
                final_dst = os.path.join(dst_dir, dst_filename)
                shutil.move(src, final_dst)
                self.log(f"Moved: {src} -> {final_dst}")
                success_count += 1
            except Exception as e:
                error_message = f"Error moving {src}: {e}"
                messagebox.showerror("Error", error_message)
                self.log(f"ERROR: {error_message}")

        # Delete empty folders if option is enabled
        if self.delete_empty_folders.get():
            self.log("Checking for empty folders to delete...")
            self.remove_empty_dirs(self.path.get())

        message = f"Successfully organized {success_count} of {len(self.preview)} files! Skipped {skipped_count} files."
        messagebox.showinfo("Success", 
                           f"Successfully organized {success_count} of {len(self.preview)} files!\n"
                           f"Skipped {skipped_count} files (already in correct location)")
        self.preview = []
        self.status_label.config(text=message)
        self.log(message)

    def get_file_category(self, file_path):
        """Determine the category of a file based on its extension"""
        _, extension = os.path.splitext(file_path)
        extension = extension.lower()  # Normalize extension to lowercase
        
        for category, extensions in self.category_definitions.items():
            if extension in extensions:
                return category
                
        # If we don't recognize the extension, return "Other"
        return "Other"
    
    def preview_by_category(self):
        """Preview organizing files by category (Images, Documents, Videos, etc.)"""
        folder = self.path.get()
        if not folder:
            messagebox.showerror("Error", "Please select a folder first!")
            return

        self.log(f"Generating preview for organizing files by category in {folder}")
        preview = []
        
        # Count files in each category for logging
        category_counts = {}
        
        for file_path in self.get_files(folder):
            if os.path.isfile(file_path):
                category = self.get_file_category(file_path)
                # Keep track of how many files in each category
                if category not in category_counts:
                    category_counts[category] = 0
                category_counts[category] += 1
                
                category_folder = os.path.join(folder, category)
                dest_path = os.path.join(category_folder, os.path.basename(file_path))
                preview.append((file_path, dest_path))

        if not preview:
            message = "No files found to organize!"
            messagebox.showinfo("No Files", message)
            self.log(message)
            return
        
        # Log the category distribution
        self.log("Files by category:")
        for category, count in category_counts.items():
            self.log(f"  {category}: {count} files")
            
        self.show_preview(preview)
        message = f"Preview ready: {len(preview)} files to organize by category"
        self.status_label.config(text=message)
        self.log(message)
    
    def show_date_help(self):
        """Show help information about date sources"""
        help_window = Toplevel(self.root)
        help_window.title("Date Source Help")
        help_window.geometry("500x400")
        
        text = Text(help_window, wrap=tk.WORD, padx=10, pady=10)
        text.pack(fill="both", expand=True)
        
        help_text = """Date Source Options:

1. All Sources (Filename → EXIF → File Date)
   The application will try to extract the date in this order:
   - First from the filename (if it contains a date pattern)
   - Then from EXIF data (for image files)
   - Finally from the file's creation date

2. Filename Only
   Only looks for date patterns in the filename, such as:
   - YYYY-MM-DD (e.g., photo-2023-05-15.jpg)
   - YYYYMMDD (e.g., 20230515_party.jpg)
   - DD-MM-YYYY (e.g., 15-05-2023.jpg)
   - MM-DD-YYYY (e.g., 05-15-2023.jpg)
   Falls back to file creation date if no pattern is found.

3. EXIF Only
   Only extracts dates from image EXIF metadata. This works for
   photos from cameras and smartphones that store the date the
   photo was taken in the file's metadata.
   Falls back to file creation date if no EXIF data is found.

4. File Date Only
   Uses only the file's creation timestamp to organize files.
   This is the date when the file was created on your system.
   
   Note: On Linux, true creation date is not available, so we use
   the earliest of modification/access times as an approximation.

Date Sorting Level:

1. By Year (YYYY)
   Creates folders like "2023" for each year

2. By Month (YYYY-MM)
   Creates folders like "2023-05" for each month of each year

3. By Day (YYYY-MM-DD)
   Creates folders like "2023-05-15" for each day

Note: For all options except "File Date Only", if the selected
data source doesn't provide a date, the app will fall back to using
the file's creation date.
"""
        
        text.insert(tk.END, help_text)
        text.config(state="disabled")
        
        # Add close button
        close_button = tk.Button(help_window, text="Close", command=help_window.destroy)
        close_button.pack(pady=10)

    def confirm_delete_empty(self):
        """Confirm deletion of empty folders if option is selected"""
        if self.delete_empty_folders.get():
            answer = messagebox.askokcancel(
                "Confirm Delete Empty Folders", 
                "Enabling this option will delete empty folders after organizing files.\n\n"
                "Are you sure you want to enable this feature?",
                icon=messagebox.WARNING
            )
            if not answer:
                self.delete_empty_folders.set(False)
            else:
                self.log("Delete empty folders option enabled")
        else:
            self.log("Delete empty folders option disabled")
        
        # Save the config when this option changes
        self.save_config()
    
    def is_dir_empty(self, path):
        """Check if a directory is empty."""
        try:
            # Check if directory contains any files or subdirectories
            with os.scandir(path) as entries:
                return next(entries, None) is None
        except (FileNotFoundError, PermissionError, NotADirectoryError):
            # If there's an error accessing the directory, consider it non-empty for safety
            return False
            
    def remove_empty_dirs(self, path):
        """Recursively remove empty directories starting from path."""
        if not os.path.isdir(path):
            return
            
        # Process all subdirectories first
        for item in os.listdir(path):
            subdir = os.path.join(path, item)
            if os.path.isdir(subdir):
                self.remove_empty_dirs(subdir)
                
        # Check if current directory is empty now
        if self.is_dir_empty(path) and path != self.path.get():  # Don't delete the root folder
            try:
                os.rmdir(path)
                self.log(f"Removed empty directory: {path}")
            except Exception as e:
                self.log(f"Error removing directory {path}: {e}")

if __name__ == '__main__':
    root = tk.Tk()
    app = FileOrganizerApp(root)
    root.mainloop()
