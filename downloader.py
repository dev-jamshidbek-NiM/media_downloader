import requests, time
import threading
import yt_dlp as ydl
import os
import requests

class MediaDownloader:
    def __init__(self):
        self.video_formats = {}

    def get_video_formats(self, link):
        """
        Fetch all available resolutions, sizes, and format IDs for the given video link using yt-dlp.
        Estimate sizes for resolutions missing size information.
        :param link: Video URL
        :return: List of tuples (resolution, size, format_id)
        """
        try:
            import requests

            ydl_opts = {
                'quiet': True,
                'cookiefile': 'path_to_your_cookies.txt',  # Provide the path to your cookies.txt file
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',  # Custom User-Agent
            }

            with ydl.YoutubeDL(ydl_opts) as ydl_instance:
                info_dict = ydl_instance.extract_info(link, download=False)
                if 'formats' not in info_dict:
                    raise ValueError("No available formats for this video.")
                
                formats = info_dict['formats']
                video_formats = []
                base_resolution_size = None  # Known resolution and size for estimation

                # Helper function to fetch video size if not provided
                def get_video_size(url):
                    try:
                        response = requests.head(url, allow_redirects=True)
                        if 'Content-Length' in response.headers:
                            return int(response.headers['Content-Length'])
                        return None
                    except Exception as e:
                        print(f"Error fetching file size: {e}")
                        return None

                # Pass 1: Collect sizes for resolutions with known sizes
                resolution_data = {}
                for fmt in formats:
                    if fmt.get('vcodec') == "none":  # Exclude audio-only formats
                        continue

                    resolution = f"{fmt.get('height', 'Unknown')}p"
                    height = fmt.get('height')

                    # Check for filesize
                    filesize = fmt.get('filesize') or fmt.get('filesize_approx')
                    if not filesize:
                        video_url = fmt.get('url')
                        filesize = get_video_size(video_url)

                    if filesize:
                        size_mb = filesize / (1024 * 1024)
                        resolution_data[height] = size_mb  # Store size by height for estimation
                        if not base_resolution_size and height:
                            base_resolution_size = (height, size_mb)

                # Pass 2: Estimate sizes for missing resolutions
                for fmt in formats:
                    if fmt.get('vcodec') == "none":
                        continue

                    resolution = f"{fmt.get('height', 'Unknown')}p"
                    height = fmt.get('height')

                    if height not in resolution_data and base_resolution_size and height:
                        # Estimate size based on known resolution size
                        base_height, base_size = base_resolution_size
                        estimated_size = base_size * (height ** 2) / (base_height ** 2)
                        resolution_data[height] = estimated_size

                # Build the video formats list
                for fmt in formats:
                    if fmt.get('vcodec') == "none":
                        continue

                    resolution = f"{fmt.get('height', 'Unknown')}p"
                    height = fmt.get('height')

                    size_mb = resolution_data.get(height)
                    size_text = f"{size_mb:.1f} MB" if size_mb else "Unknown Size"

                    # Append only resolution, size, and format_id
                    video_formats.append((resolution, size_text, fmt.get('format_id')))

                return video_formats

        except Exception as e:
            raise ValueError(f"Failed to retrieve video info: {e}")


    def download_video(self, link, format_id, status_callback, video_title=None, downloaded_folder=None):
        """
        Download the video at the specified resolution using yt-dlp.
        
        :param link: Video URL
        :param format_id: Selected format ID for the video
        :param status_callback: Function to update status messages
        :param video_title: Custom title for the video (optional)
        :param downloaded_folder: Folder to save the video (optional)
        """
        self.start_time = time.time()

        # Determine the output folder
        output_folder = downloaded_folder if downloaded_folder else "downloaded_videos"
        os.makedirs(output_folder, exist_ok=True)

        # Determine the video output name
        output_name = f"{video_title}.%(ext)s" if video_title else "%(title)s.%(ext)s"
        
        print("Available formats:")
        
        print(f"Format ID: {format_id}, Resolution: {link},")


        try:
            ydl_opts = {
                'format': f"{format_id}+bestaudio",  # Combine selected video format with best available audio
                'outtmpl': os.path.join(output_folder, output_name),  # Save in the specified folder with the determined name
                'progress_hooks': [lambda d: self._progress_hook(d, status_callback)],
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',  # Convert to MP4 format
                }],
            }

            with ydl.YoutubeDL(ydl_opts) as ydl_instance:
                info_dict = ydl_instance.extract_info(link, download=True)
                title = info_dict.get('title', 'Unknown Title')
                status_callback(f"Download Completed: {title}")
        except Exception as e:
            status_callback(f"Error: {e}")


    def download_audio(self, link, status_callback, audio_title=None, downloaded_folder=None):
        """
        Download audio from the video (MP3 format) using yt-dlp.
        
        :param link: Video URL
        :param status_callback: Function to update status messages
        :param audio_title: Custom title for the audio file (optional)
        :param downloaded_folder: Folder to save the audio file (optional)
        """
        self.start_time = time.time()

        # Determine the output folder
        output_folder = downloaded_folder if downloaded_folder else "downloaded_music"
        os.makedirs(output_folder, exist_ok=True)

        # Determine the audio output name
        output_name = f"{audio_title}.%(ext)s" if audio_title else "%(title)s.%(ext)s"

        try:
            ydl_opts = {
                'format': 'bestaudio/best',  # Download the best available audio quality
                'outtmpl': os.path.join(output_folder, output_name),  # Save in the determined folder
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',  # Extract audio
                    'preferredcodec': 'mp3',  # Convert to MP3 format
                    'preferredquality': '192',  # Set the MP3 quality (bitrate)
                }],
                'keepvideo': False,  # Do not keep the original video file
                'progress_hooks': [lambda d: self._progress_hook(d, status_callback)],
            }

            # Download and process the audio
            with ydl.YoutubeDL(ydl_opts) as ydl_instance:
                info_dict = ydl_instance.extract_info(link, download=True)
                title = info_dict.get('title', 'Unknown Title')
                status_callback(f"Audio Download Completed: {title}")
        except Exception as e:
            status_callback(f"Error: {e}")
            
    def _progress_hook(self, d, status_callback):
        """
        Hook to update download progress status with detailed info.
        """
        if d['status'] == 'downloading':
            # Extract progress details
            total_bytes = d.get('total_bytes', 0)  # Total size in bytes
            downloaded_bytes = d.get('downloaded_bytes', 0)  # Downloaded size in bytes
            speed = d.get('speed', 0)  # Download speed in bytes/second
            eta = d.get('eta', 0)  # Estimated time remaining in seconds
            fragment_index = d.get('fragment_index', None)  # Fragment number
            fragment_total = d.get('fragment_count', None)  # Total fragments

            # Calculate percent downloaded if possible
            if total_bytes > 0:
                percent = (downloaded_bytes / total_bytes) * 100
            else:
                percent = 0

            # Format data into a human-readable format
            percent_display = f"{percent:.1f}%" if total_bytes > 0 else "N/A"
            total_size_display = self.format_size(total_bytes) if total_bytes else "Unknown Size"
            downloaded_display = self.format_size(downloaded_bytes)
            speed_display = self.format_size(speed) + "/s" if speed else "N/A"
            eta_display = self.format_time(eta) if eta else "N/A"
            fragment_info = f"(frag {fragment_index}/{fragment_total})" if fragment_index and fragment_total else ""

            # Construct the status message
            status_message = (
                f"{percent_display} {downloaded_display} of ~{total_size_display} at {speed_display} "
                f"ETA {eta_display} {fragment_info}"
            )

            # Send status update through callback
            status_callback(status_message)

        elif d['status'] == 'finished':
            status_callback(f"[download] Download completed: {d.get('filename', 'Unknown')}")

        elif d['status'] == 'error':
            status_callback(f"[download] Error: {d.get('error', 'Unknown error')}")   

    def format_size(self, size_in_bytes):
        """Format size in bytes to human-readable format (MiB)."""
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} B"
        elif size_in_bytes < 1024 * 1024:
            return f"{size_in_bytes / 1024:.2f} KiB"
        elif size_in_bytes < 1024 * 1024 * 1024:
            return f"{size_in_bytes / (1024 * 1024):.2f} MiB"
        else:
            return f"{size_in_bytes / (1024 * 1024 * 1024):.2f} GiB"

    def format_time(self,seconds):
        """
        Format time given in seconds to a human-readable HH:MM:SS format.

        Parameters:
            seconds (int): Time in seconds.

        Returns:
            str: Time formatted as HH:MM:SS.
        """
        if seconds is None or seconds <= 0:
            return "N/A"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

