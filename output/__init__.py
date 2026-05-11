"""CSV 统计文件生成"""

import csv
import os
from datetime import datetime

from models.media import MediaItem
from utils import stamp2time_csv


class CsvWriter:
    def __init__(self, save_path: str, user_name: str, screen_name: str, time_range: str):
        filename = f'{screen_name}-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.csv'
        self._path = os.path.join(save_path, filename)
        self._f = open(self._path, 'w', encoding='utf-8-sig', newline='')
        self._writer = csv.writer(self._f)
        self._writer.writerow([user_name, screen_name])
        self._writer.writerow([f'Tweet Range : {time_range}'])
        self._writer.writerow([f'Save Path : {save_path}'])
        self._writer.writerow([
            'Tweet Date', 'Display Name', 'User Name', 'Tweet URL',
            'Media Type', 'Media URL', 'Saved Filename', 'Tweet Content',
            'Favorite Count', 'Retweet Count', 'Reply Count'
        ])

    def write_item(self, item: MediaItem, saved_filename: str = ''):
        self._writer.writerow([
            stamp2time_csv(item.timestamp),
            item.author_name,
            f'@{item.author_screen_name}',
            item.tweet_url,
            item.media_type.capitalize(),
            item.url,
            saved_filename,
            item.tweet_text,
            item.stats.favorite_count if item.stats else 0,
            item.stats.retweet_count if item.stats else 0,
            item.stats.reply_count if item.stats else 0,
        ])

    def close(self):
        self._f.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class TextCsvWriter:
    """纯文本模式的 CSV"""
    def __init__(self, save_path: str, user_name: str = '', screen_name: str = '', time_range: str = ''):
        filename = f'{screen_name or "search"}-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}-text.csv'
        self._path = os.path.join(save_path, filename)
        self._f = open(self._path, 'w', encoding='utf-8-sig', newline='')
        self._writer = csv.writer(self._f)
        if user_name:
            self._writer.writerow([user_name, f'@{screen_name}'])
            self._writer.writerow([f'Tweet Range : {time_range}'])
        else:
            self._writer.writerow([f'Run Time : {datetime.now().strftime("%Y-%m-%d %H-%M-%S")}'])
        self._writer.writerow([
            'Tweet Date', 'Display Name', 'User Name', 'Tweet URL',
            'Tweet Content', 'Favorite Count', 'Retweet Count', 'Reply Count'
        ])

    def write_text_item(self, item):
        from models.media import TextItem
        self._writer.writerow([
            stamp2time_csv(item.timestamp),
            item.display_name,
            item.screen_name,
            item.tweet_url,
            item.tweet_text,
            item.stats.favorite_count if item.stats else 0,
            item.stats.retweet_count if item.stats else 0,
            item.stats.reply_count if item.stats else 0,
        ])

    def close(self):
        self._f.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
