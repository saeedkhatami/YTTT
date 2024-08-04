import yt_dlp
import platform
import subprocess
import os
import sys
import logging
from PyQt5 import QtWidgets, QtCore

class QTextEditLogger(logging.Handler):
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit

    def emit(self, record):
        msg = self.format(record)
        self.text_edit.append(msg)
        self.text_edit.ensureCursorVisible()

# Initialize the logger
logger = logging.getLogger(__name__)

def display_intro():
    logger.info("YouTubeTerminalTerminal")
    os_type = platform.system()
    if os_type == "Windows":
        current_working_directory = os.getcwd()
        logger.info(f"Current Working Directory: {current_working_directory}")
        aria2_directory = os.path.join(current_working_directory, 'thirdparty', 'aria2')
        ffmpeg_directory = os.path.join(current_working_directory, 'thirdparty', 'ffmpeg', 'bin')
        logger.info(f"Aria2 Directory: {aria2_directory}")
        logger.info(f"FFMPEG Directory: {ffmpeg_directory}")
        os.environ["PATH"] += os.pathsep + aria2_directory
        os.environ["PATH"] += os.pathsep + ffmpeg_directory
        logger.info(f"Updated PATH: {os.environ['PATH']}")
        try:
            result = subprocess.run(['aria2c', '--version'], capture_output=True, text=True)
            logger.info(result.stdout)
        except FileNotFoundError:
            logger.error("aria2c not found in PATH")
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            logger.info(result.stdout)
        except FileNotFoundError:
            logger.error("ffmpeg not found in PATH")

def is_playlist(url):
    ydl_opts = {'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        return 'entries' in info_dict

def get_ydl_options(debug, quality, is_playlist, output_folder, use_proxy, proxy_url, progress_hook):
    outtmpl = os.path.join(output_folder, '%(title)s.%(ext)s') if not is_playlist else os.path.join(output_folder, '%(playlist_title)s', '%(playlist_index)03d-%(title)s.%(ext)s')
    
    common_opts = {
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'outtmpl': outtmpl,
        'external_downloader': 'aria2c',
        'external_downloader_args': [
            '--min-split-size=1M',
            '--max-connection-per-server=16',
            '--max-concurrent-downloads=16',
            '--split=16'
        ],
        'progress_hooks': [progress_hook]
    }

    if use_proxy:
        common_opts['proxy'] = proxy_url

    if debug:
        common_opts['verbose'] = True
    else:
        common_opts['quiet'] = True
    
    if quality == '480':
        common_opts['format'] = 'bestvideo[height<=480]+bestaudio/best[height<=480]'
    elif quality == '720':
        common_opts['format'] = 'bestvideo[height<=720]+bestaudio/best[height<=720]'
    elif quality == '1080':
        common_opts['format'] = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'
    else:
        common_opts['format'] = 'bestvideo+bestaudio/best'
                 
    return common_opts

class DownloadThread(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)

    def __init__(self, url, debug, quality, output_folder, use_proxy, proxy_url):
        super().__init__()
        self.url = url
        self.debug = debug
        self.quality = quality
        self.output_folder = output_folder
        self.use_proxy = use_proxy
        self.proxy_url = proxy_url

    def run(self):
        self.log_signal.emit(f"Starting download: {self.url}")
        self.log_signal.emit(f"Quality: {self.quality}")
        self.log_signal.emit(f"Output folder: {self.output_folder}")
        if self.use_proxy:
            self.log_signal.emit(f"Using proxy: {self.proxy_url}")

        self.download_video(self.url, self.debug, self.quality, self.output_folder, self.use_proxy, self.proxy_url)
        self.log_signal.emit("Download completed.")

    def download_video(self, url, debug, quality, output_folder, use_proxy, proxy_url):
        def progress_hook(d):
            if d['status'] == 'downloading':
                total_bytes = d.get('total_bytes', 0)
                downloaded_bytes = d.get('downloaded_bytes', 0)
                if total_bytes > 0:
                    progress = downloaded_bytes / total_bytes * 100
                    self.log_signal.emit(f"Download progress: {progress:.2f}%")

        playlist = is_playlist(url)
        ydl_opts = get_ydl_options(debug, quality, playlist, output_folder, use_proxy, proxy_url, progress_hook)
        
        # Redirect stdout and stderr to capture yt-dlp logs
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = self
        sys.stderr = self
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def write(self, msg):
        if msg.strip():
            self.log_signal.emit(msg.strip())

    def flush(self):
        pass

class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("YouTube Downloader")

        layout = QtWidgets.QVBoxLayout()

        self.debug_label = QtWidgets.QLabel("Enable DEBUG mode?")
        self.debug_checkbox = QtWidgets.QCheckBox()
        layout.addWidget(self.debug_label)
        layout.addWidget(self.debug_checkbox)

        self.url_label = QtWidgets.QLabel("YouTube URL:")
        self.url_input = QtWidgets.QLineEdit()
        layout.addWidget(self.url_label)
        layout.addWidget(self.url_input)

        self.quality_label = QtWidgets.QLabel("Quality:")
        self.quality_dropdown = QtWidgets.QComboBox()
        self.quality_dropdown.addItems(["480", "720", "1080", "best"])
        layout.addWidget(self.quality_label)
        layout.addWidget(self.quality_dropdown)

        self.output_label = QtWidgets.QLabel("Select Output Folder:")
        self.output_button = QtWidgets.QPushButton("Browse")
        self.output_button.clicked.connect(self.select_output_folder)
        self.output_folder = QtWidgets.QLabel("")
        layout.addWidget(self.output_label)
        layout.addWidget(self.output_button)
        layout.addWidget(self.output_folder)

        self.proxy_checkbox = QtWidgets.QCheckBox("Use Proxy")
        self.proxy_checkbox.stateChanged.connect(self.toggle_proxy_input)
        layout.addWidget(self.proxy_checkbox)

        self.proxy_url_label = QtWidgets.QLabel("Proxy URL:")
        self.proxy_url_input = QtWidgets.QLineEdit()
        self.proxy_url_input.setEnabled(False)
        layout.addWidget(self.proxy_url_label)
        layout.addWidget(self.proxy_url_input)

        self.download_button = QtWidgets.QPushButton("Download")
        self.download_button.clicked.connect(self.start_download)
        layout.addWidget(self.download_button)

        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        self.setLayout(layout)

        text_edit_logger = QTextEditLogger(self.log_text)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        text_edit_logger.setFormatter(formatter)
        logger.addHandler(text_edit_logger)
        logger.setLevel(logging.INFO)

    def toggle_proxy_input(self):
        enabled = self.proxy_checkbox.isChecked()
        self.proxy_url_input.setEnabled(enabled)

    def select_output_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder.setText(folder)

    def start_download(self):
        debug_mode = self.debug_checkbox.isChecked()
        url = self.url_input.text().strip()
        quality_mode = self.quality_dropdown.currentText().strip().lower()
        output_folder = self.output_folder.text().strip()
        use_proxy = self.proxy_checkbox.isChecked()
        proxy_url = self.proxy_url_input.text().strip()

        if not url or not quality_mode or not output_folder:
            QtWidgets.QMessageBox.warning(self, "Input Error", "Please fill all fields and select an output folder.")
            return

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        self.download_thread = DownloadThread(url, debug_mode, quality_mode, output_folder, use_proxy, proxy_url)
        self.download_thread.log_signal.connect(self.log_text.append)
        self.download_thread.start()

def main():
    display_intro()
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
