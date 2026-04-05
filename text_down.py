import httpx
import os
import csv
import json
from datetime import datetime

from user_info import User_info
from utils import quote_url, time2stamp, time_comparison, stamp2time_csv, get_other_info, print_info, build_headers


##########配置区域##########
cookie = 'auth_token=xxxxxxxxxxx; ct0=xxxxxxxxxxx;'
# 填入 cookie (auth_token与ct0字段) //重要:替换掉其中的x即可, 注意不要删掉分号

user_lst = ['jeleechandayo', 'yorukura_anime']
# 填入要下载的用户名(@后面的字符),支持多用户下载,在列表里添加即可

time_range = "2024-04-21:2030-01-01"
# 时间范围限制,格式如 1990-01-01:2030-01-01

has_retweet = False
# 是否包含转推

##########配置区域##########


start_time, end_time = time_range.split(':')
start_time_stamp, end_time_stamp = time2stamp(start_time), time2stamp(end_time)


class text_csv_gen():
    def __init__(self, save_path: str, user_name, screen_name, tweet_range) -> None:
        self.f = open(f'{save_path}/{screen_name}-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}-text.csv', 'w', encoding='utf-8-sig', newline='')
        self.writer = csv.writer(self.f)

        self.writer.writerow([user_name, '@' + screen_name])
        self.writer.writerow(['Tweet Range : ' + tweet_range])
        self.writer.writerow(['Save Path : ' + save_path])
        main_par = ['Display Name', 'User Name', 'Tweet Date', 'Tweet URL', 'Tweet Content', 'Favorite Count',
                    'Retweet Count', 'Reply Count']
        self.writer.writerow(main_par)

    def csv_close(self):
        self.f.close()

    def data_input(self, main_par_info: list) -> None:
        main_par_info[2] = stamp2time_csv(main_par_info[2])
        self.writer.writerow(main_par_info)


class text_down():
    def __init__(self, screen_name):
        self._user_info = User_info(screen_name)

        self._headers = build_headers(cookie)

        if not get_other_info(self._user_info, self._headers):
            return
        print_info(self._user_info)

        self._headers['referer'] = 'https://twitter.com/' + self._user_info.screen_name

        self.folder_path = os.getcwd() + os.sep + screen_name + os.sep

        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)

        self.csv_file = text_csv_gen(self.folder_path, self._user_info.name, self._user_info.screen_name, time_range)

        self.cursor = ''

        self.get_clean_save()

        self.csv_file.csv_close()

    def get_clean_save(self):
        while True:
            url = 'https://twitter.com/i/api/graphql/9zyyd1hebl7oNWIPdA8HRw/UserTweets?variables={"userId":"' + self._user_info.rest_id + '","count":20,"cursor":"' + self.cursor + '","includePromotedContent":true,"withQuickPromoteEligibilityTweetFields":true,"withVoice":true,"withV2Timeline":true}&features={"rweb_tipjar_consumption_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"articles_preview_enabled":true,"tweetypie_unmention_optimization_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"creator_subscriptions_quote_tweet_preview_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"tweet_with_visibility_results_prefer_gql_media_interstitial_enabled":true,"rweb_video_timestamps_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_enhance_cards_enabled":false}&fieldToggles={"withArticlePlainText":false}'

            response = httpx.get(quote_url(url), headers=self._headers).text
            try:
                raw_data = json.loads(response)
            except Exception:
                if 'Rate limit exceeded' in response:
                    print('API次数已超限')
                else:
                    print('获取数据失败')
                print(response)
                return
            raw_tweet_lst = raw_data['data']['user']['result']['timeline_v2']['timeline']['instructions'][-1]['entries']
            if len(raw_tweet_lst) == 2:
                return
            if self.cursor == raw_tweet_lst[-1]['content']['value']:
                return
            self.cursor = raw_tweet_lst[-1]['content']['value']

            for tweet in raw_tweet_lst:
                if 'promoted-tweet' in tweet['entryId']:
                    continue
                if 'tweet' in tweet['entryId']:
                    raw_text = tweet['content']['itemContent']['tweet_results']['result']
                    if 'tweet' in raw_text:
                        raw_text = raw_text['tweet']
                    try:
                        _time_stamp = int(raw_text['edit_control']['editable_until_msecs']) - 3600000
                    except Exception:
                        if 'edit_control_initial' in raw_text['edit_control']:
                            _time_stamp = int(raw_text['edit_control']['edit_control_initial']['editable_until_msecs']) - 3600000
                        else:
                            continue
                    if 'retweeted_status_result' in raw_text['legacy']:
                        if has_retweet:
                            raw_text = raw_text['legacy']['retweeted_status_result']['result']
                            if 'tweet' in raw_text:
                                raw_text = raw_text['tweet']
                            _display_name = raw_text['core']['user_results']['result']['legacy']['name']
                            _screen_name = '@' + raw_text['core']['user_results']['result']['legacy']['screen_name']
                        else:
                            continue
                    else:
                        _display_name = ''
                        _screen_name = ''

                    _results = time_comparison(_time_stamp, start_time_stamp, end_time_stamp)
                    if not _results[1]:
                        return
                    if not _results[0]:
                        continue

                    _Favorite_Count = raw_text['legacy']['favorite_count']
                    _Retweet_Count = raw_text['legacy']['retweet_count']
                    _Reply_Count = raw_text['legacy']['reply_count']
                    _status_id = raw_text['legacy']['conversation_id_str']
                    screen_name = raw_text['core']['user_results']['result']['legacy']['screen_name']
                    _tweet_url = f'https://twitter.com/{screen_name}/status/{_status_id}'
                    _tweet_content = raw_text['legacy']['full_text'].split('https://t.co/')[0]

                    self.csv_file.data_input([_display_name, _screen_name, _time_stamp, _tweet_url, _tweet_content, _Favorite_Count, _Retweet_Count, _Reply_Count])


if __name__ == '__main__':
    for user in user_lst:
        text_down(user)
    print('完成 (๑´ڡ`๑)')
