import yt_dlp
import platform
import subprocess
import os
import sys
from PyQt5 import QtWidgets, QtCore

def display_intro():
    print("YouTubeTerminalTerminal")
    os_type = platform.system()
    if os_type == "Windows":
        current_working_directory = os.getcwd()
        print(f"Current Working Directory: {current_working_directory}")
        aria2_directory = os.path.join(current_working_directory, 'thirdparty', 'aria2')
        ffmpeg_directory = os.path.join(current_working_directory, 'thirdparty', 'ffmpeg', 'bin')
        print(f"Aria2 Directory: {aria2_directory}")
        print(f"FFMPEG Directory: {ffmpeg_directory}")
        os.environ["PATH"] += os.pathsep + aria2_directory
        os.environ["PATH"] += os.pathsep + ffmpeg_directory
        print(f"Updated PATH: {os.environ['PATH']}")
        try:
            result = subprocess.run(['aria2c', '--version'], capture_output=True, text=True)
            print(result.stdout)
        except FileNotFoundError:
            print("aria2c not found in PATH")
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            print(result.stdout)
        except FileNotFoundError:
            print("ffmpeg not found in PATH")

def is_playlist(url):
    ydl_opts = {'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        return 'entries' in info_dict

def get_ydl_options(debug, quality, is_playlist, output_folder):
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
        'proxy': 'PROXY-URL'
    }

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

def download_video(url, debug, quality, output_folder):
    playlist = is_playlist(url)
    ydl_opts = get_ydl_options(debug, quality, playlist, output_folder)
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

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

        self.quality_label = QtWidgets.QLabel("Quality (480/720/1080/best):")
        self.quality_input = QtWidgets.QLineEdit()
        layout.addWidget(self.quality_label)
        layout.addWidget(self.quality_input)

        self.output_label = QtWidgets.QLabel("Select Output Folder:")
        self.output_button = QtWidgets.QPushButton("Browse")
        self.output_button.clicked.connect(self.select_output_folder)
        self.output_folder = QtWidgets.QLabel("")
        layout.addWidget(self.output_label)
        layout.addWidget(self.output_button)
        layout.addWidget(self.output_folder)

        self.download_button = QtWidgets.QPushButton("Download")
        self.download_button.clicked.connect(self.start_download)
        layout.addWidget(self.download_button)

        self.setLayout(layout)

    def select_output_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder.setText(folder)

    def start_download(self):
        debug_mode = self.debug_checkbox.isChecked()
        url = self.url_input.text().strip()
        quality_mode = self.quality_input.text().strip().lower()
        output_folder = self.output_folder.text().strip()

        if not url or not quality_mode or not output_folder:
            QtWidgets.QMessageBox.warning(self, "Input Error", "Please fill all fields and select an output folder.")
            return

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        download_video(url, debug_mode, quality_mode, output_folder)
        QtWidgets.QMessageBox.information(self, "Download Complete", "The download has been completed.")

def main():
    display_intro()
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
