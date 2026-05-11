"""解析 Twitter API 时间线/搜索响应，提取推文条目列表"""

import logging
from dataclasses import dataclass

from models.media import MediaItem, TextItem, TweetStats
from .tweet import parse_tweet_media, _unwrap_tweet, _extract_timestamp

logger = logging.getLogger(__name__)


@dataclass
class TimelineResult:
    """时间线解析结果"""
    items: list[MediaItem]
    cursor: str
    has_more: bool


@dataclass
class TextTimelineResult:
    """纯文本时间线解析结果"""
    items: list[TextItem]
    cursor: str
    has_more: bool


def parse_timeline_response(
    raw_data: dict,
    endpoint_type: str,
    cursor: str,
    first_page: bool,
    has_video: bool = True,
    start_time: int = 0,
    end_time: int = 2548484357000,
) -> TimelineResult:
    """
    解析用户时间线响应，返回媒体列表和分页信息。

    endpoint_type: 'media' | 'tweets' | 'highlights' | 'likes'
    """
    items = []
    new_cursor = cursor
    has_more = True

    try:
        if endpoint_type == 'highlights':
            entries = raw_data['data']['user']['result']['timeline']['timeline']['instructions'][-1]['entries']
        else:
            entries = raw_data['data']['user']['result']['timeline_v2']['timeline']['instructions']

        if endpoint_type in ('tweets', 'highlights'):
            # tweets/highlights 模式：entries 直接是列表
            if endpoint_type == 'highlights':
                tweet_entries = entries
            else:
                tweet_entries = entries[-1]['entries']

            # 检查是否到末尾
            if tweet_entries and 'cursor-top' in tweet_entries[0].get('entryId', ''):
                return TimelineResult(items=[], cursor=new_cursor, has_more=False)

            for entry in tweet_entries:
                entry_id = entry.get('entryId', '')
                if 'cursor-bottom' in entry_id:
                    new_cursor = entry['content']['value']
                    continue
                if 'promoted-tweet' in entry_id:
                    continue

                tweet_result = _extract_tweet_result(entry, 'content')
                if not tweet_result:
                    continue

                tweet_items = parse_tweet_media(tweet_result, has_video=has_video)
                filtered = _filter_by_time(tweet_items, start_time, end_time)
                if filtered is None:
                    # 超出时间范围下界
                    return TimelineResult(items=items, cursor=new_cursor, has_more=False)
                items.extend(filtered)

        else:
            # media/likes 模式：moduleItems 结构
            instructions = entries

            # 提取 cursor
            for entry in instructions[-1].get('entries', []):
                if 'bottom' in entry.get('entryId', ''):
                    new_cursor = entry['content']['value']

            # 提取推文列表
            if first_page:
                tweet_list = instructions[-1]['entries'][0]['content'].get('items', [])
            else:
                if 'moduleItems' not in instructions[0]:
                    return TimelineResult(items=[], cursor=new_cursor, has_more=False)
                tweet_list = instructions[0]['moduleItems']

            for entry in tweet_list:
                tweet_result = _extract_tweet_result(entry, 'item')
                if not tweet_result:
                    continue

                tweet_items = parse_tweet_media(tweet_result, has_video=has_video)
                filtered = _filter_by_time(tweet_items, start_time, end_time)
                if filtered is None:
                    return TimelineResult(items=items, cursor=new_cursor, has_more=False)
                items.extend(filtered)

    except (KeyError, TypeError, IndexError) as e:
        logger.error(f'解析时间线响应失败: {e}')
        return TimelineResult(items=[], cursor=new_cursor, has_more=False)

    return TimelineResult(items=items, cursor=new_cursor, has_more=has_more)


def parse_search_response(
    raw_data: dict,
    cursor: str,
    first_page: bool,
    has_video: bool = True,
    product: str = 'Media',
) -> TimelineResult:
    """解析搜索结果响应"""
    items = []
    new_cursor = cursor

    try:
        if first_page:
            entries = raw_data['data']['search_by_raw_query']['search_timeline']['timeline']['instructions'][-1]['entries']
            if len(entries) <= 2:
                return TimelineResult(items=[], cursor=new_cursor, has_more=False)
            new_cursor = entries[-1]['content']['value']

            if product == 'Media':
                tweet_list = entries[0]['content']['items']
            else:
                tweet_list = entries[:-2]
        else:
            instructions = raw_data['data']['search_by_raw_query']['search_timeline']['timeline']['instructions']
            new_cursor = instructions[-1]['entry']['content']['value']

            if product == 'Media':
                if 'moduleItems' not in instructions[0]:
                    return TimelineResult(items=[], cursor=new_cursor, has_more=False)
                tweet_list = instructions[0]['moduleItems']
            else:
                if 'entries' not in instructions[0]:
                    return TimelineResult(items=[], cursor=new_cursor, has_more=False)
                tweet_list = instructions[0]['entries']

        for entry in tweet_list:
            if product == 'Media':
                tweet_result = _extract_tweet_result(entry, 'item')
            else:
                entry_id = entry.get('entryId', '')
                if 'promoted' in entry_id:
                    continue
                try:
                    tweet_result = entry['content']['itemContent']['tweet_results']['result']
                except (KeyError, TypeError):
                    continue

            if not tweet_result:
                continue

            tweet_items = parse_tweet_media(tweet_result, has_video=has_video)
            items.extend(tweet_items)

    except (KeyError, TypeError, IndexError) as e:
        logger.error(f'解析搜索响应失败: {e}')
        return TimelineResult(items=[], cursor=new_cursor, has_more=False)

    return TimelineResult(items=items, cursor=new_cursor, has_more=True)


