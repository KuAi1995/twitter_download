"""从单条推文 JSON 中提取媒体信息"""

import logging

from models.media import MediaItem, TweetStats

logger = logging.getLogger(__name__)


def _get_highest_video_quality(variants: list) -> str | None:
    """从 video_info.variants 中选最高码率"""
    max_bitrate = -1
    best_url = None
    for v in variants:
        bitrate = v.get('bitrate', -1)
        if bitrate > max_bitrate:
            max_bitrate = bitrate
            best_url = v['url']
    return best_url


def _extract_timestamp(tweet_result: dict) -> int | None:
    """从 tweet_result 中提取时间戳（毫秒）"""
    try:
        edit_control = tweet_result.get('edit_control', {})
        if 'editable_until_msecs' in edit_control:
            return int(edit_control['editable_until_msecs']) - 3600000
        if 'edit_control_initial' in edit_control:
            return int(edit_control['edit_control_initial']['editable_until_msecs']) - 3600000
    except (KeyError, ValueError, TypeError):
        pass
    return None


def _unwrap_tweet(tweet_result: dict) -> dict:
    """处理 tweet_result 可能嵌套 'tweet' 键的情况"""
    if 'tweet' in tweet_result:
        return tweet_result['tweet']
    return tweet_result


def parse_tweet_media(tweet_result: dict, has_video: bool = True) -> list[MediaItem]:
    """从单条推文结果中提取所有媒体项"""
    items = []
    tweet = _unwrap_tweet(tweet_result)
    legacy = tweet.get('legacy', {})
    timestamp = _extract_timestamp(tweet)
    if timestamp is None:
        return items

    stats = TweetStats(
        favorite_count=legacy.get('favorite_count', 0),
        retweet_count=legacy.get('retweet_count', 0),
        reply_count=legacy.get('reply_count', 0),
    )

    # 获取作者信息
    try:
        core = tweet['core']['user_results']['result']['legacy']
        author_name = core['name']
        author_screen_name = core['screen_name']
    except (KeyError, TypeError):
        author_name = ''
        author_screen_name = ''

    tweet_text = legacy.get('full_text', '')

    # 检查是否是转推
    if 'retweeted_status_result' in legacy:
        rt_result = legacy['retweeted_status_result']['result']
        rt_tweet = _unwrap_tweet(rt_result)
        rt_legacy = rt_tweet.get('legacy', {})
        if 'extended_entities' not in rt_legacy:
            return items
        try:
            rt_core = rt_tweet['core']['user_results']['result']['legacy']
            rt_author_name = rt_core['name']
            rt_author_screen_name = rt_core['screen_name']
        except (KeyError, TypeError):
            rt_author_name = ''
            rt_author_screen_name = ''

        items.extend(_extract_media_from_entities(
            rt_legacy['extended_entities']['media'],
            timestamp=timestamp,
            author_name=rt_author_name,
            author_screen_name=rt_author_screen_name,
            tweet_text=rt_legacy.get('full_text', ''),
            stats=stats,
            is_retweet=True,
            has_video=has_video,
        ))
        return items

    # 原创推文
    if 'extended_entities' in legacy:
        items.extend(_extract_media_from_entities(
            legacy['extended_entities']['media'],
            timestamp=timestamp,
            author_name=author_name,
            author_screen_name=author_screen_name,
            tweet_text=tweet_text,
            stats=stats,
            is_retweet=False,
            has_video=has_video,
        ))

    return items


def _extract_media_from_entities(
    media_list: list,
    timestamp: int,
    author_name: str,
    author_screen_name: str,
    tweet_text: str,
    stats: TweetStats,
    is_retweet: bool,
    has_video: bool,
) -> list[MediaItem]:
    """从 extended_entities.media 列表中提取 MediaItem"""
    items = []
    for media in media_list:
        if 'video_info' in media:
            if not has_video:
                continue
            url = _get_highest_video_quality(media['video_info']['variants'])
            if not url:
                continue
            media_type = 'video'
        else:
            url = media.get('media_url_https', '')
            media_type = 'image'

        items.append(MediaItem(
            url=url,
            timestamp=timestamp,
            media_type=media_type,
            author_name=author_name,
            author_screen_name=author_screen_name,
            tweet_url=media.get('expanded_url', ''),
            tweet_text=tweet_text,
            is_retweet=is_retweet,
            stats=stats,
        ))
    return items
