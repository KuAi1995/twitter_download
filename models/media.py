from dataclasses import dataclass


@dataclass
class TweetStats:
    favorite_count: int = 0
    retweet_count: int = 0
    reply_count: int = 0


@dataclass
class MediaItem:
    """表示一条可下载的媒体"""
    url: str
    timestamp: int  # 毫秒时间戳
    media_type: str  # 'image' | 'video'
    author_name: str = ''
    author_screen_name: str = ''
    tweet_url: str = ''
    tweet_text: str = ''
    is_retweet: bool = False
    stats: TweetStats | None = None


@dataclass
class TextItem:
    """表示一条纯文本推文"""
    timestamp: int
    display_name: str
    screen_name: str
    tweet_url: str
    tweet_text: str
    stats: TweetStats | None = None
