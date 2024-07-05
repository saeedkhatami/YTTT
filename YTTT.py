import yt_dlp

def display_intro():
    print("YouTubeTerminalTerminal")

def get_ydl_options(debug):
    common_opts = {
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'outtmpl': './%(playlist_title)s/%(playlist_index)03d-%(title)s.%(ext)s',
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
    
    return common_opts

def download_video(url, debug):
    ydl_opts = get_ydl_options(debug)
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def menu():
    display_intro()
    debug_mode = input("DEBUG? (y/n): ").strip().lower() == 'y'
    url = input("Give me your YouTube URL: ").strip()
    # quality_mode = input("Quality(480/720/1080/best): ")
    download_video(url, debug_mode)

if __name__ == "__main__":
    menu()

