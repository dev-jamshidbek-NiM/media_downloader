import customtkinter as ctk
import hashlib
import os
import time
import requests
import threading
from datetime import datetime
from tkinter import filedialog, ttk

CONCURRENT_DOWNLOADS = 10  # Adjust based on network and server limits


def get_file_hash(content):
    """Generate a hash for the binary content of the file using SHA-256."""
    return hashlib.sha256(content).hexdigest()


def download_image(url, progress_bar, label_progress, error_links, cancel_flag):
    try:
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            content = response.content
            content_hash = get_file_hash(content)

            """Check if the URL is an image URL based on the file extension."""
            valid_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
            image_format = url.split('.')[-1].lower()
            if image_format in valid_extensions:
                original_format = image_format
            else:
                original_format = 'jpg'
            filename = f"downloaded_images/{content_hash}.{original_format}"

            if not os.path.exists(filename):
                with open(filename, 'wb') as f:
                    f.write(content)

                if url not in downloaded_links:
                    with open("downloaded_links.txt", "a") as file:
                        file.write(url + "\n")

            progress_bar.step(1)
            label_progress.configure(text=f"Downloaded: {filename}")

            if cancel_flag[0]:  # Exit if cancel is requested
                return

    except Exception as e:
        error_links.append(url)


def start_download(image_urls, progress_bar, label_progress, cancel_flag):
    """Start threaded download of images."""
    # Load previously downloaded URLs
    global downloaded_links
    downloaded_links = set()
    if os.path.exists("downloaded_links.txt"):
        with open("downloaded_links.txt", "r") as file:
            downloaded_links = set(file.read().splitlines())

    error_links = []  # Track any error links
    threads = []  # Store the threads for download tasks

    # Prepare directory for downloaded images
    os.makedirs("downloaded_images", exist_ok=True)

    for url in image_urls:
        if url in downloaded_links:
            continue  # Skip already downloaded
        if cancel_flag[0]:  # Check if cancel was requested
            break

        thread = threading.Thread(target=download_image,
                                  args=(url, progress_bar, label_progress, error_links, cancel_flag))
        thread.start()
        threads.append(thread)

        # Limit concurrent downloads while allowing the UI to remain responsive
        while len(threads) >= CONCURRENT_DOWNLOADS:
            # Wait briefly for threads to finish without freezing the UI
            for t in threads:
                if not t.is_alive():
                    threads.remove(t)
                    break  # Exit the for loop and re-evaluate the thread list

            # Optional: If cancel is requested, we can exit the loop.
            if cancel_flag[0]:
                break

        # Optionally sleep for a short duration to allow UI updates (if necessary)
        time.sleep(0.1)

    # Wait for any remaining threads to complete after breaking out of the loop
    for t in threads:
        t.join(timeout=0.1)  # Ensure we are not blocking the UI

    # Log errors if there are any
    if error_links:
        with open("errors.txt", "a") as file:
            file.write("\n".join(error_links) + "\n")


class ImageDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.threads = []  # Track threads

        # App configuration
        self.title("Image Downloader")
        self.geometry("600x400")

        # App opened time
        self.app_opened_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Cancel flag
        self.cancel_download = [False]

        # Widgets setup
        self.label_time = ctk.CTkLabel(self, text=f"App Opened Time: {self.app_opened_time}")
        self.label_time.pack(pady=5)

        self.label_real_time = ctk.CTkLabel(self, text="")
        self.label_real_time.pack(pady=5)

        self.progress_label = ctk.CTkLabel(self, text="Progress:")
        self.progress_label.pack(pady=10)

        self.progress_bar = ttk.Progressbar(self, length=300, mode='determinate')
        self.progress_bar.pack(pady=10)

        self.button_download = ctk.CTkButton(self, text="Select File to Download", command=self.select_file)
        self.button_download.pack(pady=10)

        self.button_cancel = ctk.CTkButton(self, text="Cancel", command=self.cancel_download_task)

        self.update_time()  # Start real-time clock

    def select_file(self):
        """Open a file dialog to select a file containing image URLs."""
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            self.start_download(file_path)
            self.button_download.pack_forget()  # Hide download button
            self.button_cancel.pack(pady=5)  # Show cancel button

    def cancel_download_task(self):
        """Cancel the download process."""
        self.cancel_download[0] = True
        self.button_cancel.pack_forget()  # Hide cancel button
        self.button_download.pack(pady=10)  # Show download button
        self.progress_label.configure(text="Download canceled.")
        self.progress_bar["value"] = 0

    def start_download(self, file_path):
        """Start the download process in a new thread to avoid freezing."""
        with open(file_path, "r") as f:
            image_urls = f.read().splitlines()

        self.progress_bar["maximum"] = len(image_urls)
        self.progress_bar["value"] = 0
        self.cancel_download[0] = False  # Reset cancel flag

        # Start downloading in a background thread
        threading.Thread(target=start_download,
                         args=(image_urls, self.progress_bar, self.progress_label, self.cancel_download),
                         daemon=True).start()

    def update_time(self):
        """Update the real-time clock."""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.label_real_time.configure(text=f"Current Time: {current_time}")
        self.label_real_time.after(1000, self.update_time)  # Update every second


if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    app = ImageDownloaderApp()
    app.mainloop()
