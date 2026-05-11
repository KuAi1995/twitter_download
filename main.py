"""
Twitter 图片/视频/文本下载工具

支持三种模式：
  - user: 按用户下载媒体（默认）
  - tag:  按 Tag/话题搜索下载
  - text: 下载用户纯文本推文
"""

import argparse
import hashlib
import logging
import os
import re
import time

from api import TwitterClient, Endpoint
from api.client import RateLimitError, ApiError
from config import Config, load_config
from downloader import download_media
from models.media import MediaItem
from output import CsvWriter, TextCsvWriter
from output.cache import DownloadCache
from parser import parse_timeline_response, parse_search_response, parse_text_timeline
from utils import time2stamp, stamp2time, del_special_char_with_hash

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _get_endpoint(config: Config) -> tuple[Endpoint, str]:
    """根据配置确定使用哪个 endpoint 和解析类型"""
    if config.has_highlights:
        return Endpoint.USER_HIGHLIGHTS, 'highlights'
    if config.has_likes:
        return Endpoint.USER_LIKES, 'media'
    if config.has_retweet:
        return Endpoint.USER_TWEETS, 'tweets'
    return Endpoint.USER_MEDIA, 'media'


def _resolve_time_range(config: Config) -> tuple[int, int]:
    """解析时间范围配置"""
    start = 655028357000   # 1990-10-04
    end = 2548484357000    # 2050-10-04
    if config.has_likes:
        return start, end
    if config.time_range:
        parts = config.time_range.split(':')
        if len(parts) == 2:
            start = time2stamp(parts[0])
            end = time2stamp(parts[1])
    return start, end


def _prepare_user_dir(save_path: str, name: str, screen_name: str) -> str:
    """创建或查找用户保存目录"""
    target = os.path.join(save_path, f'{name} (@{screen_name})')
    if os.path.exists(target):
        return target
    # 查找已有目录（用户可能改名）
    if os.path.exists(save_path):
        for item in os.listdir(save_path):
            item_path = os.path.join(save_path, item)
            if os.path.isdir(item_path) and screen_name in item:
                os.rename(item_path, target)
                return target
    os.makedirs(target, exist_ok=True)
    return target


def _get_sync_start_time(user_dir: str, default_start: int) -> int:
    """从已有文件推断同步起始时间"""
    files = sorted(os.listdir(user_dir))
    for f in reversed(files):
        if '-img_' in f or '-vid_' in f:
            match = re.findall(r'\d{4}-\d{2}-\d{2}', f)
            if match:
                return time2stamp(match[0])
    return default_start


def run_user_mode(config: Config):
    """按用户下载媒体"""
    client = TwitterClient(config.cookie, config.proxy)
    endpoint, parse_type = _get_endpoint(config)
    start_time, end_time = _resolve_time_range(config)

    for screen_name in config.user_list:
        try:
            logger.info(f'开始处理用户: {screen_name}')
            client.set_referer(f'https://twitter.com/{screen_name}')
            user = client.fetch_user_info(screen_name)
            logger.info(
                f'昵称: {user.name} | @{user.screen_name} | '
                f'总推数: {user.statuses_count} | 媒体数: {user.media_count}'
            )

            user_dir = _prepare_user_dir(config.save_path, user.name, user.screen_name)
            user_start = start_time
            if config.auto_sync:
                user_start = _get_sync_start_time(user_dir, start_time)

            cache = DownloadCache(user_dir) if config.down_log else None
            csv_writer = None
            if not config.has_likes:
                csv_writer = CsvWriter(user_dir, user.name, user.screen_name, config.time_range)

            cursor = ''
            first_page = True
            total_downloaded = 0
            total_processed = 0

            while True:
                try:
                    raw_data = client.fetch_timeline(endpoint, user.rest_id, cursor)
                except RateLimitError:
                    logger.error('API 调用次数已超限，停止')
                    break
                except ApiError as e:
                    logger.error(f'API 错误: {e}')
                    break

                result = parse_timeline_response(
                    raw_data, parse_type, cursor, first_page,
                    has_video=config.has_video,
                    start_time=user_start,
                    end_time=end_time,
                )
                first_page = False
                cursor = result.cursor

                total_processed += len(result.items)

                # 过滤缓存
                items = result.items
                if cache:
                    items = [item for item in items if cache.is_new(item.url)]

                if items:
                    count = download_media(
                        items, user_dir,
                        img_format=config.img_format,
                        max_concurrent=config.max_concurrent,
                        proxy=config.proxy,
                        log_output=config.log_output,
                    )
                    total_downloaded += count

                    if csv_writer:
                        for item in items:
                            csv_writer.write_item(item)

                logger.info(f'已扫描媒体: {total_processed}')

                if not result.has_more:
                    break

            if csv_writer:
                csv_writer.close()
            if cache:
                cache.save()
            logger.info(f'{user.name} 完成 | 共扫描 {total_processed} 个媒体，本次新下载 {total_downloaded} 个文件')

        except Exception as e:
            logger.error(f'用户 {screen_name} 处理失败: {e}')
            continue

    logger.info(f'全部完成 | API 调用次数: {client.request_count}')


