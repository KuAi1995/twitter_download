"""异步并发下载器"""

import asyncio
import logging
import os

import httpx

from models.media import MediaItem
from utils import stamp2time

logger = logging.getLogger(__name__)


def _quote_url(url: str) -> str:
    return url.replace('{', '%7B').replace('}', '%7D')


def download_media(
    items: list[MediaItem],
    save_path: str,
    img_format: str = 'png',
    max_concurrent: int = 8,
    proxy: str | None = None,
    log_output: bool = False,
) -> int:
    """
    下载媒体列表到指定目录。返回成功下载数量。
    """
    if not items:
        return 0

    count = 0

    async def _run():
        nonlocal count
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _download_one(item: MediaItem, order: int):
            nonlocal count
            time_str = stamp2time(item.timestamp)
            suffix = 'retweet' if item.is_retweet else ''
            type_tag = 'vid' if item.media_type == 'video' else 'img'
            prefix = f'{time_str}-{type_tag}'
            if suffix:
                prefix += f'-{suffix}'

            if item.media_type == 'video':
                filename = f'{prefix}_{order}.mp4'
                url = item.url
            else:
                filename = f'{prefix}_{order}.{img_format}'
                url = f'{item.url}?format={img_format}&name=4096x4096'

            filepath = os.path.join(save_path, filename)

            for attempt in range(1, 11):
                try:
                    async with semaphore:
                        async with httpx.AsyncClient(proxy=proxy) as client:
                            response = await client.get(_quote_url(url), timeout=(3.05, 16))
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    count += 1
                    if log_output:
                        logger.info(f'{filepath} =====> 下载完成')
                    return filepath
                except Exception as e:
                    logger.warning(f'{filepath} =====> 第{attempt}次下载失败: {e}')
            else:
                logger.error(f'{filepath} =====> 超过最大重试次数，已跳过')
                return None

        await asyncio.gather(*[
            asyncio.create_task(_download_one(item, i))
            for i, item in enumerate(items)
        ])

    asyncio.run(_run())
    return count
