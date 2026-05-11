"""Twitter API 客户端，负责发请求和基础错误处理"""

import re
import json
import logging

import httpx

from .endpoints import (
    Endpoint,
    build_user_media_url,
    build_user_tweets_url,
    build_user_tweets_text_url,
    build_user_highlights_url,
    build_user_likes_url,
    build_user_by_screen_name_url,
    build_search_url,
)
from models.user import UserInfo

logger = logging.getLogger(__name__)

BEARER_TOKEN = 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA'


class RateLimitError(Exception):
    pass


class ApiError(Exception):
    pass


def _quote_url(url: str) -> str:
    return url.replace('{', '%7B').replace('}', '%7D')


class TwitterClient:
    def __init__(self, cookie: str, proxy: str | None = None):
        self.proxy = proxy
        self._headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'authorization': BEARER_TOKEN,
            'cookie': cookie,
            'x-csrf-token': re.findall(r'ct0=(.*?);', cookie)[0],
        }
        self.request_count = 0

    def set_referer(self, referer: str):
        self._headers['referer'] = referer

    def fetch_user_info(self, screen_name: str) -> UserInfo:
        """获取用户基本信息"""
        url = build_user_by_screen_name_url(screen_name)
        data = self._request(url)
        result = data['data']['user']['result']
        return UserInfo(
            screen_name=screen_name,
            rest_id=result['rest_id'],
            name=result['legacy']['name'],
            statuses_count=result['legacy']['statuses_count'],
            media_count=result['legacy']['media_count'],
        )

    def fetch_timeline(self, endpoint: Endpoint, user_id: str, cursor: str = '') -> dict:
        """获取时间线原始数据"""
        url_builders = {
            Endpoint.USER_MEDIA: build_user_media_url,
            Endpoint.USER_TWEETS: build_user_tweets_url,
            Endpoint.USER_HIGHLIGHTS: build_user_highlights_url,
            Endpoint.USER_LIKES: build_user_likes_url,
        }
        url = url_builders[endpoint](user_id, cursor)
        return self._request(url)

    def fetch_user_tweets_text(self, user_id: str, cursor: str = '') -> dict:
        """获取用户推文（用于纯文本下载）"""
        url = build_user_tweets_text_url(user_id, cursor)
        return self._request(url)

    def fetch_search(self, query: str, cursor: str = '', count: int = 50, product: str = 'Media') -> dict:
        """搜索推文"""
        url = build_search_url(query, cursor, count, product)
        return self._request(url)

    def _request(self, url: str) -> dict:
        """发送 GET 请求并解析 JSON，网络错误自动重试"""
        for attempt in range(1, 4):
            try:
                response = httpx.get(_quote_url(url), headers=self._headers, proxy=self.proxy, timeout=10)
                self.request_count += 1
                text = response.text
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    if 'Rate limit exceeded' in text:
                        raise RateLimitError('API 调用次数已超限')
                    raise ApiError(f'响应解析失败: {text[:200]}')
            except (RateLimitError, ApiError):
                raise
            except Exception as e:
                if attempt == 3:
                    raise
                logger.warning(f'请求失败 (第{attempt}次): {e}，重试中...')
                import time
                time.sleep(1)
