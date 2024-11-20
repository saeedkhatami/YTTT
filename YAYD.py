import yt_dlp
import platform
import subprocess
import os
import sys
import logging
from PyQt5 import QtWidgets, QtCore
from datetime import datetime


class QTextEditLogger(logging.Handler):
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit

    def emit(self, record):
        msg = self.format(record)
        self.text_edit.append(msg)
        self.text_edit.ensureCursorVisible()


logger = logging.getLogger(__name__)


def display_intro():
    logger.info("Yet Another Youtube Downloader")
    os_type = platform.system()
    if os_type == "Windows":
        current_working_directory = os.getcwd()
        logger.info(f"Current Working Directory: {current_working_directory}")
        # aria2_directory = os.path.join(current_working_directory, "thirdparty", "aria2")
        ffmpeg_directory = os.path.join(
            current_working_directory, "thirdparty", "ffmpeg", "bin"
        )

        # if not os.path.exists(aria2_directory):
        #     logger.error(f"Aria2 directory not found: {aria2_directory}")
        if not os.path.exists(ffmpeg_directory):
            logger.error(f"FFMPEG directory not found: {ffmpeg_directory}")

        os.environ["PATH"] += (
            os.pathsep + os.pathsep + ffmpeg_directory
        )
        logger.info(f"Updated PATH: {os.environ['PATH']}")

        check_dependencies()


def check_dependencies():
    """Check if required dependencies are available"""
    dependencies = {"ffmpeg": "FFmpeg"}

    for cmd, name in dependencies.items():
        try:
            result = subprocess.run([cmd, "--version"], capture_output=True, text=True)
            logger.info(f"{name} found: {result.stdout.splitlines()}")
        except FileNotFoundError:
            logger.error(
                f"{name} not found in PATH. Please install {name} to continue."
            )
            return False
    return True


def format_size(bytes):
    """Convert bytes to human readable format"""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024
    return f"{bytes:.2f} TB"


