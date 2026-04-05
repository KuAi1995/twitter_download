import re
import time
import httpx
import asyncio
import os
import json
import logging
from user_info import User_info
from csv_gen import csv_gen
from cache_gen import cache_gen
from utils import quote_url, stamp2time, time2stamp, time_comparison, get_heighest_video_quality, build_headers, print_info, get_other_info
from tenacity import retry, stop_after_attempt, wait_fixed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TwitterDownloader:
    def __init__(self, settings):
        self.settings = settings
        self.max_concurrent_requests = 8

        self.log_output = settings.get('log_output', False)
        self.has_retweet = settings.get('has_retweet', False)
        self.has_highlights = settings.get('high_lights', False)
        self.has_likes = settings.get('likes', False)
        self.has_video = settings.get('has_video', False)
        self.down_log = settings.get('down_log', False)
        self.async_down = settings.get('async_down', True)
        self.autoSync = settings.get('autoSync', False)
        self.img_format = settings.get('img_format', 'png')
        self.proxies = settings.get('proxy') or None

        if not settings['save_path']:
            settings['save_path'] = os.getcwd()
        self.save_path = settings['save_path'] + os.sep

        self.start_time_stamp = 655028357000   #1990-10-04
        self.end_time_stamp = 2548484357000    #2050-10-04

        if self.has_highlights:
            self.has_retweet = False
        if settings.get('time_range'):
            start_time, end_time = settings['time_range'].split(':')
            self.start_time_stamp = time2stamp(start_time)
            self.end_time_stamp = time2stamp(end_time)
        if self.has_likes:
            self.has_retweet = True
            self.has_highlights = False
            self.start_time_stamp = 655028357000
            self.end_time_stamp = 2548484357000

        self.backup_stamp = self.start_time_stamp
        self._headers = build_headers(settings['cookie'])

        self.request_count = 0
        self.down_count = 0

        # 每个用户重置的状态
        self.start_label = True
        self.first_page = True
        self.csv_file = None
        self.cache_data = None

    @retry(stop=stop_after_attempt(10), wait=wait_fixed(2))
    def _get_other_info(self, _user_info):
        result = get_other_info(_user_info, self._headers, self.proxies)
        self.request_count += 1
        return result

    @retry(stop=stop_after_attempt(10), wait=wait_fixed(2))
    def get_download_url(self, _user_info):

        def get_url_from_content(content):
            _photo_lst = []
            if self.has_retweet or self.has_highlights:
                x_label = 'content'
            else:
                x_label = 'item'
            for i in content:
                try:
                    if 'promoted-tweet' in i['entryId']:
                        continue
                    if 'tweet' in i['entryId']:
                        if 'tweet' in i[x_label]['itemContent']['tweet_results']['result']:
                            a = i[x_label]['itemContent']['tweet_results']['result']['tweet']['legacy']
                            frr = [a['favorite_count'], a['retweet_count'], a['reply_count']]
                            tweet_msecs = int(i[x_label]['itemContent']['tweet_results']['result']['tweet']['edit_control']['editable_until_msecs']) - 3600000
                        else:
                            a = i[x_label]['itemContent']['tweet_results']['result']['legacy']
                            frr = [a['favorite_count'], a['retweet_count'], a['reply_count']]
                            tweet_msecs = int(i[x_label]['itemContent']['tweet_results']['result']['edit_control']['editable_until_msecs']) - 3600000
                        timestr = stamp2time(tweet_msecs)

                        _result = time_comparison(tweet_msecs, self.start_time_stamp, self.end_time_stamp)
                        if _result[0]:
                            if 'extended_entities' in a and 'retweeted_status_result' not in a:
                                _photo_lst += [(get_heighest_video_quality(_media['video_info']['variants']), f'{timestr}-vid', [tweet_msecs, _user_info.name, f'@{_user_info.screen_name}', _media['expanded_url'], 'Video', get_heighest_video_quality(_media['video_info']['variants']), '', a['full_text']] + frr) if 'video_info' in _media and self.has_video else (_media['media_url_https'], f'{timestr}-img', [tweet_msecs, _user_info.name, f'@{_user_info.screen_name}', _media['expanded_url'], 'Image', _media['media_url_https'], '', a['full_text']] + frr) for _media in a['extended_entities']['media']]
                            elif 'retweeted_status_result' in a and 'extended_entities' in a['retweeted_status_result']['result']['legacy']:
                                _photo_lst += [(get_heighest_video_quality(_media['video_info']['variants']), f'{timestr}-vid-retweet', [tweet_msecs, a['retweeted_status_result']['result']['core']['user_results']['result']['legacy']['name'], f"@{a['retweeted_status_result']['result']['core']['user_results']['result']['legacy']['screen_name']}", _media['expanded_url'], 'Video', get_heighest_video_quality(_media['video_info']['variants']), '', a['retweeted_status_result']['result']['legacy']['full_text']] + frr) if 'video_info' in _media and self.has_video else (_media['media_url_https'], f'{timestr}-img-retweet', [tweet_msecs, a['retweeted_status_result']['result']['core']['user_results']['result']['legacy']['name'], f"@{a['retweeted_status_result']['result']['core']['user_results']['result']['legacy']['screen_name']}", _media['expanded_url'], 'Image', _media['media_url_https'], '', a['retweeted_status_result']['result']['legacy']['full_text']] + frr) for _media in a['retweeted_status_result']['result']['legacy']['extended_entities']['media']]
                        elif not _result[1]:
                            self.start_label = False
                            break

                    elif 'profile-conversation' in i['entryId']:
                        if 'tweet' in i[x_label]['items'][0]['item']['itemContent']['tweet_results']['result']:
                            a = i[x_label]['items'][0]['item']['itemContent']['tweet_results']['result']['tweet']['legacy']
                            frr = [a['favorite_count'], a['retweet_count'], a['reply_count']]
                            tweet_msecs = int(i[x_label]['items'][0]['item']['itemContent']['tweet_results']['result']['tweet']['edit_control']['editable_until_msecs']) - 3600000
                        else:
                            a = i[x_label]['items'][0]['item']['itemContent']['tweet_results']['result']['legacy']
                            frr = [a['favorite_count'], a['retweet_count'], a['reply_count']]
                            tweet_msecs = int(i[x_label]['items'][0]['item']['itemContent']['tweet_results']['result']['edit_control']['editable_until_msecs']) - 3600000
                        timestr = stamp2time(tweet_msecs)

                        _result = time_comparison(tweet_msecs, self.start_time_stamp, self.end_time_stamp)
                        if _result[0]:
                            if 'extended_entities' in a:
                                _photo_lst += [(get_heighest_video_quality(_media['video_info']['variants']), f'{timestr}-vid', [tweet_msecs, _user_info.name, f'@{_user_info.screen_name}', _media['expanded_url'], 'Video', get_heighest_video_quality(_media['video_info']['variants']), '', a['full_text']] + frr) if 'video_info' in _media and self.has_video else (_media['media_url_https'], f'{timestr}-img', [tweet_msecs, _user_info.name, f'@{_user_info.screen_name}', _media['expanded_url'], 'Image', _media['media_url_https'], '', a['full_text']] + frr) for _media in a['extended_entities']['media']]
                        elif not _result[1]:
                            self.start_label = False
                            break

                except Exception as e:
                    continue
                if 'cursor-bottom' in i['entryId']:
                    _user_info.cursor = i['content']['value']

            return _photo_lst

        logger.info(f'已下载图片/视频:{_user_info.count}')
        if self.has_highlights:
            url_top = 'https://twitter.com/i/api/graphql/w9-i9VNm_92GYFaiyGT1NA/UserHighlightsTweets?variables={"userId":"' + _user_info.rest_id + '","count":20,'
            url_bottom = '"includePromotedContent":true,"withVoice":true}&features={"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"c9s_tweet_anatomy_moderator_badge_enabled":true,"tweetypie_unmention_optimization_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":false,"tweet_awards_web_tipping_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"rweb_video_timestamps_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_media_download_video_enabled":false,"responsive_web_enhance_cards_enabled":false}'
        elif self.has_likes:
            url_top = 'https://twitter.com/i/api/graphql/-fbTO1rKPa3nO6-XIRgEFQ/Likes?variables={"userId":"' + _user_info.rest_id + '","count":200,'
            url_bottom = '"includePromotedContent":false,"withClientEventToken":false,"withBirdwatchNotes":false,"withVoice":true,"withV2Timeline":true}&features={"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"c9s_tweet_anatomy_moderator_badge_enabled":true,"tweetypie_unmention_optimization_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":false,"tweet_awards_web_tipping_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"rweb_video_timestamps_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_media_download_video_enabled":false,"responsive_web_enhance_cards_enabled":false}'
        elif self.has_retweet:
            url_top = 'https://twitter.com/i/api/graphql/2GIWTr7XwadIixZDtyXd4A/UserTweets?variables={"userId":"' + _user_info.rest_id + '","count":20,'
            url_bottom = '"includePromotedContent":false,"withQuickPromoteEligibilityTweetFields":true,"withVoice":true,"withV2Timeline":true}&features={"rweb_lists_timeline_redesign_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"tweetypie_unmention_optimization_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":false,"tweet_awards_web_tipping_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_media_download_video_enabled":false,"responsive_web_enhance_cards_enabled":false}&fieldToggles={"withAuxiliaryUserLabels":false,"withArticleRichContentState":false}'
        else:
            url_top = 'https://twitter.com/i/api/graphql/Le6KlbilFmSu-5VltFND-Q/UserMedia?variables={"userId":"' + _user_info.rest_id + '","count":500,'
            url_bottom = '"includePromotedContent":false,"withClientEventToken":false,"withBirdwatchNotes":false,"withVoice":true,"withV2Timeline":true}&features={"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"tweetypie_unmention_optimization_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":false,"tweet_awards_web_tipping_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_media_download_video_enabled":false,"responsive_web_enhance_cards_enabled":false}'

        if _user_info.cursor:
            url = url_top + '"cursor":"' + _user_info.cursor + '",' + url_bottom
        else:
            url = url_top + url_bottom
        try:
            response = httpx.get(quote_url(url), headers=self._headers, proxy=self.proxies).text
            self.request_count += 1
            try:
                raw_data = json.loads(response)
            except json.JSONDecodeError:
                if 'Rate limit exceeded' in response:
                    logger.error('API次数已超限')
                else:
                    logger.error('获取数据失败')
                logger.debug(response)
                return
            if self.has_highlights:
                raw_data = raw_data['data']['user']['result']['timeline']['timeline']['instructions'][-1]['entries']
            elif self.has_retweet:
                raw_data = raw_data['data']['user']['result']['timeline_v2']['timeline']['instructions'][-1]['entries']
            else:
                raw_data = raw_data['data']['user']['result']['timeline_v2']['timeline']['instructions']
            if (self.has_retweet or self.has_highlights) and 'cursor-top' in raw_data[0]['entryId']:
                return False

            if not self.has_retweet and not self.has_highlights:
                for i in raw_data[-1]['entries']:
                    if 'bottom' in i['entryId']:
                        _user_info.cursor = i['content']['value']

            if self.start_label:
                if not self.has_retweet and not self.has_highlights:
                    if self.first_page:
                        raw_data = raw_data[-1]['entries'][0]['content']['items']
                        self.first_page = False
                    else:
                        if 'moduleItems' not in raw_data[0]:
                            return False
                        else:
                            raw_data = raw_data[0]['moduleItems']
                photo_lst = get_url_from_content(raw_data)
            else:
                return False

            if not photo_lst:
                photo_lst.append(True)
        except (KeyError, TypeError) as e:
            logger.error(f'获取推文信息错误: {e}')
            logger.debug(response)
            return False
        except Exception as e:
            logger.error(f'获取推文信息未知错误: {e}')
            return False
        return photo_lst

    def download_control(self, _user_info):
        downloader = self

        async def _main():
            async def down_save(url, prefix, csv_info, order: int):
                if '.mp4' in url:
                    _file_name = f'{_user_info.save_path + os.sep}{prefix}_{_user_info.count + order}.mp4'
                else:
                    try:
                        _file_name = f'{_user_info.save_path + os.sep}{prefix}_{_user_info.count + order}.{downloader.img_format}'
                        url += f'?format={downloader.img_format}&name=4096x4096'
                    except Exception as e:
                        logger.warning(f'文件名生成失败: {url}')
                        return False
                count = 0
                while count < 10:
                    try:
                        async with semaphore:
                            async with httpx.AsyncClient(proxy=downloader.proxies) as client:
                                response = await client.get(quote_url(url), timeout=(3.05, 16))
                                downloader.down_count += 1
                        with open(_file_name, 'wb') as f:
                            f.write(response.content)

                        if not downloader.has_likes:
                            csv_info[-5] = os.path.split(_file_name)[1]
                            downloader.csv_file.data_input(csv_info)

                        if downloader.log_output:
                            logger.info(f'{_file_name}=====>下载完成')

                        break
                    except Exception as e:
                        count += 1
                        logger.warning(f'{_file_name}=====>第{count}次下载失败,正在重试: {e}')
                else:
                    logger.error(f'{_file_name}=====>超过最大重试次数,已跳过')

            while True:
                photo_lst = downloader.get_download_url(_user_info)
                if not photo_lst:
                    break
                elif photo_lst[0] == True:
                    continue
                if downloader.async_down:
                    semaphore = asyncio.Semaphore(downloader.max_concurrent_requests)
                    if downloader.down_log:
                        await asyncio.gather(*[asyncio.create_task(down_save(url[0], url[1], url[2], order)) for order, url in enumerate(photo_lst) if downloader.cache_data.is_present(url[0])])
                    else:
                        await asyncio.gather(*[asyncio.create_task(down_save(url[0], url[1], url[2], order)) for order, url in enumerate(photo_lst)])
                else:
                    for order, url in enumerate(photo_lst):
                        await down_save(url[0], url[1], url[2], order)
                _user_info.count += len(photo_lst)

        asyncio.run(_main())

    def run_user(self, _user_info):
        # 重置每个用户的状态
        self.start_label = True
        self.first_page = True
        self.start_time_stamp = self.backup_stamp

        self._headers['referer'] = 'https://twitter.com/' + _user_info.screen_name
        if not self._get_other_info(_user_info):
            return False
        print_info(_user_info)
        _path = self.save_path + _user_info.name + " (@" + _user_info.screen_name + ")"
        _is_create_folder = True
        if os.path.exists(_path):
            _user_info.save_path = _path
        else:
            save_dir = self.save_path
            if os.path.exists(save_dir):
                for item in os.listdir(save_dir):
                    item_path = os.path.join(save_dir, item)
                    if os.path.isdir(item_path) and _user_info.screen_name in item:
                        os.rename(item_path, _path)
                        _user_info.save_path = _path
                        _is_create_folder = False
                        break
                if _is_create_folder:
                    os.makedirs(_path)
                    _user_info.save_path = _path

        if not self.has_likes:
            self.csv_file = csv_gen(_user_info.save_path, _user_info.name, _user_info.screen_name, self.settings['time_range'])

        if self.down_log:
            self.cache_data = cache_gen(_user_info.save_path)

        if self.autoSync:
            files = sorted(os.listdir(_user_info.save_path))
            if len(files) > 0:
                re_rule = r'\d{4}-\d{2}-\d{2}'
                for i in files[::-1]:
                    if "-img_" in i or "-vid_" in i:
                        self.start_time_stamp = time2stamp(re.findall(re_rule, i)[0])
                        break
                    else:
                        self.start_time_stamp = self.backup_stamp
            else:
                self.start_time_stamp = self.backup_stamp

        self.download_control(_user_info)

        if not self.has_likes:
            self.csv_file.csv_close()
        if self.down_log:
            self.cache_data.save()
            self.cache_data = None
        logger.info(f'{_user_info.name}下载完成')

    def run(self):
        _start = time.time()
        for i in self.settings['user_lst'].split(','):
            self.run_user(User_info(i))
        logger.info(f'共耗时:{time.time() - _start:.1f}秒 | 共调用{self.request_count}次API | 共下载{self.down_count}份图片/视频')


if __name__ == '__main__':
    with open('settings.json', 'r', encoding='utf8') as f:
        settings = json.load(f)
    downloader = TwitterDownloader(settings)
    downloader.run()
