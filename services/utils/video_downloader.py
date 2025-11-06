"""Shared video download logic"""
import os, requests

class VideoDownloader:
    def __init__(self, log_callback=None):
        self.log = log_callback or print
    
    def download(self, url: str, output_path: str, timeout=300) -> str:
        self.log(f"[Download] {os.path.basename(output_path)}")
        self.log(f"[DEBUG] Downloading from: {url[:100]}...")
        self.log(f"[DEBUG] Target path: {output_path}")
        
        with requests.get(url, stream=True, timeout=timeout, allow_redirects=True) as r:
            r.raise_for_status()
            total = int(r.headers.get('content-length', 0))
            self.log(f"[DEBUG] Content-Length: {total} bytes ({total/1024/1024:.2f} MB)")
            downloaded = 0
            with open(output_path, 'wb') as f:
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
        
        file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        if not os.path.exists(output_path) or file_size == 0:
            raise Exception("Download failed")
        
        self.log(f"[Download] ✓ Complete - File size: {file_size/1024/1024:.2f} MB")
        return output_path