def is_playlist(url):
    """
    Check if the given URL is a playlist.
    Returns (is_playlist, error_message)
    """
    try:
        ydl_opts = {
            "quiet": True,
            "extract_flat": True,
            "force_generic_extractor": False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            if info_dict is None:
                return False, "Could not extract video information"

            is_playlist = bool(
                "entries" in info_dict or info_dict.get("_type") == "playlist"
            )

            logger.debug(f"URL type check - Playlist: {is_playlist}")
            if is_playlist:
                playlist_title = info_dict.get("title", "Unknown Playlist")
                video_count = (
                    len(info_dict.get("entries", []))
                    if "entries" in info_dict
                    else "Unknown"
                )
                logger.info(
                    f"Detected playlist: {playlist_title} with {video_count} videos"
                )

            return is_playlist, None

    except Exception as e:
        error_msg = f"Error checking URL type: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


class DownloadThread(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)
    progress_signal = QtCore.pyqtSignal(float)
    status_signal = QtCore.pyqtSignal(str)

    def __init__(
        self, url, debug, quality, output_folder, use_proxy, proxy_url, audio_only=False
    ):
        super().__init__()
        self.url = url
        self.debug = debug
        self.quality = quality
        self.output_folder = output_folder
        self.use_proxy = use_proxy
        self.proxy_url = proxy_url
        self.audio_only = audio_only
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True
        self.status_signal.emit("Download cancelled")

    def run(self):
        try:
            self.download_video()
        except Exception as e:
            self.log_signal.emit(f"Error during download: {str(e)}")
            self.status_signal.emit("Download failed")

    def download_video(self):
        def progress_hook(d):
            if self.is_cancelled:
                raise Exception("Download cancelled by user")

            if d["status"] == "downloading":
                total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                downloaded_bytes = d.get("downloaded_bytes", 0)
                speed = d.get("speed", 0)
                eta = d.get("eta", 0)

                if total_bytes > 0:
                    progress = (downloaded_bytes / total_bytes) * 100
                    self.progress_signal.emit(progress)

                    status = f"Downloading: {progress:.1f}% "
                    status += (
                        f"({format_size(downloaded_bytes)}/{format_size(total_bytes)}) "
                    )
                    if speed:
                        status += f"@ {format_size(speed)}/s "
                    if eta:
                        status += f"ETA: {eta}s"

                    self.status_signal.emit(status)

            elif d["status"] == "finished":
                self.status_signal.emit("Download completed. Processing video...")

        try:
            is_playlist_bool, error_msg = is_playlist(self.url)
            if error_msg:
                self.log_signal.emit(f"Warning: {error_msg}")

                is_playlist_bool = False

            ydl_opts = self.get_ydl_options(is_playlist_bool, progress_hook)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.log_signal.emit(f"Starting download for: {self.url}")
                ydl.download([self.url])

            self.status_signal.emit("Download and processing completed!")

        except Exception as e:
            self.log_signal.emit(f"Error: {str(e)}")
            self.status_signal.emit("Download failed")
            raise

    def get_ydl_options(self, is_playlist, progress_hook):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if is_playlist:
            outtmpl = os.path.join(
                self.output_folder,
                "%(playlist_title)s",
                f"{timestamp}_%(playlist_index)03d-%(title)s.%(ext)s",
            )
        else:
            outtmpl = os.path.join(self.output_folder, f"{timestamp}_%(title)s.%(ext)s")

        opts = {
            "outtmpl": outtmpl,
            "progress_hooks": [progress_hook],
            "quiet": not self.debug,
            "verbose": self.debug,
        }

        if self.audio_only:
            opts.update(
                {
                    "format": "bestaudio/best",
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "192",
                        }
                    ],
                }
            )
        else:
            quality_map = {
                "480": "bestvideo[height<=480]+bestaudio/best[height<=480]",
                "720": "bestvideo[height<=720]+bestaudio/best[height<=720]",
                "1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                "best": "bestvideo+bestaudio/best",
            }
            opts.update(
                {
                    "format": quality_map.get(self.quality, "bestvideo+bestaudio/best"),
                    "merge_output_format": "mp4",
                }
            )

        if self.use_proxy and self.proxy_url:
            opts["proxy"] = self.proxy_url

        return opts


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.download_thread = None

    def initUI(self):
        self.setWindowTitle("Yet Another Youtube Downloader")
        self.setMinimumWidth(600)

        layout = QtWidgets.QVBoxLayout()

        url_group = QtWidgets.QGroupBox("Video URL")
        url_layout = QtWidgets.QVBoxLayout()
        self.url_input = QtWidgets.QLineEdit()
        self.url_input.setPlaceholderText("Enter YouTube URL here...")
        url_layout.addWidget(self.url_input)
        url_group.setLayout(url_layout)
        layout.addWidget(url_group)

        options_group = QtWidgets.QGroupBox("Download Options")
        options_layout = QtWidgets.QGridLayout()

        self.debug_checkbox = QtWidgets.QCheckBox("Enable Debug Mode")
        options_layout.addWidget(self.debug_checkbox, 0, 0)

        self.audio_only_checkbox = QtWidgets.QCheckBox("Audio Only (MP3)")
        options_layout.addWidget(self.audio_only_checkbox, 0, 1)

        quality_label = QtWidgets.QLabel("Quality:")
        self.quality_dropdown = QtWidgets.QComboBox()
        self.quality_dropdown.addItems(["480", "720", "1080", "best"])
        options_layout.addWidget(quality_label, 1, 0)
        options_layout.addWidget(self.quality_dropdown, 1, 1)

        output_label = QtWidgets.QLabel("Output Folder:")
        self.output_button = QtWidgets.QPushButton("Browse")
        self.output_button.clicked.connect(self.select_output_folder)
        self.output_folder = QtWidgets.QLabel("")
        options_layout.addWidget(output_label, 2, 0)
        options_layout.addWidget(self.output_button, 2, 1)
        options_layout.addWidget(self.output_folder, 2, 2)

        self.proxy_checkbox = QtWidgets.QCheckBox("Use Proxy")
        self.proxy_checkbox.stateChanged.connect(self.toggle_proxy_input)
        self.proxy_url_input = QtWidgets.QLineEdit()
        self.proxy_url_input.setEnabled(False)
        self.proxy_url_input.setPlaceholderText("http://proxy:port")
        options_layout.addWidget(self.proxy_checkbox, 3, 0)
        options_layout.addWidget(self.proxy_url_input, 3, 1, 1, 2)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        progress_group = QtWidgets.QGroupBox("Download Progress")
        progress_layout = QtWidgets.QVBoxLayout()

        self.progress_bar = QtWidgets.QProgressBar()
        self.status_label = QtWidgets.QLabel("Ready")
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)

        button_layout = QtWidgets.QHBoxLayout()
        self.download_button = QtWidgets.QPushButton("Download")
        self.download_button.clicked.connect(self.start_download)
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_download)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.download_button)
        button_layout.addWidget(self.cancel_button)
        progress_layout.addLayout(button_layout)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        log_group = QtWidgets.QGroupBox("Log")
        log_layout = QtWidgets.QVBoxLayout()
        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        self.setLayout(layout)

        text_edit_logger = QTextEditLogger(self.log_text)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        text_edit_logger.setFormatter(formatter)
        logger.addHandler(text_edit_logger)
        logger.setLevel(logging.INFO)

    def toggle_proxy_input(self):
        self.proxy_url_input.setEnabled(self.proxy_checkbox.isChecked())

    def select_output_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Output Folder"
        )
        if folder:
            self.output_folder.setText(folder)

    def update_progress(self, progress):
        self.progress_bar.setValue(int(progress))

    def update_status(self, status):
        self.status_label.setText(status)

    def start_download(self):
        url = self.url_input.text().strip()
        output_folder = self.output_folder.text().strip()

        if not url or not output_folder:
            QtWidgets.QMessageBox.warning(
                self,
                "Input Error",
                "Please fill in the URL and select an output folder.",
            )
            return

        if not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder)
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self, "Error", f"Could not create output folder: {str(e)}"
                )
                return

        self.download_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)

        self.download_thread = DownloadThread(
            url=url,
            debug=self.debug_checkbox.isChecked(),
            quality=self.quality_dropdown.currentText(),
            output_folder=output_folder,
            use_proxy=self.proxy_checkbox.isChecked(),
            proxy_url=self.proxy_url_input.text().strip(),
            audio_only=self.audio_only_checkbox.isChecked(),
        )

        self.download_thread.log_signal.connect(self.log_text.append)
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.status_signal.connect(self.update_status)
        self.download_thread.finished.connect(self.download_finished)

        self.download_thread.start()

    def cancel_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.cancel()
            self.cancel_button.setEnabled(False)

    def download_finished(self):
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.download_thread = None


def main():
    if not check_dependencies():
        sys.exit(1)

    app = QtWidgets.QApplication(sys.argv)

    app.setStyle("Fusion")

    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
