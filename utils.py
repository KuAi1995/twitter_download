import re
import time
from datetime import datetime


def quote_url(url):
    return url.replace('{', '%7B').replace('}', '%7D')


def del_special_char(string):
    string = re.sub(r'[^\u4e00-\u9fa5\u0030-\u0039\u0041-\u005a\u0061-\u007a\u3040-\u31FF\.]', '', string)
    return string


def del_special_char_with_hash(string):
    string = re.sub(r'[^#\u4e00-\u9fa5\u0030-\u0039\u0041-\u005a\u0061-\u007a\u3040-\u31FF\.]', '', string)
    return string


def stamp2time(msecs_stamp: int) -> str:
    timeArray = time.localtime(msecs_stamp / 1000)
    return time.strftime("%Y-%m-%d %H-%M", timeArray)


def stamp2time_csv(msecs_stamp: int) -> str:
    timeArray = time.localtime(msecs_stamp / 1000)
    return time.strftime("%Y-%m-%d %H:%M", timeArray)


def time2stamp(timestr: str) -> int:
    datetime_obj = datetime.strptime(timestr, "%Y-%m-%d")
    return int(time.mktime(datetime_obj.timetuple()) * 1000.0 + datetime_obj.microsecond / 1000.0)


def time_comparison(now, start, end):
    start_label = True
    start_down = False
    if now >= start and now <= end:
        start_down = True
    elif now < start:
        start_label = False
    return [start_down, start_label]


def get_heighest_video_quality(variants) -> str:
    if len(variants) == 1:
        return variants[0]['url']
    max_bitrate = 0
    heighest_url = None
    for i in variants:
        if 'bitrate' in i:
            if int(i['bitrate']) > max_bitrate:
                max_bitrate = int(i['bitrate'])
                heighest_url = i['url']
    return heighest_url


def get_other_info(_user_info, _headers, proxies=None):
    import httpx
    import json
    url = 'https://twitter.com/i/api/graphql/xc8f1g7BYqr6VTzTbvNlGw/UserByScreenName?variables={"screen_name":"' + _user_info.screen_name + '","withSafetyModeUserFields":false}&features={"hidden_profile_likes_enabled":false,"hidden_profile_subscriptions_enabled":false,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"subscriptions_verification_info_verified_since_enabled":true,"highlights_tweets_tab_ui_enabled":true,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"responsive_web_graphql_timeline_navigation_enabled":true}&fieldToggles={"withAuxiliaryUserLabels":false}'
    try:
        response = httpx.get(quote_url(url), headers=_headers, proxy=proxies).text
        raw_data = json.loads(response)
        _user_info.rest_id = raw_data['data']['user']['result']['rest_id']
        _user_info.name = raw_data['data']['user']['result']['legacy']['name']
        _user_info.statuses_count = raw_data['data']['user']['result']['legacy']['statuses_count']
        _user_info.media_count = raw_data['data']['user']['result']['legacy']['media_count']
    except Exception:
        print('获取信息失败')
        print(response)
        return False
    return True


def print_info(_user_info):
    print(
        f'''
        <======基本信息=====>
        昵称:{_user_info.name}
        用户名:{_user_info.screen_name}
        数字ID:{_user_info.rest_id}
        总推数(含转推):{_user_info.statuses_count}
        含图片/视频/音频推数(不含转推):{_user_info.media_count}
        <==================>
        开始爬取...
        '''
    )


def build_headers(cookie):
    _headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
    }
    _headers['cookie'] = cookie
    re_token = 'ct0=(.*?);'
    _headers['x-csrf-token'] = re.findall(re_token, cookie)[0]
    return _headers