def run_tag_mode(config: Config):
    """按 Tag 搜索下载"""
    client = TwitterClient(config.cookie, config.proxy)
    query = config.tag
    if config.tag_filter:
        query += ' ' + config.tag_filter

    folder = os.path.join(os.getcwd(), del_special_char_with_hash(config.tag))
    os.makedirs(folder, exist_ok=True)

    if config.text_mode:
        product = 'Latest'
        entries_count = 20
    elif config.tag_media_latest:
        product = 'Latest'
        entries_count = 20
    else:
        product = 'Media'
        entries_count = 50

    client.set_referer(f'https://twitter.com/search?q={config.tag}&src=typed_query&f=media')

    text_csv = TextCsvWriter(folder) if config.text_mode else None
    cursor = ''
    first_page = True
    pages = config.tag_count // entries_count

    for _ in range(pages):
        try:
            raw_data = client.fetch_search(query, cursor, entries_count, product)
        except RateLimitError:
            logger.error('API 调用次数已超限')
            break
        except ApiError as e:
            logger.error(f'API 错误: {e}')
            break

        if config.text_mode:
            # 文本模式：复用搜索解析但提取文本
            result = parse_search_response(raw_data, cursor, first_page, product=product)
            cursor = result.cursor
            first_page = False
            # 对于文本模式，从 items 中提取文本信息写入 CSV
            # 这里简化处理：搜索文本模式暂不支持（保持原有行为）
            if not result.has_more:
                break
        else:
            result = parse_search_response(raw_data, cursor, first_page, product=product)
            cursor = result.cursor
            first_page = False

            if result.items:
                download_media(
                    result.items, folder,
                    img_format='png',
                    max_concurrent=config.max_concurrent,
                    proxy=config.proxy,
                )

            if not result.has_more:
                break

    if text_csv:
        text_csv.close()
    logger.info(f'Tag 模式完成 | API 调用次数: {client.request_count}')


def run_text_mode(config: Config):
    """下载用户纯文本推文"""
    client = TwitterClient(config.cookie, config.proxy)
    start_time, end_time = _resolve_time_range(config)

    for screen_name in config.user_list:
        try:
            logger.info(f'开始处理用户: {screen_name}')
            client.set_referer(f'https://twitter.com/{screen_name}')
            user = client.fetch_user_info(screen_name)
            logger.info(f'昵称: {user.name} | @{user.screen_name}')

            folder = os.path.join(os.getcwd(), screen_name)
            os.makedirs(folder, exist_ok=True)

            with TextCsvWriter(folder, user.name, user.screen_name, config.time_range) as csv_writer:
                cursor = ''
                while True:
                    try:
                        raw_data = client.fetch_user_tweets_text(user.rest_id, cursor)
                    except RateLimitError:
                        logger.error('API 调用次数已超限')
                        break
                    except ApiError as e:
                        logger.error(f'API 错误: {e}')
                        break

                    result = parse_text_timeline(
                        raw_data, cursor,
                        start_time=start_time,
                        end_time=end_time,
                        has_retweet=config.has_retweet,
                    )
                    cursor = result.cursor

                    for item in result.items:
                        csv_writer.write_text_item(item)

                    if not result.has_more:
                        break

            logger.info(f'{user.name} 文本下载完成')

        except Exception as e:
            logger.error(f'用户 {screen_name} 处理失败: {e}')
            continue

    logger.info(f'全部完成 | API 调用次数: {client.request_count}')


def main():
    parser = argparse.ArgumentParser(description='Twitter 图片/视频/文本下载工具')
    parser.add_argument('--mode', choices=['user', 'tag', 'text'], default='user',
                        help='下载模式: user(按用户), tag(按话题), text(纯文本)')
    parser.add_argument('--config', default='settings.json', help='配置文件路径')
    args = parser.parse_args()

    config = load_config(args.config)

    start = time.time()

    if args.mode == 'user':
        run_user_mode(config)
    elif args.mode == 'tag':
        run_tag_mode(config)
    elif args.mode == 'text':
        run_text_mode(config)

    logger.info(f'总耗时: {time.time() - start:.1f}秒')


if __name__ == '__main__':
    main()
