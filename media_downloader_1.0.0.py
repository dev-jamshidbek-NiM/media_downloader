from main import VideoDownloader
import os
import time
import pickle
import threading
import tkinter as tk
import customtkinter as ctk
from datetime import datetime
from tkinter import filedialog, messagebox
from customtkinter import CTkLabel, CTkEntry, CTkButton, CTkOptionMenu, CTkFrame, CTkSlider, CTkTextbox
import pyperclip
import webbrowser
import hashlib
import requests
from customtkinter import CTkProgressBar
import concurrent.futures
from cryptography.fernet import Fernet
import re
from tkinterdnd2 import DND_ALL, TkinterDnD


def sanitize_filename(url):
    """
    Sanitize the URL to create a valid filename by removing invalid characters.
    """
    # Replace all invalid characters with an underscore
    sanitized_name = re.sub(r'[<>:"/\\|?*\'"!@#$%^&+=\[\]{}();,~` ]', '_', url)

    # Optionally, you can truncate the name to a specific length for safety
    max_length = 245  # Max length for most file systems
    sanitized_name = sanitized_name[:max_length]

    return sanitized_name

counter = 0

def generate_numeric_filename():
    global counter
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S-%f")  # Includes microseconds
    counter += 1
    return f"{timestamp}-{counter:04d}"  # Counter ensures uniqueness

class ImageDownloaderApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        # Initialize the settings
        self.settings_file = "settings.ini"
        self.settings = self.load_settings()
        self.downloader = VideoDownloader()

        self.title("Image Downloader")
        self.geometry("830x500")  # Set a fixed window size
        self.minsize(700, 400)
        
        # Check if the .ico file exists
        if os.path.exists("icon/icon.ico"):
            # Set the .ico file as the window icon
            self.iconbitmap("icon/icon.ico")
        
        self.configure(bg="#1e1e1e")

        self.home_window = None
        self.show_home_window_number = 0

        self.settings_window = None
        self.show_settings_window_number = 0

        self.about_window = None
        self.show_about_window_number = 0

        # Store the selected file path and track changes
        self.download_cancelled = False
        self.selected_file_path = None
        self.url_entry_link = None
        self.content = None
        self.selected_img_format = None
        self.status_display_changed = False
        self.downloading_content = False
        self.downloaded_media_count = 0
        self.total_media_links = 0
        self.download_path = self.settings.get("download_path")
        self.media_urls = None
        
        
        # Available resolutions
        self.resolutions = ['Manual', '144p', '240p', '360p', '480p', '720p', '1080p']
        # Available resolutions
        self.media_types = ['Video', 'Audio', 'Image']
        
        # Variables for selected media type and resolution
        self.selected_media_type = "Video"
        self.selected_auto_download_res = "Manual"

        # StringVars for keeping selected values
        self.selected_media_type_var = ctk.StringVar(value=self.selected_media_type)
        self.selected_auto_download_res_var = ctk.StringVar(value=self.selected_auto_download_res)
        

        # Variables
        self.clipboard_monitoring = False
        self.clipboard_monitor_thread = None
        # File path to save the clipboard links
        self.clipboard_file_path = "clipboard.txt"
        # Create buttons
        self.resolution_buttons = []
        

        # App opened time
        self.app_opened_time = datetime.now().strftime("%Y-%m-%d   %H:%M:%S")

        # Sidebar for modern menu
        self.sidebar_frame = None
        self.create_sidebar()
        self.show_home()
        

    
    def on_resolution_selected(self, selected_value):
        self.selected_auto_download_res = selected_value
        self.selected_auto_download_res_var.set(selected_value)

    def on_media_type_selected(self, selected_value):
        self.selected_media_type = selected_value
        self.selected_media_type_var.set(selected_value)


    def show_home(self):
        if self.settings_window and self.show_settings_window_number >= 1:
            self.settings_window.pack_forget()
            self.show_settings_window_number -= 1
        if self.about_window and self.show_about_window_number >= 1:
            self.about_window.pack_forget()
            self.show_about_window_number -= 1

        if self.show_home_window_number == 0:
            self.home_window = tk.Frame(self, bg="#1e1e1e")
            self.home_window.pack(side="left", fill="both", expand=True)
            self.show_home_window_number += 1
            

                
            # Frame for format selection and progress bar
            self.options_frame = tk.Frame(self.home_window, bg="#1e1e1e")
            self.options_frame.pack(pady=(15, 10), fill="x")

            # Real-time display and app opened time
            self.time_label = CTkLabel(
                self.options_frame,
                text=f"Opened: {self.app_opened_time}       Time: {datetime.now().strftime('%H:%M:%S')}       Elapsed: 0:00:00",
                fg_color="#1e1e1e",
                text_color="#ffffff",
                font=("Arial", 14, "bold")
            )
            self.time_label.pack(pady=(0,10), fill="x")
            self.update_real_time()
            
            self.status_frame = tk.Frame(self.options_frame, bg="#1e1e1e")
            self.status_frame.pack(side="left", expand=True, fill="both")
            
            # Status label
            self.status_label = ctk.CTkLabel(self.status_frame, text="Status", text_color="green", font=("Arial", 15))
            self.status_label.pack(fill="x", expand=True, padx=(10, 10), pady=(0, 5))
                
            # Progress bar
            self.progress_bar = CTkProgressBar(self.status_frame)
            self.progress_bar.pack(fill="x", expand=True, padx=(10, 10), pady=(5, 5))
            self.progress_bar.set(0)
            self.progress_bar.configure(height=20)
            
            # Resolution menu
            self.resolution_menu = CTkOptionMenu(
                self.options_frame,
                variable=self.selected_auto_download_res_var,  # Use StringVar here
                values=self.resolutions,
                command=self.on_resolution_selected,
                width=130,
            )
            self.resolution_menu.pack(padx=(10, 10), pady=(5, 5))

        
            self.toggle_clipboard_button = CTkButton(self.options_frame, text="Start Clipboard", command=self.toggle_clipboard_monitoring, width=130)
            self.toggle_clipboard_button.pack(side="left", padx=(10, 10), pady=(5, 5))

            

            # Frame for URL entry and file button
            self.url_frame = tk.Frame(self.home_window, bg="#1e1e1e")
            self.url_frame.pack(pady=(10, 5), fill="x")

            # Entry for image URLs
            self.url_entry = CTkEntry(self.url_frame, placeholder_text="Enter image URL manually", width=200)
            self.url_entry.pack(side="left", padx=(10, 5), fill="x", expand=True)

            # Bind Ctrl+A to select all text
            self.url_entry.bind('<Control-a>', self.select_all)
            
            self.or_label = CTkLabel(self.url_frame, text="or",
                                     text_color="white", font=("Arial", 17))
            self.or_label.pack(side="left", padx=(5, 5))

            # Button to select file with image URLs
            self.file_button = CTkButton(self.url_frame, text="Choose IMG URL File", command=self.select_file,
                                         width=100)
            self.file_button.pack(side="left", padx=(5, 5))
            
            
            # Media type menu
            self.media_menu = CTkOptionMenu(
                self.url_frame,
                variable=self.selected_media_type_var,  # Use StringVar here
                values=self.media_types,
                command=self.on_media_type_selected,
                width=130,
            )
            self.media_menu.pack(side="left", padx=(5, 10))
        
            # Modern Status Display Textbox
            self.status_display = CTkTextbox(self.home_window, height=10, fg_color="#2b2b2b", text_color="white",
                                            corner_radius=8, wrap="word")
            self.status_display.pack(padx=10, pady=(5, 5), fill="both", expand=True)
            self.status_display.configure(font=("Arial", self.settings.get('text_size')))
            self.status_display.drop_target_register(DND_ALL)
            self.status_display.dnd_bind('<<Drop>>', self.handle_drop)


            
            
            # Frame for buttons
            self.button_frame = tk.Frame(self.home_window, bg="#1e1e1e")
            self.button_frame.pack(pady=(10, 10), fill="x")

            # Create update Button
            self.update_file_button = CTkButton(self.button_frame, text="Update File", command=self.update_button_command, width=100)
            self.update_file_button.pack(side="left", padx=(10, 5))
            
            # Submit to encryption
            self.submit_to_encrypton_button = CTkButton(self.button_frame, text="Encrypt and Save",
                                                        command=self.save_encrypted_data,
                                                        width=100)
            self.submit_to_encrypton_button.pack(side="left", padx=5)
            
            # Create Save As Button
            self.save_as_button = CTkButton(self.button_frame, text="Save As", command=self.save_as_file, width=100)
            self.save_as_button.pack(side="left", padx=5)

            # Submit button
            self.submit_button = CTkButton(self.button_frame, text="Download", command=self.start_download,
                                           width=100)
            self.submit_button.pack(side="right", padx=(5, 10))

            # Cancel button
            self.cancel_button = CTkButton(self.button_frame, text="Cancel", command=self.cancel_download, width=100)
            self.cancel_button.pack(side="right", padx=5)

            # Refresh button
            self.refresh_button = CTkButton(self.button_frame, text="Refresh", command=self.refresh_home, width=100)
            self.refresh_button.pack(side="right", padx=5)

            # Bind event to detect changes in the status display
            self.status_display.bind("<<Modified>>", self.on_status_display_modified)

            # Bind Ctrl+A to select all text
            self.url_entry.bind('<Control-a>', self.select_all)
            self.status_display.bind('<Control-a>', self.select_all)


            # Attach resolution_frame to home_window
            self.resolution_frame = ctk.CTkFrame(self.home_window, fg_color="#ffffff", height=50)
            self.resolution_frame.pack(padx=10, pady=(20, 15), fill="both")
            self.resolution_frame.bind("<Configure>", self.adjust_buttons)
                       
            if self.content:
                self.status_display.insert(1.0, self.content)
    
    def adjust_buttons(self, event=None):
        """Adjust the layout of the buttons dynamically."""
        # Clear the existing grid
        for widget in self.resolution_frame.winfo_children():
            widget.grid_forget()

        # Check if buttons exist in the list
        if not self.resolution_buttons:
            return  # No buttons to adjust

        # Calculate the number of buttons that fit in one row
        frame_width = self.resolution_frame.winfo_width()
        button_width = 120  # Include button width and padding
        buttons_per_row = max(frame_width // button_width, 1)  # Ensure at least one button per row

        # Place buttons in the grid
        for index, button in enumerate(self.resolution_buttons):
            row = index // buttons_per_row
            col = index % buttons_per_row
            button.grid(row=row, column=col, padx=5, pady=5, sticky="ew")

        
        
    def select_all(self, event):
        widget = event.widget

        if isinstance(widget, ctk.CTkEntry):
            # For CTkEntry widget
            widget.select_range(0, 'end')  # Selects all text in the Entry widget
        elif isinstance(widget, tk.Text):
            # For Text widget
            widget.tag_add("sel", "1.0", "end")  # Select all text in the Text widget
            widget.mark_set("insert", "1.0")  # Move cursor to the start of the text
            widget.see("insert")  # Scroll to the cursor (if needed)
        else:
            event.widget.select_range(0, 'end')  # Selects all text in the Entry widget

        return 'break'  # Prevents further processing of the event
    
    
    def monitor_clipboard(self):
        clipboard_seen_links = set()  # To keep track of links already saved

        # Monitor clipboard in a loop
        while self.clipboard_monitoring:
            clipboard_content = pyperclip.paste().strip()

            # Check if clipboard content is not empty and not already processed
            if clipboard_content and clipboard_content not in clipboard_seen_links:
                clipboard_seen_links.add(clipboard_content)  # Mark as seen (without newline)

                # Ensure download is not cancelled
                if not self.downloading_content:
                    # Add content to the display widget
                    self.status_display.insert(tk.END, clipboard_content + "\n")

                    # Optionally, store the full content of the display for later use
                    self.content = self.status_display.get(1.0, tk.END)

            time.sleep(2)  # Poll clipboard every 2 seconds

    def toggle_clipboard_monitoring(self):
        if self.clipboard_monitoring:
            # Stop monitoring
            self.clipboard_monitoring = False
            self.toggle_clipboard_button.configure(text="Start Clipboard")
        else:
            # Start monitoring in a new thread
            self.clipboard_monitoring = True
            self.toggle_clipboard_button.configure(text="Stop Clipboard")
            self.clipboard_monitor_thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
            self.clipboard_monitor_thread.start()

    def save_as_file(self):
        # Get content from the status display
        self.content = self.status_display.get("1.0", tk.END).strip()  # Remove extra whitespace and newline

        # Check if there's content to save
        if not self.content or self.content.split('\n')[-1]=="No content to save. Please add some text.":  # If content is empty
            self.status_display.insert(tk.END, "No content to save. Please add some text.\n")
            return

        # Open a file dialog to select the save location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[
                ("Text Files", "*.txt"),
                ("PDF Files", "*.pdf"),
                ("Word Documents", "*.docx"),
                ("Excel Files", "*.xlsx"),
                ("All Files", "*.*")
            ],
            title="Save As"
        )

        # Proceed only if a file path is selected
        if file_path:
            try:
                # Write content to the file
                if file_path.endswith(".txt") or file_path.endswith(".pdf"):
                    with open(file_path, "w", encoding="utf-8") as file:
                        file.write(self.content)

                elif file_path.endswith(".docx"):
                    from docx import Document
                    doc = Document()
                    doc.add_paragraph(self.content)
                    doc.save(file_path)
                    
                elif file_path.endswith(".xlsx"):
                    import openpyxl
                    wb = openpyxl.Workbook()
                    ws = wb.active
                    for i, line in enumerate(self.content.splitlines(), start=1):
                        ws.cell(row=i, column=1, value=line)
                    wb.save(file_path)
                    

                # Notify the user of success
                self.status_display.insert(tk.END, f"\n\nFile saved successfully at: {file_path}\n")
            except Exception as e:
                # Handle errors during the save process
                self.status_display.insert(tk.END, f"\n\nError saving file: {e}\n")

    def handle_drop(self, event):
        if not self.downloading_content and event.data not in self.status_display.get(1.0, tk.END).split('\n'):  
            # print(f"Dropped data: {event.data}")
            self.status_display.insert(tk.END, event.data + "\n")
            self.content = self.status_display.get(1.0, tk.END)
        
    def create_sidebar(self):
        """Create a sidebar menu on the left with icons and labels."""
        self.sidebar_frame = CTkFrame(self, width=120, corner_radius=0, fg_color="#2e2e2e")
        self.sidebar_frame.pack(side="left", fill="y")

        # Keep track of the currently selected button
        self.selected_button = None

        # Sidebar buttons with explicit attributes
        self.home_button = self.add_sidebar_button("Home", self.show_home)  # Assign to self.home_button
        self.settings_button = self.add_sidebar_button("Settings", self.show_settings)
        self.help_button = self.add_sidebar_button("Help", self.show_about)
        self.quit_button = self.add_sidebar_button("Quit", self.quit_app)

        # Automatically select the Home button when the app starts
        if self.home_button:  # Ensure the button was created successfully
            self.select_button(self.home_button, self.show_home)

    def add_sidebar_button(self, text, command):
        """Helper function to add a button to the sidebar."""
        button = CTkButton(
            self.sidebar_frame,
            text=text,
            command=lambda: self.select_button(button, command),
            width=120,
            fg_color="#3a3a3a",
            text_color="white",
            corner_radius=5,
        )
        button.pack(pady=10, padx=10)
        return button  # Return the created button

    def select_button(self, button, command):
        """Highlight the selected button and reset others."""
        if not button:  # Avoid errors if button is None
            return

        # Reset the style of the previously selected button
        if self.selected_button:
            self.selected_button.configure(fg_color="#3a3a3a", text_color="white")

        # Highlight the newly selected button
        button.configure(fg_color="#2d5efc", text_color="white")  # Use your preferred highlight color
        self.selected_button = button

        # Execute the associated command
        command()

    def refresh_home(self):
        if self.download_cancelled:
            self.progress_bar.set(0)
            self.status_display.delete(1.0, tk.END)
            self.selected_file_path = None
            self.content = None
            self.url_entry_link = None
            self.url_entry.delete(0, tk.END)
        else:
            self.status_display.delete(1.0, tk.END)

    def clear_resolution_buttons(self):
        """Clear the existing resolution buttons."""
        for btn in self.resolution_buttons:
            btn.destroy()
        self.resolution_buttons.clear()
    
    def start_download(self):
        """Clear the status display and start download."""
        if self.selected_media_type == "Image":
            self.update_content_status()
            self.url_entry_link = self.url_entry.get()
            self.selected_img_format = self.settings.get('image_format_var')
            self.download_path = self.settings.get("download_path")
            # Assign default path if no image path is provided
            if not self.download_path:
                # Define a default path if no image path is specified
                self.download_path = os.path.join(os.getcwd(), "downloaded_images")
                # print("No path provided. Using default path:", self.download_path)
            else:
                # Check if the path exists; create if it does not
                if not os.path.exists(self.download_path):
                    os.makedirs(self.download_path, exist_ok=True)

            image_urls = []  # Initialize the list to collect image URLs

            if self.selected_file_path and self.content:
                # Split content into URLs and add to the image_urls list
                image_urls = [i.strip().replace("\t", "") for i in self.content.split("\n") if
                            i.strip().replace("\t", "").startswith("https:") or i.strip().replace("\t", "").startswith(
                                "http:")]
            elif self.url_entry_link:
                if self.url_entry_link.strip().replace("\t", "").startswith("https:"):
                    image_urls.append(self.url_entry_link.strip().replace("\t", ""))
            elif self.content:
                image_urls = [i.strip().replace("\t", "") for i in self.content.split("\n") if
                            i.strip().replace("\t", "").startswith("https:") or i.strip().replace("\t", "").startswith(
                                "http:")]
            if image_urls:
                # print(image_urls)
                """Simulate a download process for testing."""
                # Reset progress and status
                self.progress_bar.set(0)
                self.status_display.delete(1.0, tk.END)  # Clear the status display
                self.status_display.insert(tk.END, "Starting download...\n")
                self.download_cancelled = False
                self.downloading_content = True
                total_links = len(image_urls)
                # Start the asynchronous download in a new thread to avoid freezing the UI
                threading.Thread(target=self._download_images_thread,
                                args=(image_urls, total_links, self.selected_img_format, self.download_path,
                                    self.settings.get('max_workers'))).start()

                # Resetting necessary variables after download
                self.selected_file_path = None
                self.content = None
                self.url_entry_link = None
                self.url_entry.delete(0, tk.END)
        elif self.selected_media_type =="Video" or self.selected_media_type =="Audio":
            self.clear_resolution_buttons()
            self.update_content_status()
            self.url_entry_link = self.url_entry.get()
            self.selected_img_format = self.settings.get('image_format_var')
            self.download_path = self.settings.get("download_path")
            # Assign default path if no image path is provided
            if not self.download_path:
                # Define a default path if no image path is specified
                self.download_path = os.path.join(os.getcwd(), "downloaded_images")
                # print("No path provided. Using default path:", self.download_path)
            else:
                # Check if the path exists; create if it does not
                if not os.path.exists(self.download_path):
                    os.makedirs(self.download_path, exist_ok=True)

            image_urls = []  # Initialize the list to collect image URLs

            if self.selected_file_path and self.content:
                # Split content into URLs and add to the image_urls list
                image_urls = [i.strip().replace("\t", "") for i in self.content.split("\n") if
                            i.strip().replace("\t", "").startswith("https:") or i.strip().replace("\t", "").startswith(
                                "http:")]
            elif self.url_entry_link:
                if self.url_entry_link.strip().replace("\t", "").startswith("https:"):
                    image_urls.append(self.url_entry_link.strip().replace("\t", ""))
            elif self.content:
                image_urls = [i.strip().replace("\t", "") for i in self.content.split("\n") if
                            i.strip().replace("\t", "").startswith("https:") or i.strip().replace("\t", "").startswith(
                                "http:")]
            if image_urls:
                # Reset progress and status
                self.progress_bar.set(0)
                # self.status_display.delete(1.0, tk.END)  # Clear the status display
                self.status_display.insert(1.0, "Starting download...\n")
                self.download_cancelled = False
                self.downloading_content = True
                
                global total_media_links
                total_media_links = len(image_urls)
                
                self.clear_resolution_buttons()
                
                # Start the asynchronous download in a new thread to avoid freezing the UI
                thread = threading.Thread(target=self.fetch_resolutions_sequential, args=(image_urls,))
                thread.start()
                
                # Resetting necessary variables after download
                self.content = None
                self.url_entry_link = None
                self.url_entry.delete(0, tk.END)


    def fetch_resolutions_sequential(self, links):
        """Fetch video resolutions sequentially or create audio buttons."""
        if self.selected_media_type == "Audio":
            # Audio download mode  
            links = links
            while True:
                if links and not self.resolution_buttons and not self.download_cancelled:
                    link = links[0]
                    self.create_audio_button(link)
                    links.pop(0)
                if not links or self.download_cancelled:
                    break
                else:
                    time.sleep(5)
                    
        elif self.selected_media_type=="Video":
            # Video download mode with resolutions (fetch sequentially)
            links = links
            while True:
                if links and not self.resolution_buttons and not self.download_cancelled:
                    link = links[0]
                    resolutions = self.downloader.get_video_formats(link)
                    self.create_resolution_button(link=link, resolutions=resolutions)
                    # self.create_audio_button(link)
                    links.pop(0)
                        
                if not links or self.download_cancelled:
                    break
                else:
                    time.sleep(5)
     


    def create_audio_button(self, link):
        """Create a button for downloading audio."""
        button = CTkButton(
            self.resolution_frame, 
            text=f"Download Audio from {link}",
            command=lambda l=link: self.start_audio_download(l), width=200
        )
        self.resolution_buttons.append(button)
        self.adjust_buttons()
        
        self.after(10000, self._auto_click_button_internal)
    
    def process_video_formats(self, video_formats):
        """
        Organize video formats by first gathering all unique resolutions with sizes,
        and then appending other resolutions without sizes or duplicates.

        :param video_formats: List of tuples (resolution, size_text, format_id)
        :return: Ordered list of video formats
        """
        # Helper function to extract size in MB from size_text
        def size_to_mb(size_text):
            try:
                return float(size_text.replace(" MB", ""))
            except ValueError:
                return None

        # Step 1: Gather unique formats with sizes
        unique_formats = []  # Final list of video formats
        unique_resolutions = set()  # To track resolutions already added

        # First pass: Add all unique resolutions with available sizes
        for res, size_text, fmt_id in video_formats:
            size_mb = size_to_mb(size_text)
            if size_mb != "Unknown Size" and res not in unique_resolutions:
                unique_formats.append((res, size_text, fmt_id))
                unique_resolutions.add(res)

        # Step 2: Append remaining formats without duplicates
        for res, size_text, fmt_id in video_formats:
            if res not in unique_resolutions:
                unique_formats.append((res, size_text, fmt_id))
                unique_resolutions.add(res)

        return unique_formats
    
    
    
    def create_resolution_button(self, link, resolutions):
        """Create a button for downloading a specific video resolution."""
        # print(resolutions)
        # unique_resolutions=self.process_video_formats(resolutions)
        # print(unique_resolutions)
        for resolution, size, format_id in resolutions:
            btn_text = f"{resolution.lower()} - {size}"
            print(f"Button Text: {btn_text}, Format ID: {format_id}")
            # Create button
            button = CTkButton(
                self.resolution_frame,
                text=btn_text,
                command=lambda l=link, f_id=format_id: self.start_video_download(l, f_id)
            )
            self.resolution_buttons.append(button)
        
        self.adjust_buttons()

                
        """Auto-click the button if its text starts with the specified string."""
        self.after(10000, self._auto_click_button_internal)


 
    def start_video_download(self, link, format_id):
        """Start downloading the video in a separate thread."""
        # Clear resolution buttons once download starts
        url = link
        filename_save_as = self.settings.get('filename_save_as')
        if filename_save_as == 'Url':
            title = sanitize_filename(url)
        elif filename_save_as == "Hash 256":
            title = hashlib.sha256(url.encode('utf-8')).hexdigest()
        elif filename_save_as == 'Numeric':
            title = generate_numeric_filename()
            
        print(f"Downloading video from: {link} with format ID: {format_id}")
        thread = threading.Thread(target=self.downloader.download_video, args=(link, format_id, self.update_status, title, self.download_path))
        thread.start()
        self.clear_resolution_buttons()
        self.downloaded_media_count+=1
        progress = self.downloaded_media_count / total_media_links
        self._safe_update_progress(progress)
        

    def start_audio_download(self, link):
        """Start downloading audio in a separate thread."""
        url = link
        filename_save_as = self.settings.get('filename_save_as')
        if filename_save_as == 'Url':
            title = sanitize_filename(url)
        elif filename_save_as == "Hash 256":
            title = hashlib.sha256(url.encode('utf-8')).hexdigest()
        elif filename_save_as == 'Numeric':
            title = generate_numeric_filename()
            
        thread = threading.Thread(target=self.downloader.download_audio, args=(link, self.update_status, title, self.download_path))
        thread.start()
        self.clear_resolution_buttons()
        self.downloaded_media_count+=1
        progress = self.downloaded_media_count / total_media_links
        self._safe_update_progress(progress)
   
    def update_status(self, message):
        """Update the status bar with the given message."""
        self.status_label.configure(text=message)
         
    def _auto_click_button_internal(self):
        """Internal method to perform the auto-click in the main thread."""
        if self.selected_auto_download_res != "Manual" and self.resolution_buttons and not self.download_cancelled:
            for button in self.resolution_buttons:
                if button.cget("text").startswith(self.selected_auto_download_res):
                    button.invoke()  # Simulate the button click
                    break  # Stop after the first match
                
        elif self.selected_auto_download_res != "Manual" and len(self.resolution_buttons)==1 and not self.download_cancelled:
            button = self.resolution_buttons[0]
            button.invoke()
            


    def cancel_download(self):
        """Cancels the download process."""
        if self.status_display.get(1.0, 2.0) == "Starting download...\n" and not self.download_cancelled:   
            self.download_cancelled = True
            self.downloading_content = False
            self.update_status_display("Cancelling downloads...")
            self.clear_resolution_buttons()
            self.status_label.configure(text="Status")
            # Wait for 5 seconds before starting the reversal
            self.progress_bar.after(5000, self.reverse_progress)
            
    def format_time_f(self, seconds):
        """Convert seconds to a human-readable format."""
        if seconds < 60:
            return f"{seconds:.2f} seconds"
        elif seconds < 3600:
            minutes, seconds = divmod(seconds, 60)
            return f"{int(minutes)} minutes and {seconds:.2f} seconds"
        else:
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{int(hours)} hours, {int(minutes)} minutes and {seconds:.2f} seconds"

    def _download_images_thread(self, urls, total, selected_img_format, image_path, max_workers=5):
        """The actual download process running in a separate thread."""
        self.download_cancelled = False  # Reset the flag when starting a new download
        filename_save_as = self.settings.get('filename_save_as')

        if not urls:
            # print("No valid URLs provided.")
            self.update_status_display("No valid URLs to download.")
            return

        # Update the status display with URLs and max workers
        self.update_status_display(f"URLs to process: {len(urls)}, Max workers: {max_workers}")

        existing_files = {filename for filename in os.listdir(image_path)}
        start_time = time.time()  # Start the timer

        def download_image(url):
            if self.download_cancelled:  # Check if the download was cancelled
                return "Cancelled"

            # print("Attempting to download:", url)
            try:
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                img_data = response.content
                if filename_save_as == 'Url' or filename_save_as=="Default":
                    img_hash = sanitize_filename(url)
                elif filename_save_as == "Hash 256":
                    img_hash = hashlib.sha256(url.encode('utf-8')).hexdigest()
                elif filename_save_as == 'Numeric':
                    img_hash = generate_numeric_filename()
                    
                original_format = url.split('.')[-1].lower() if url.split('.')[-1].lower() in ['jpg', 'jpeg', 'png',
                                                                                               'gif', 'bmp',
                                                                                               'webp'] else "jpg"
                chosen_format = original_format if selected_img_format == "default" else selected_img_format
                filename = f"{img_hash}.{chosen_format.lower()}"

                if filename in existing_files:
                    return f"Skipped (already downloaded): {url}"

                filepath = os.path.join(image_path, filename)
                with open(filepath, 'wb') as file:
                    file.write(img_data)

                existing_files.add(filename)
                progress = len(existing_files) / total
                self._safe_update_progress(progress)
                return f"Downloaded: {url}"

            except requests.exceptions.RequestException as e:
                return f"Error downloading {url}: {e}"

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(download_image, url): url for url in urls}

            for future in concurrent.futures.as_completed(future_to_url):
                if self.download_cancelled:
                    self.update_status_display("Download cancelled by user.")
                    break
                result = future.result()
                # print(result)
                self.update_status_display(result)

        if not self.download_cancelled:
            self.update_status_display("All downloads completed.")
            # Calculate time taken
            self.download_cancelled = True
            self.downloading_content = False
            elapsed_time = time.time() - start_time
            self.update_status_display(f"Downloaded {total} images in {self.format_time_f(elapsed_time)}.")
            self._safe_update_progress("Completed")

        
    def reverse_progress(self):
        current_value = self.progress_bar.get()  # Get the current progress value
        if current_value > 0:
            new_value = current_value - 1  # Decrease the progress value
            self.progress_bar.set(new_value)  # Update the progress bar
            self.progress_bar.after(50, self.reverse_progress)  # Repeat after 50ms
        else:
            self.progress_bar.set(0)  # Ensure the progress bar is fully reset

    def _safe_update_progress(self, progress):
        if progress != "Completed":
            """Safely update the progress bar from a thread."""
            self.progress_bar.after(0, lambda: self.progress_bar.set(progress))
        elif progress == "Completed":
            # Wait for 5 seconds before starting the reversal
            self.progress_bar.after(5000, self.reverse_progress) # Start reversing the progress bar

    def update_status_display(self, message):
        """Update the status display area."""
        self.status_display.insert(tk.END, message + "\n")
        self.status_display.see(tk.END)  # Scroll to the end

    def update_real_time(self):
        """Update the real-time display and calculate elapsed time."""
        # Current time
        current_time = datetime.now()
        # Elapsed time
        elapsed_time = current_time - datetime.strptime(self.app_opened_time, "%Y-%m-%d %H:%M:%S")

        # Update the label with real-time, elapsed time
        self.time_label.configure(
            text=f"Opened: {self.app_opened_time}       Time: {current_time.strftime('%H:%M:%S')}       Elapsed: {str(elapsed_time).split('.')[0]}"
        )
        # Call this function again after 1 second
        self.time_label.after(1000, self.update_real_time)


    def on_status_display_modified(self, event):
        """Mark status display as changed and reset the modified flag."""
        self.status_display_changed = True
        self.status_display.edit_modified(False)  # Reset the modified flag

    def select_file(self):
        """Allow user to select a file with image URLs and load its content."""
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*")])
        if file_path.split(".")[-1] == "txt":
            self.selected_file_path = file_path
            with open(file_path, 'r') as file:
                self.content = file.read()
                self.status_display.delete(1.0, tk.END)
                self.status_display.insert(tk.END, self.content)
                self.content = self.status_display.get(1.0, tk.END)
            self.status_display_changed = False  # Reset change flag after loading
        elif file_path:
            self.selected_file_path = file_path
            self.content = self.load_encrypted_data(self.selected_file_path)
            if self.content:
                self.status_display.delete(1.0, tk.END)
                self.status_display.insert(tk.END, self.content)
                self.content = self.status_display.get(1.0, tk.END)
                # print(self.content)
                self.status_display_changed = False  # Reset change flag after loading
        else:
            pass

    def load_encrypted_data(self, data_filename):
        if data_filename.endswith('.data'):
            data_path = data_filename
            key_path = data_filename.rsplit('.', 1)[0] + ".key"
        elif data_filename.endswith('.key'):
            key_path = data_filename
            data_path = data_filename.rsplit('.', 1)[0] + ".data"
        else:
            message = "Invalid file type."
            self.update_status_display(message)
            return None

        # Check if the corresponding key and data files exist
        if not os.path.exists(data_path) or not os.path.exists(key_path):
            message = f"Key or data file does not exist: {key_path}, {data_path}"
            self.update_status_display(message)  # Display in status display area
            return None

        # Load the encryption key
        with open(key_path, "rb") as key_file:
            key = key_file.read()

        cipher_suite = Fernet(key)

        # Load and decrypt the data
        with open(data_path, "rb") as data_file:
            encrypted_data = data_file.read()

        try:
            serialized_data = cipher_suite.decrypt(encrypted_data)
        except Exception as e:
            message = f"Failed to decrypt data: {e}"
            self.update_status_display(message)
            return None

        # Deserialize the data
        data = pickle.loads(serialized_data)
        # print("Decrypted data:", data)
        # Format data as a string with each element on a new line
        formatted_data = "\n".join(data)

        return formatted_data

    def update_content_status(self):
        self.content = self.status_display.get(1.0, tk.END)

    def save_encrypted_data(self, base_filename="image_links", folder="database"):
        """Save extracted links to an encrypted file along with its key."""

        self.update_content_status()
        data = []  # Initialize data

        if self.content:
            # Extract links that start with "https:"
            data = [i.strip().replace("\t", "") for i in self.content.split("\n") if
                    i.strip().replace("\t", "").startswith("https:") or i.strip().replace("\t", "").startswith("http:")]

        if data:
            
            # Create the folder if it doesn't exist
            if not os.path.exists(folder):
                os.makedirs(folder)

            # Generate a new key for each file
            key = Fernet.generate_key()
            cipher_suite = Fernet(key)

            # Serialize and encrypt the data
            serialized_data = pickle.dumps(data)
            encrypted_data = cipher_suite.encrypt(serialized_data)

            # Find the next available filename in the specified folder
            counter = 1
            while True:
                data_filename = os.path.join(folder, f"{base_filename}_{counter}.data")
                key_filename = os.path.join(folder, f"{base_filename}_{counter}.key")
                if not os.path.exists(data_filename) and not os.path.exists(key_filename):
                    break
                counter += 1

            try:
                # Save the encrypted data
                with open(data_filename, "wb") as data_file:
                    data_file.write(encrypted_data)

                # Save the encryption key
                with open(key_filename, "wb") as key_file:
                    key_file.write(key)

                message = f"Encrypted data saved to {data_filename} with key in {key_filename}"
                self.update_status_display(message)

            except Exception as e:
                message = f"An error occurred while saving files: {e}"
                self.update_status_display(message)
        else:
            message = "No valid links to save."
            self.update_status_display(message)

    def save_encrypted_data_to_selected_file(self, given_data, file_name):
        """Serialize and encrypt the data before saving it to an encrypted .data file."""
        data = []  # Initialize data
        if self.content:
            # Extract links that start with "https:"
            data = [i for i in given_data.split("\n") if i.startswith("https:") or i.startswith("http:")]

        if data:
            key_filename = file_name.rsplit('.', 1)[0] + ".key"
            file_name = file_name.rsplit('.', 1)[0] + ".data"
            # Check if the key file exists
            if os.path.exists(key_filename):
                # Load the existing key
                with open(key_filename, "rb") as key_file:
                    key = key_file.read()
                cipher_suite = Fernet(key)
            else:
                # Generate a new key if the key file does not exist
                key = Fernet.generate_key()
                cipher_suite = Fernet(key)

            # Serialize and encrypt the data
            serialized_data = pickle.dumps(data)
            encrypted_data = cipher_suite.encrypt(serialized_data)
            # Save the encrypted data
            with open(file_name, "wb") as data_file:
                data_file.write(encrypted_data)
            message = f"\n\nSuccessfully updated {file_name}"
            self.update_status_display(message)

            # If a new key was generated, save it
            if not os.path.exists(key_filename):
                with open(key_filename, "wb") as key_file:
                    key_file.write(key)


    def update_button_command(self):
        """Check for unsaved changes before starting the download process."""
        if self.status_display_changed and self.selected_file_path:
            should_save = messagebox.askyesno(
                "Save Changes",
                "Do you want to save changes to the selected file?"
            )
            if should_save:  # Save changes
                if self.selected_file_path.endswith('.data') or self.selected_file_path.endswith('.key'):
                    # Handling saving to an encrypted .data file
                    self.save_encrypted_data_to_selected_file(file_name=self.selected_file_path,
                                                              given_data=self.status_display.get(1.0, tk.END))
                else:
                    # Handling saving to a plain text file
                    with open(self.selected_file_path, 'w') as file:
                        file.write(self.status_display.get(1.0, tk.END))
                        
                    message = f"\n\nSuccessfully updated {self.selected_file_path}"
                    self.update_status_display(message)
                self.status_display_changed = False
            
        

    def show_settings(self):
        self.update_content_status()
        # Hide other windows if they're displayed
        if self.home_window and self.show_home_window_number >= 1:
            self.home_window.pack_forget()
            self.show_home_window_number -= 1
        if self.about_window and self.show_about_window_number >= 1:
            self.about_window.pack_forget()
            self.show_about_window_number -= 1

        # Create settings window if not already displayed
        if self.show_settings_window_number == 0:
            self.settings_window = CTkFrame(self, fg_color="gray20", bg_color="gray20")
            self.settings_window.pack(side="left", fill="both", expand=True)
            self.show_settings_window_number += 1

            # Button Frame
            button_frame = CTkFrame(self.settings_window, fg_color="gray20")
            button_frame.pack(side="top", anchor="e", padx=10, pady=10)  # Align to the right side (east)

            # Reset to Default Button
            reset_button = CTkButton(button_frame, text="Reset to Default", command=self.reset_settings,
                                     fg_color="#E67E22", hover_color="#D35400")
            reset_button.pack(side="left", padx=5)

            # Save Changes Button
            save_button = CTkButton(button_frame, text="Save Changes", command=self.save_settings_to_file,
                                    fg_color="#2ECC71", hover_color="#27AE60")
            save_button.pack(side="left", padx=5)

            # Title
            CTkLabel(self.settings_window, text="Settings", font=("Arial", 18, "bold"), text_color="cyan").pack(pady=10)

            # Text Size
            text_frame = CTkFrame(self.settings_window, fg_color="gray20", corner_radius=8)
            text_frame.pack(fill="x", padx=10, pady=10)
            CTkLabel(text_frame, text="Text Size", font=("Arial", 14), text_color="#ffffff").pack(side="left", padx=10)
            self.text_size_var = tk.IntVar(value=self.settings.get('text_size', 13))
            self.text_size_label = CTkLabel(text_frame, text=str(self.text_size_var.get()), font=("Arial", 12), text_color="#ffffff")
            self.text_size_label.pack(side="right", padx=10)

            text_size_slider = CTkSlider(text_frame, from_=8, to=30, number_of_steps=22, variable=self.text_size_var,
                                         command=self.update_text_size_label)
            text_size_slider.pack(fill="x", padx=10, pady=(6, 0))

            # Download Path
            path_frame = CTkFrame(self.settings_window, fg_color="gray20", corner_radius=8)
            path_frame.pack(fill="x", padx=10, pady=10)
            CTkLabel(path_frame, text="Download Path", font=("Arial", 14), text_color="#ffffff").pack(side="left", padx=10)
            self.download_path_var = tk.StringVar(value=self.settings.get('download_path', ''))
            download_path_entry = CTkEntry(path_frame, textvariable=self.download_path_var, width=240,
                                           placeholder_text="Select download folder")
            download_path_entry.pack(side="left", padx=10, fill="x", expand=True)
            download_path_button = CTkButton(path_frame, text="Select", command=self.select_download_path)
            download_path_button.pack(side="right", padx=10)
            
            # filename
            filename_frame = CTkFrame(self.settings_window, fg_color="gray20", corner_radius=8)
            filename_frame.pack(fill="x", padx=10, pady=10)
            CTkLabel(filename_frame, text="Download Filename as", font=("Arial", 14), text_color="#ffffff").pack(side="left", padx=10)
            
            self.filename_save_as = tk.StringVar(value=self.settings.get('filename_save_as'))
            self.filename_selector = CTkOptionMenu(filename_frame,
                                               values=['Default', 'Url', 'Hash 256', 'Numeric'],
                                               variable=self.filename_save_as, width=100)
            self.filename_selector.pack(side="left", padx=10, fill="x", expand=True)
            
            # Image format selection
            CTkLabel(filename_frame, text='IMG Format', font=("Arial", 14), text_color="#ffffff").pack(side="left", padx=10)
            self.image_format_var = tk.StringVar(value=self.settings.get('image_format_var'))
            self.format_option = CTkOptionMenu(filename_frame,
                                               values=['default', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'],
                                               variable=self.image_format_var)
            self.format_option.pack(side="left", padx=(5, 10), fill="x", expand=True)
            
            
            # Max Workers
            max_frame = CTkFrame(self.settings_window, fg_color="gray20", corner_radius=8)
            max_frame.pack(fill="x", padx=10, pady=10)
            CTkLabel(max_frame, text="Max Workers", font=("Arial", 14), text_color="#ffffff").pack(side="left", padx=10)
            self.max_workers_var = tk.StringVar(value=self.settings.get('max_workers', 5))
            max_workers_entry = CTkEntry(max_frame, textvariable=self.max_workers_var, width=60)
            max_workers_entry.pack(side="left", padx=10, fill="x", expand=True)

    def reset_settings(self):
        """Reset settings to default values after user confirmation."""
        # Ask for user confirmation
        if not messagebox.askokcancel("Confirm Reset", "Are you sure you want to reset all settings to default?"):
            return  # Exit if the user cancels
        
        # Default settings
        default_settings = {
            'text_size': 14,
            'download_path': 'downloaded_images',
            'filename_save_as': 'Default',
            "image_format_var": 'jpg',
            'bg_color': 'dark',
            'max_workers': 5,
        }
        self.settings = default_settings.copy()  # Reset to default

        # Update UI variables
        self.text_size_var.set(self.settings['text_size'])
        self.download_path_var.set(self.settings['download_path'])
        self.filename_save_as.set(self.settings['filename_save_as'])
        self.image_format_var.set(self.settings['image_format_var'])
        self.max_workers_var.set(self.settings['max_workers'])

        # Save the default settings to the file
        self.save_settings_to_file()

        # Inform the user that the settings have been reset
        messagebox.showinfo("Settings Reset", "Settings have been reset to default values.")

    def load_settings(self):
        # Load settings from settings.ini if it exists
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "rb") as f:
                return pickle.load(f)
        self.default_settings = {'text_size': 14, 'download_path': 'downloaded_images', 'bg_color': 'dark', 'filename_save_as':'Default', 'image_format_var':'jpg',
                                 'max_workers': 5}
        
        return self.default_settings

    def select_download_path(self):
        # Open a folder selection dialog
        path = filedialog.askdirectory()
        if path:
            self.download_path_var.set(path)
            self.save_setting('download_path', path)

    def save_setting(self, key, value):
        # Update setting in the dictionary
        self.settings[key] = value
        # print(f"Updated {key}: {value}")  # Debugging message

    def save_settings_to_file(self):
        try:
            self.settings['text_size'] = self.text_size_var.get()
            self.settings['download_path'] = self.download_path_var.get()
            self.settings['filename_save_as'] = self.filename_save_as.get()
            self.settings['image_format_var'] = self.image_format_var.get()
            self.settings['max_workers'] = int(
                self.max_workers_var.get() if self.max_workers_var.get().isdigit() else 5)
            with open("settings.ini", "wb") as file:
                # noinspection PyTypeChecker
                pickle.dump(self.settings, file)
            messagebox.showinfo("Settings Saved", "Settings have been successfully saved.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while saving settings: {e}")

    def update_text_size_label(self, value):
        # Update the text size label and save the new size
        self.text_size_label.configure(text=str(int(float(value))))
        self.save_setting('text_size', int(float(value)))

    def open_email(self, event):
        email = "devjamshidbek@gmail.com"
        # Open Gmail with the email address pre-filled
        webbrowser.open(f"mailto:{email}")
        # Optionally, copy email to clipboard
        pyperclip.copy(email)
        # print(f"Copied to clipboard: {email}")

    def show_about(self):
        self.update_content_status()
        # Hide home window if it's already displayed
        if self.home_window and self.show_home_window_number >= 1:
            self.home_window.pack_forget()
            self.show_home_window_number -= 1
        if self.settings_window and self.show_settings_window_number >= 1:
            self.settings_window.pack_forget()
            self.show_settings_window_number -= 1

        if self.show_about_window_number == 0:
            self.about_window = CTkFrame(self, fg_color="gray20", bg_color="gray20",)
            self.about_window.pack(side='left', fill="both", expand=True)
            self.show_about_window_number += 1

            # Main About Info
            CTkLabel(
                self.about_window,
                text="Image Downloader App",
                text_color="#3498db",
                font=("Arial", 20, "bold"),
                anchor="center"
            ).pack(pady=(20, 5))

            # Create the About label with clickable email
            about_label = CTkLabel(
                self.about_window,
                text="Created by: Jamshidbek Foziljonov\nDate: 11/4/2024\nEmail: devjamshidbek@gmail.com",
                text_color="white",
                font=("Arial", 14),
                anchor="center"
            )
            about_label.pack(pady=(0, 15))

            # Make the email clickable
            about_label.bind("<Button-1>", self.open_email)

            # App Purpose
            CTkLabel(
                self.about_window,
                text="Purpose: Easily download and manage images from multiple sources.",
                text_color="lightgray",
                font=("Arial", 12),
                anchor="center",
                wraplength=400
            ).pack(pady=(5, 15))

            # Key Features List
            features_text = (
                "• Multi-format support (JPG, PNG, BMP, GIF, etc.)\n"
                "• Custom download paths\n"
                "• Real-time progress and status updates\n"
                "• User-friendly interface with modern design\n"
                "• High-performance, with multi-threaded downloads"
            )
            CTkLabel(
                self.about_window,
                text="Key Features:",
                text_color="#2ECC71",
                font=("Arial", 14, "bold"),
                anchor="w"
            ).pack(pady=(5, 5), padx=15, anchor="w")

            CTkLabel(
                self.about_window,
                text=features_text,
                text_color="white",
                font=("Arial", 12),
                anchor="w",
                justify="left",
                wraplength=450
            ).pack(pady=(0, 15), padx=15, anchor="w")

            # Version Information
            CTkLabel(
                self.about_window,
                text="Version: 1.0.0",
                text_color="lightgray",
                font=("Arial", 12, "italic"),
                anchor="center"
            ).pack(pady=(0, 20))

    def quit_app(self):
        """Quit the application safely."""
        self.destroy()


if __name__ == "__main__":
    app = ImageDownloaderApp()
    app.mainloop()
