from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import logging
from config import Config
import threading
import time
import re


def create_app():
    app = Flask(__name__, static_folder="static")
    app.config.from_object(Config)
    CORS(app)

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    os.makedirs(app.config["DOWNLOAD_FOLDER"], exist_ok=True)

    active_downloads = {}

    class DownloadManager:
        def __init__(self, url, options, download_id):
            self.url = url
            self.options = options
            self.download_id = download_id
            self.progress = 0
            self.status = "pending"
            self.cancelled = False
            self.error = None
            self.output_file = None
            self.final_filename = None

        def progress_hook(self, d):
            if self.cancelled:
                raise Exception("Download cancelled")

            if d["status"] == "downloading":
                total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                downloaded_bytes = d.get("downloaded_bytes", 0)

                if total_bytes > 0:
                    self.progress = (downloaded_bytes / total_bytes) * 100
                    self.status = f"Downloading: {self.progress:.1f}%"

            elif d["status"] == "finished":
                self.status = "Processing"
                self.output_file = d["filename"]

            elif d["status"] == "merged":
                self.final_filename = d.get("filename")
                self.output_file = d.get("filename")

        def get_ydl_opts(self):
            output_template = os.path.join(
                app.config["DOWNLOAD_FOLDER"],
                f"%(title).100s_{self.download_id}.%(ext)s",
            )

            opts = {
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "outtmpl": output_template,
                "progress_hooks": [self.progress_hook],
                "merge_output_format": "mp4",
                "restrictfilenames": True,
                "windowsfilenames": True,
                "postprocessor_hooks": [self.progress_hook],
            }

            if self.options.get("audio_only"):
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
                quality = self.options.get("quality", "best")
                if quality != "best":
                    opts["format"] = (
                        f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"
                    )

            if self.options.get("use_proxy"):
                proxy_url = self.options.get("proxy_url")
                if proxy_url:
                    opts["proxy"] = proxy_url

            return opts

        def start_download(self):
            try:
                with yt_dlp.YoutubeDL(self.get_ydl_opts()) as ydl:
                    self.status = "Starting download"
                    info = ydl.extract_info(self.url, download=True)
                    if not self.cancelled:
                        self.status = "Completed"
                        self.progress = 100

                        if not self.final_filename and info:
                            filename = ydl.prepare_filename(info)
                            if os.path.exists(filename):
                                self.final_filename = filename
                                self.output_file = filename

            except Exception as e:
                self.status = "Failed"
                self.error = str(e)
                logger.error(f"Download error: {e}")

    @app.route("/")
    def index():
        return app.send_static_file("index.html")

    @app.route("/api/download", methods=["POST"])
    def start_download():
        data = request.json
        url = data.get("url")

        if not url:
            return jsonify({"error": "URL is required"}), 400

        download_id = str(int(time.time()))
        options = {
            "quality": data.get("quality", "best"),
            "audio_only": data.get("audioOnly", False),
            "use_proxy": data.get("useProxy", False),
            "proxy_url": data.get("proxyUrl"),
        }

        download_manager = DownloadManager(url, options, download_id)
        active_downloads[download_id] = download_manager

        thread = threading.Thread(target=download_manager.start_download, daemon=True)
        thread.start()

        return jsonify({"download_id": download_id, "message": "Download started"})

    @app.route("/api/status/<download_id>")
    def get_status(download_id):
        download = active_downloads.get(download_id)
        if not download:
            return jsonify({"error": "Download not found"}), 404

        return jsonify(
            {
                "status": download.status,
                "progress": download.progress,
                "error": download.error,
            }
        )

    @app.route("/api/cancel/<download_id>")
    def cancel_download(download_id):
        download = active_downloads.get(download_id)
        if not download:
            return jsonify({"error": "Download not found"}), 404

        download.cancelled = True
        return jsonify({"message": "Download cancelled"})

    @app.route("/api/download/<download_id>")
    def get_file(download_id):
        download = active_downloads.get(download_id)
        if not download:
            return jsonify({"error": "Download not found"}), 404

        if not download.output_file or not os.path.exists(download.output_file):
            download_dir = app.config["DOWNLOAD_FOLDER"]
            possible_files = [f for f in os.listdir(download_dir) if download_id in f]
            if possible_files:
                download.output_file = os.path.join(download_dir, possible_files[0])
            else:
                return jsonify({"error": "File not found"}), 404

        try:
            return send_file(
                download.output_file,
                as_attachment=True,
                download_name=os.path.basename(download.output_file),
            )
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            return jsonify({"error": "Error sending file"}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
