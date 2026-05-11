"""下载缓存，避免重复下载"""

import os
import pickle


class DownloadCache:
    def __init__(self, save_path: str):
        self._path = os.path.join(save_path, 'cache_data.log')
        if os.path.exists(self._path) and os.path.getsize(self._path) > 0:
            try:
                with open(self._path, 'rb') as f:
                    self._data: set = pickle.load(f)
            except (pickle.UnpicklingError, EOFError):
                self._data = set()
        else:
            self._data = set()

    def is_new(self, url: str) -> bool:
        """如果 URL 未下载过返回 True，并记录"""
        if url in self._data:
            return False
        self._data.add(url)
        return True

    def save(self):
        with open(self._path, 'wb') as f:
            pickle.dump(self._data, f)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.save()
