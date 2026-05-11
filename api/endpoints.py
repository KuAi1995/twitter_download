"""Twitter GraphQL API endpoint URL 构造"""

from enum import Enum
from urllib.parse import quote


# 所有 endpoint 共用的 features 参数
COMMON_FEATURES = (
    '"responsive_web_graphql_exclude_directive_enabled":true,'
    '"verified_phone_label_enabled":false,'
    '"creator_subscriptions_tweet_preview_api_enabled":true,'
    '"responsive_web_graphql_timeline_navigation_enabled":true,'
    '"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,'
    '"tweetypie_unmention_optimization_enabled":true,'
    '"responsive_web_edit_tweet_api_enabled":true,'
    '"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,'
    '"view_counts_everywhere_api_enabled":true,'
    '"longform_notetweets_consumption_enabled":true,'
    '"responsive_web_twitter_article_tweet_consumption_enabled":true,'
    '"tweet_awards_web_tipping_enabled":false,'
    '"freedom_of_speech_not_reach_fetch_enabled":true,'
    '"standardized_nudges_misinfo":true,'
    '"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,'
    '"rweb_video_timestamps_enabled":true,'
    '"longform_notetweets_rich_text_read_enabled":true,'
    '"longform_notetweets_inline_media_enabled":true,'
    '"responsive_web_media_download_video_enabled":false,'
    '"responsive_web_enhance_cards_enabled":false'
)


class Endpoint(Enum):
    USER_MEDIA = 'user_media'
    USER_TWEETS = 'user_tweets'
    USER_HIGHLIGHTS = 'user_highlights'
    USER_LIKES = 'user_likes'
    USER_BY_SCREEN_NAME = 'user_by_screen_name'
    SEARCH = 'search'


def build_user_media_url(user_id: str, cursor: str = '') -> str:
    variables = f'{{"userId":"{user_id}","count":500'
    if cursor:
        variables += f',"cursor":"{cursor}"'
    variables += ',"includePromotedContent":false,"withClientEventToken":false,"withBirdwatchNotes":false,"withVoice":true,"withV2Timeline":true}'
    features = '{' + COMMON_FEATURES + '}'
    return (
        f'https://twitter.com/i/api/graphql/Le6KlbilFmSu-5VltFND-Q/UserMedia'
        f'?variables={variables}'
        f'&features={features}'
    )


def build_user_tweets_url(user_id: str, cursor: str = '') -> str:
    variables = f'{{"userId":"{user_id}","count":20'
    if cursor:
        variables += f',"cursor":"{cursor}"'
    variables += ',"includePromotedContent":false,"withQuickPromoteEligibilityTweetFields":true,"withVoice":true,"withV2Timeline":true}'
    features = '{"rweb_lists_timeline_redesign_enabled":true,' + COMMON_FEATURES + '}'
    field_toggles = '&fieldToggles={"withAuxiliaryUserLabels":false,"withArticleRichContentState":false}'
    return (
        f'https://twitter.com/i/api/graphql/2GIWTr7XwadIixZDtyXd4A/UserTweets'
        f'?variables={variables}'
        f'&features={features}'
        f'{field_toggles}'
    )


def build_user_tweets_text_url(user_id: str, cursor: str = '') -> str:
    """用于纯文本下载的 UserTweets endpoint"""
    variables = f'{{"userId":"{user_id}","count":20,"cursor":"{cursor}","includePromotedContent":true,"withQuickPromoteEligibilityTweetFields":true,"withVoice":true,"withV2Timeline":true}}'
    features = (
        '{"rweb_tipjar_consumption_enabled":true,' + COMMON_FEATURES +
        ',"c9s_tweet_anatomy_moderator_badge_enabled":true,'
        '"articles_preview_enabled":true,'
        '"communities_web_enable_tweet_community_results_fetch":true,'
        '"creator_subscriptions_quote_tweet_preview_enabled":false,'
        '"tweet_with_visibility_results_prefer_gql_media_interstitial_enabled":true}'
        '&fieldToggles={"withArticlePlainText":false}'
    )
    return (
        f'https://twitter.com/i/api/graphql/9zyyd1hebl7oNWIPdA8HRw/UserTweets'
        f'?variables={variables}'
        f'&features={features}'
    )


def build_user_highlights_url(user_id: str, cursor: str = '') -> str:
    variables = f'{{"userId":"{user_id}","count":20'
    if cursor:
        variables += f',"cursor":"{cursor}"'
    variables += ',"includePromotedContent":true,"withVoice":true}'
    features = (
        '{"c9s_tweet_anatomy_moderator_badge_enabled":true,' + COMMON_FEATURES + '}'
    )
    return (
        f'https://twitter.com/i/api/graphql/w9-i9VNm_92GYFaiyGT1NA/UserHighlightsTweets'
        f'?variables={variables}'
        f'&features={features}'
    )


def build_user_likes_url(user_id: str, cursor: str = '') -> str:
    variables = f'{{"userId":"{user_id}","count":200'
    if cursor:
        variables += f',"cursor":"{cursor}"'
    variables += ',"includePromotedContent":false,"withClientEventToken":false,"withBirdwatchNotes":false,"withVoice":true,"withV2Timeline":true}'
    features = '{' + COMMON_FEATURES + '}'
    return (
        f'https://twitter.com/i/api/graphql/-fbTO1rKPa3nO6-XIRgEFQ/Likes'
        f'?variables={variables}'
        f'&features={features}'
    )


def build_user_by_screen_name_url(screen_name: str) -> str:
    variables = f'{{"screen_name":"{screen_name}","withSafetyModeUserFields":false}}'
    features = (
        '{"hidden_profile_likes_enabled":false,'
        '"hidden_profile_subscriptions_enabled":false,' + COMMON_FEATURES +
        ',"subscriptions_verification_info_verified_since_enabled":true,'
        '"highlights_tweets_tab_ui_enabled":true}'
    )
    return (
        f'https://twitter.com/i/api/graphql/xc8f1g7BYqr6VTzTbvNlGw/UserByScreenName'
        f'?variables={variables}'
        f'&features={features}'
        f'&fieldToggles={{"withAuxiliaryUserLabels":false}}'
    )


def build_search_url(query: str, cursor: str = '', count: int = 50, product: str = 'Media') -> str:
    variables = f'{{"rawQuery":"{quote(query)}","count":{count},"cursor":"{cursor}","querySource":"typed_query","product":"{product}"}}'
    features = (
        '{"rweb_tipjar_consumption_enabled":true,' + COMMON_FEATURES +
        ',"c9s_tweet_anatomy_moderator_badge_enabled":true,'
        '"articles_preview_enabled":true,'
        '"communities_web_enable_tweet_community_results_fetch":true,'
        '"creator_subscriptions_quote_tweet_preview_enabled":false,'
        '"tweet_with_visibility_results_prefer_gql_media_interstitial_enabled":true}'
    )
    return (
        f'https://twitter.com/i/api/graphql/tUJgNbJvuiieOXvq7OmHwA/SearchTimeline'
        f'?variables={variables}'
        f'&features={features}'
    )
