
import os
import httpx
from pathlib import Path
from typing import Optional
from core.logger.logger_manager import get_logger_manager

class FileDownloader:
    def __init__(self, timeout: float = 60.0, proxy: Optional[str] = None):
        self.logger = get_logger_manager().get_logger(self.__class__.__name__)

        self.client = httpx.Client(
            proxy=proxy,
            timeout=timeout,
            follow_redirects=True
        )

    def download(self, url: str, save_path: str) -> bool:
        if not self.client or self.client.is_closed:
            self.logger.error("Client is not initialized or closed")
            return False

        path = Path(save_path)
        temp_path = path.with_suffix(path.suffix + ".tmp")

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Start downloading: {url}")

            with self.client.stream("GET", url) as response:
                response.raise_for_status()
                with open(temp_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)

            if temp_path.exists():
                temp_path.replace(path)

            self.logger.info(f"Saved to: {path}")
            return True

        except Exception as e:
            self.logger.error(f"Download failed {url}: {e}")
            if temp_path.exists():
                os.remove(temp_path)
            return False

    def close(self):
        if not self.client or self.client.is_closed:
            return

        self.client.close()
        self.client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()