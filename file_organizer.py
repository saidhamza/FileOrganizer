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
        self.root.minsize(600, 650)    # Increased minimum height
        self.root.resizable(True, True)

        # Config file path
        self.config_file = os.path.join(os.path.expanduser("~"), ".file_organizer_config.json")
        
        # Load config
        self.config = self.load_config()
        
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

        # File category definitions
        self.category_definitions = {
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".svg", ".heic"],
            "Documents": [".doc", ".docx", ".pdf", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"],
            "Videos": [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg", ".mts", ".m2ts", ".3gp"],
            "Audio": [".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a", ".wma", ".aiff"],
            "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"],
            "Code": [".py", ".js", ".html", ".css", ".java", ".c", ".cpp", ".php", ".rb", ".go", ".rs", ".ts", ".sh", ".json", ".xml"],
            "Executables": [".exe", ".msi", ".app", ".bat", ".sh", ".apk", ".deb", ".rpm"]
        }

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
        
        # First try the standard dialog
        folder_selected = filedialog.askdirectory(initialdir=initial_dir)
        
        # If user cancelled or if we want to enter a network path manually
        if not folder_selected:
            # Check if user wants to enter a network path
            if messagebox.askyesno("Network Path", 
                                  "Do you want to enter a network path manually?\n\n"
                                  "For example: //server/share or \\\\server\\share"):
                folder_selected = self.manual_network_path_input()
        
        if folder_selected:
            self.path.set(folder_selected)
            self.last_directory = folder_selected
            self.add_to_recent_folders(folder_selected)
            self.save_config()
            self.status_label.config(text=f"Selected folder: {folder_selected}")
            self.log(f"Selected folder: {folder_selected}")
    
    def manual_network_path_input(self):
        """Dialog for manual network path input"""
        dialog = Toplevel(self.root)
        dialog.title("Enter Network Path")
        dialog.geometry("400x150")
        dialog.grab_set()
        
        result = [None]  # Use list to store result from inner function
        
        tk.Label(dialog, text="Enter Network Path:", font=("Arial", 10)).pack(pady=10)
        path_var = tk.StringVar()
        path_entry = tk.Entry(dialog, textvariable=path_var, width=50)
        path_entry.pack(pady=5)
        path_entry.focus_set()
        
        # Example label
        tk.Label(dialog, text="Example: //server/share or \\\\server\\share", 
                font=("Arial", 8)).pack()
        
        def on_ok():
            path = path_var.get().strip().replace("\\", "/")
            if path:
                result[0] = path
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        button_frame = tk.Frame(dialog)
        button_frame.pack(fill="x", pady=10)
        
        tk.Button(button_frame, text="Cancel", command=on_cancel).pack(side="right", padx=10)
        tk.Button(button_frame, text="OK", command=on_ok).pack(side="right", padx=10)
        
        # Wait for dialog to close
        dialog.wait_window()
        return result[0]
    
    def show_network_help(self):
        """Show help for accessing network folders"""
        help_dialog = Toplevel(self.root)
        help_dialog.title("Network Path Help")
        help_dialog.geometry("500x300")
        
        text = Text(help_dialog, wrap=tk.WORD, padx=10, pady=10)
        text.pack(fill="both", expand=True)
        
        help_text = """Accessing Network Folders:

1. You can directly type a network path into the folder field, such as:
   //server/share or \\\\server\\share

2. When using the Browse button, you can select "Yes" to enter a network
   path manually if the standard folder dialog doesn't show network paths.

3. For authenticated shares (requiring username/password):
   
   • On Windows: First map the network drive in File Explorer
     (Right-click This PC → Map network drive...)
   
   • On Linux: Use the file browser to mount the share first, or use
     the 'mount' command in terminal:
     
     sudo mount -t cifs //server/share /mnt/mountpoint -o username=user,password=pass

   • On macOS: Use Finder → Go → Connect to Server... (⌘K)

Once mounted, you can select the mounted share through the Browse button.
"""
        
        text.insert(tk.END, help_text)
        text.config(state="disabled")
        
        tk.Button(help_dialog, text="Close", command=help_dialog.destroy).pack(pady=10)

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

    def confirm_and_execute(self, window, cancel_button, execute_button):
        if messagebox.askyesno("Confirm", "Are you sure you want to organize the files?"):
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
