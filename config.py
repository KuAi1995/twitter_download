"""配置加载"""

import json
import os
from dataclasses import dataclass, field


@dataclass
class Config:
    cookie: str = ''
    save_path: str = ''
    user_list: list[str] = field(default_factory=list)
    proxy: str | None = None

    # 模式选择（互斥）
    has_retweet: bool = False
    has_highlights: bool = False
    has_likes: bool = False

    # 下载选项
    has_video: bool = True
    img_format: str = 'png'
    async_down: bool = True
    max_concurrent: int = 8
    log_output: bool = False
    down_log: bool = False
    auto_sync: bool = False

    # 时间范围
    time_range: str = ''

    # Tag 模式
    tag: str = ''
    tag_filter: str = ''
    tag_count: int = 100
    tag_media_latest: bool = False

    # 文本模式
    text_mode: bool = False

    def __post_init__(self):
        if not self.save_path:
            self.save_path = os.getcwd()
        # 互斥逻辑
        if self.has_highlights:
            self.has_retweet = False
        if self.has_likes:
            self.has_retweet = True
            self.has_highlights = False


def load_config(path: str = 'settings.json') -> Config:
    """从 settings.json 加载配置"""
    with open(path, 'r', encoding='utf8') as f:
        data = json.load(f)

    import re
    raw_users = [u.strip() for u in re.split(r'[,，]', data.get('user_lst', '')) if u.strip()]
    # 过滤非法用户名（Twitter screen_name 只含字母数字下划线）
    user_list = [u for u in raw_users if re.match(r'^[A-Za-z0-9_]+$', u)]

    return Config(
        cookie=data.get('cookie', ''),
        save_path=data.get('save_path', ''),
        user_list=user_list,
        proxy=data.get('proxy') or None,
        has_retweet=data.get('has_retweet', False),
        has_highlights=data.get('high_lights', False),
        has_likes=data.get('likes', False),
        has_video=data.get('has_video', True),
        img_format=data.get('img_format', 'png'),
        async_down=data.get('async_down', True),
        max_concurrent=data.get('max_concurrent', 8),
        log_output=data.get('log_output', False),
        down_log=data.get('down_log', False),
        auto_sync=data.get('autoSync', False),
        time_range=data.get('time_range', ''),
        tag=data.get('tag', ''),
        tag_filter=data.get('tag_filter', ''),
        tag_count=data.get('tag_count', 100),
        tag_media_latest=data.get('tag_media_latest', False),
        text_mode=data.get('text_mode', False),
    )
