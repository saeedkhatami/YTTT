import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'awjrbahgfvyui2f3576agkhfbkae')
    DOWNLOAD_FOLDER = os.getenv('DOWNLOAD_FOLDER', 'downloads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'mp4', 'mp3'}