import yt_dlp
import platform
import subprocess
import os
import sys

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

def menu():
    display_intro()
    debug_mode = input("DEBUG? (y/n): ").strip().lower() == 'y'
    url = input("Give me your YouTube URL: ").strip()
    quality_mode = input("Quality (480/720/1080/best): ").strip().lower()
    output_folder = input("Enter the output folder: ").strip()
    if not os.path.exists(output_folder):
        print(f"The folder '{output_folder}' does not exist. Creating it.")
        os.makedirs(output_folder)
    download_video(url, debug_mode, quality_mode, output_folder)

if __name__ == "__main__":
    menu()