def parse_text_timeline(
    raw_data: dict,
    cursor: str,
    start_time: int = 0,
    end_time: int = 2548484357000,
    has_retweet: bool = False,
) -> TextTimelineResult:
    """解析用户推文时间线，提取纯文本"""
    items = []
    new_cursor = cursor

    try:
        entries = raw_data['data']['user']['result']['timeline_v2']['timeline']['instructions'][-1]['entries']
        if len(entries) <= 2:
            return TextTimelineResult(items=[], cursor=new_cursor, has_more=False)

        entry_cursor = entries[-1]['content']['value']
        if entry_cursor == cursor:
            return TextTimelineResult(items=[], cursor=new_cursor, has_more=False)
        new_cursor = entry_cursor

        for entry in entries:
            entry_id = entry.get('entryId', '')
            if 'promoted-tweet' in entry_id:
                continue
            if 'tweet' not in entry_id:
                continue

            try:
                raw_text = entry['content']['itemContent']['tweet_results']['result']
            except (KeyError, TypeError):
                continue

            raw_text = _unwrap_tweet(raw_text)
            legacy = raw_text.get('legacy', {})
            timestamp = _extract_timestamp(raw_text)
            if timestamp is None:
                continue

            # 处理转推
            if 'retweeted_status_result' in legacy:
                if not has_retweet:
                    continue
                rt = _unwrap_tweet(legacy['retweeted_status_result']['result'])
                try:
                    display_name = rt['core']['user_results']['result']['legacy']['name']
                    screen_name = '@' + rt['core']['user_results']['result']['legacy']['screen_name']
                except (KeyError, TypeError):
                    continue
                legacy = rt.get('legacy', {})
            else:
                display_name = ''
                screen_name = ''

            # 时间过滤
            from utils import time_comparison
            result = time_comparison(timestamp, start_time, end_time)
            if not result[1]:
                return TextTimelineResult(items=items, cursor=new_cursor, has_more=False)
            if not result[0]:
                continue

            try:
                status_id = legacy['conversation_id_str']
                tweet_screen_name = raw_text['core']['user_results']['result']['legacy']['screen_name']
                tweet_url = f'https://twitter.com/{tweet_screen_name}/status/{status_id}'
                tweet_text = legacy.get('full_text', '').split('https://t.co/')[0]
            except (KeyError, TypeError):
                continue

            stats = TweetStats(
                favorite_count=legacy.get('favorite_count', 0),
                retweet_count=legacy.get('retweet_count', 0),
                reply_count=legacy.get('reply_count', 0),
            )

            items.append(TextItem(
                timestamp=timestamp,
                display_name=display_name,
                screen_name=screen_name,
                tweet_url=tweet_url,
                tweet_text=tweet_text,
                stats=stats,
            ))

    except (KeyError, TypeError, IndexError) as e:
        logger.error(f'解析文本时间线失败: {e}')
        return TextTimelineResult(items=[], cursor=new_cursor, has_more=False)

    return TextTimelineResult(items=items, cursor=new_cursor, has_more=True)


def _extract_tweet_result(entry: dict, content_key: str) -> dict | None:
    """从 entry 中提取 tweet_results.result"""
    try:
        if content_key == 'content':
            return entry['content']['itemContent']['tweet_results']['result']
        else:
            return entry['item']['itemContent']['tweet_results']['result']
    except (KeyError, TypeError):
        return None


def _filter_by_time(items: list[MediaItem], start_time: int, end_time: int) -> list[MediaItem] | None:
    """
    按时间过滤媒体项。
    返回 None 表示已超出时间范围下界（应停止翻页）。
    """
    from utils import time_comparison
    filtered = []
    for item in items:
        result = time_comparison(item.timestamp, start_time, end_time)
        if not result[1]:
            return None  # 超出下界
        if result[0]:
            filtered.append(item)
    return filtered
