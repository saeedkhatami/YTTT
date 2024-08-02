import yt_dlp
import platform
import subprocess
import os

def display_intro():
    print("YouTubeTerminalTerminal")

def is_playlist(url):
    ydl_opts = {'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        return 'entries' in info_dict

def get_ydl_options(debug, quality, is_playlist):
    outtmpl = './%(title)s.%(ext)s' if not is_playlist else './%(playlist_title)s/%(playlist_index)03d-%(title)s.%(ext)s'
    
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

def download_video(url, debug, quality):
    playlist = is_playlist(url)
    ydl_opts = get_ydl_options(debug, quality, playlist)
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def download_binaries():
    os_type = platform.system()
    if os_type == "Linux":
        print("Detected Linux. Installing ffmpeg and aria2 using apt.")
        subprocess.run(["sudo", "apt", "update"])
        subprocess.run(["sudo", "apt", "install", "-y", "ffmpeg", "aria2"])
    elif os_type == "Windows":
        print("Detected Windows. Downloading ffmpeg and aria2 binaries.")
        if not os.path.exists("ffmpeg.exe"):
            subprocess.run(["curl", "-L", "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip", "-o", "ffmpeg.zip"])
            subprocess.run(["tar", "-xf", "ffmpeg.zip"])
            # install via latest at next update, and curl and tar
        if not os.path.exists("aria2c.exe"):
            subprocess.run(["curl", "-L", "https://github.com/aria2/aria2/releases/download/release-1.36.0/aria2-1.36.0-win-64bit-build1.zip", "-o", "aria2.zip"])
            subprocess.run(["tar", "-xf", "aria2.zip"])
            # install via latest at next update, and curl and tar
    # those are not installed before on windows
    else:
        print(f"Unsupported OS: {os_type}")
        exit(1)

def menu():
    display_intro()
    download_binaries()
    debug_mode = input("DEBUG? (y/n): ").strip().lower() == 'y'
    url = input("Give me your YouTube URL: ").strip()
    quality_mode = input("Quality (480/720/1080/best): ").strip().lower()
    download_video(url, debug_mode, quality_mode)

if __name__ == "__main__":
    menu()
