import json
import time
from builtins import print
from copy import deepcopy
from enum import Enum

import requests
from requests import RequestException


# CONSTANTS
class Mode(Enum):
    SOLO = "_p2"
    DUO = "_p10"
    SQUAD = "_p9"
    ALL = 'all'


class PlayablePlatform(Enum):
    PC = "pc"
    XBOX1 = "xb1"
    PS4 = "ps4"


class Language(Enum):
    ENGLISH = "en"
    GERMAN = "de"
    SPANISH = "es"
    CHINESE = "zh"
    FRENCH = "fr"
    ITALIAN = "it"
    JAPANESE = "ja"


class NewsType(Enum):
    BATTLEROYALE = "battleroyalenews"
    SAVETHEWORLD = "savetheworldnews"


class TimeWindow(Enum):
    CURRENT_SEASON = 'monthly'
    ALLTIME = 'alltime'


# Exceptions
class InvalidPlatformException(Exception):
    def __init__(self):
        super().__init__('The Platform is invalid.')


class InvalidModeException(Exception):
    def __init__(self):
        super().__init__('The Mode is invalid.')


class SiteNotAvailableException(Exception):
    def __init__(self):
        super().__init__('The Fortnite server are down or the bot lost the connection.')


class UserNotFoundException(Exception):
    def __init__(self, username):
        super().__init__('The User {} was not found.'.format(username))


class StatNameCollectionNotFoundException(Exception):
    def __init__(self):
        super().__init__('Stat name list cannot be null or empty.')


class FortniteClient:
    # base64 encoded string of two MD5 hashes delimited by a colon. The two hashes are the client_id and
    # client_secret OAuth2 fields.
    EPIC_LAUNCHER_AUTHORIZATION = \
        'MzRhMDJjZjhmNDQxNGUyOWIxNTkyMTg3NmRhMzZmOWE6ZGFhZmJjY2M3Mzc3NDUwMzlkZmZlNTNkOTRmYzc2Y2Y='

    # Same as EPIC_LAUNCHER_AUTHORIZATION
    FORTNITE_AUTHORIZATION = 'ZWM2ODRiOGM2ODdmNDc5ZmFkZWEzY2IyYWQ4M2Y1YzY6ZTFmMzFjMjExZjI4NDEzMTg2MjYyZDM3YTEzZmM4NGQ='

    # Epic API Endpoints
    EPIC_OAUTH_TOKEN_ENDPOINT = 'https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/token'
    EPIC_OAUTH_TOKEN_KILL_ENDPOINT = \
        'https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/sessions/kill/'
    EPIC_OAUTH_EXCHANGE_ENDPOINT = 'https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/exchange'
    EPIC_OAUTH_VERIFY_ENDPOINT = 'https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/verify'
    EPIC_FRIENDS_ENDPOINT = 'https://friends-public-service-prod06.ol.epicgames.com/friends/api/public/friends/'

    # Fortnite API Endpoints
    FORTNITE_API = 'https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/'
    FORTNITE_PERSONA_API = 'https://persona-public-service-prod06.ol.epicgames.com/persona/api/'
    FORTNITE_ACCOUNT_API = 'https://account-public-service-prod03.ol.epicgames.com/account/api/'
    FORTNITE_NEWS_API = 'https://fortnitecontent-website-prod07.ol.epicgames.com/content/api/'
    FORTNITE_STATUS_API = 'https://lightswitch-public-service-prod06.ol.epicgames.com/lightswitch/api/'

    @staticmethod
    def send_unreal_client_get_request(endpoint, authorization=EPIC_LAUNCHER_AUTHORIZATION, oauth=False):
        r"""
        Sends a GET request as the Unreal Engine Client.

        :param endpoint:        API Endpoint to request
        :param authorization:   Authorization header
        :param oauth:           Is :param authorization: an OAuth2 token
        :return:                Decoded JSON response body
        """
        try:
            headers = {
                'User-Agent': 'game=UELauncher, engine=UE4, build=7.10.1-4107608+++Portal+Release-Live',
                'Authorization': oauth and 'bearer ' + authorization or 'basic ' + authorization
            }
            return json.loads(requests.get(endpoint, None, headers=headers).text)
        except RequestException as ex:
            raise ex  # Throw exception back up to caller

    @staticmethod
    def send_unreal_client_post_request(endpoint, params=None, authorization=EPIC_LAUNCHER_AUTHORIZATION,
                                        oauth=False):
        r"""
        Sends a POST request as the Unreal Engine Client.

        :param endpoint:        API Endpoint to request
        :param params:          Request parameters, using the name as the array key and value as the array value
        :param authorization:   Authorization header
        :param oauth:           Is :param authorization: an OAuth2 token
        :return:                Decoded JSON response body
        """

        headers = {
            'UserAgent': 'game=UELauncher, engine=UE4, build=7.10.1-4107608+++Portal+Release-Live',
            'Authorization': oauth and 'bearer ' + authorization or 'basic ' + authorization
        }
        try:
            return json.loads(requests.post(endpoint, params, None, headers=headers).text)
        except RequestException as ex:
            raise ex  # Throw exception back up to caller

    @staticmethod
    def send_unreal_client_delete_request(endpoint, access_token):
        r"""
        Sends a DELETE request as the Unreal Engine Client.

        :param endpoint: API    Endpoint to request
        :param access_token:    OAuth2 access token
        """
        headers = {
            'UserAgent': 'game=UELauncher, engine=UE4, build=7.10.1-4107608+++Portal+Release-Live',
            'Authorization': 'bearer ' + access_token
        }
        requests.delete(endpoint, headers=headers)

    @staticmethod
    def send_fortnite_get_request(endpoint, access_token, extra_headers=None):
        r"""
        Sends a GET request as the Fortnite client.

        :param endpoint:        API endpoint to request
        :param access_token:    OAuth2 access token
        :param extra_headers:   (optional)
        :return:                Decoded JSON response body
        """
        if extra_headers is None:
            extra_headers = {}
        headers = {
            'UserAgent': 'game=Fortnite, engine=UE4, build=++Fortnite+Release-2.5-CL-3889387, netver=3886413',
            'Authorization': 'bearer ' + access_token
        }
        headers = {**headers, **extra_headers}
        try:
            raw = requests.get(endpoint, None, headers=headers).text
            print(raw)
            return json.loads(raw)
        except RequestException as ex:
            raise ex  # Throw exception back up to calle

    @staticmethod
    def send_fortnite_post_request(endpoint, access_token, params=None):
        r"""
        Sends a POST request as the Fortnite client.

        :param endpoint:        API endpoint to request
        :param access_token:    OAuth2 access token
        :param params:          Request parameters, using the name as the array key and value as the array value
        :return:                Decoded JSON response body
        """
        headers = {
            'User-Agent': 'game=Fortnite, engine=UE4, build=++Fortnite+Release-2.5-CL-3889387, netver=3886413',
            'Authorization': 'bearer ' + access_token
        }
        try:
            request = requests.post(endpoint, None, params, headers=headers).text
            return json.loads(request)
        except RequestException as ex:
            raise ex  # Throw exception back up to caller


class Auth:

    def __init__(self, email, password):
        self._access_token = None
        self._refresh_token = None
        self._account_id = None
        self._expires_in = None
        self._login(email, password)

    def _login(self, email, password):
        r"""
        Login using Unreal Engine credentials to access Fortnite API.

        :param email:       The account email
        :param password:    The account password
        :return:
        """
        # First, we need to get a token for the Unreal Engine client
        params = {
            'grant_type': 'password',
            'username': email,
            'password': password,
            'includePerms': False,  # We don't need these here
            'token_type': 'eg1'
        }
        data = FortniteClient.send_unreal_client_post_request(FortniteClient.EPIC_OAUTH_TOKEN_ENDPOINT,
                                                              params)
        print('DEBUG: ' + str(data))
        if not data.__contains__('access_token'):
            raise Exception(data['errorMessage'])

        # Now that we've got our Unreal Client launcher token, let's get an exchange token for Fortnite
        data = FortniteClient.send_unreal_client_get_request(FortniteClient.EPIC_OAUTH_EXCHANGE_ENDPOINT,
                                                             data['access_token'],
                                                             True)
        print('DEBUG: ' + str(data))
        if not data.__contains__('code'):
            raise Exception(data['errorMessage'])

        # Should be good. Let's get our tokens for the Fortnite API
        params = {
            'grant_type': 'exchange_code',
            'exchange_code': data['code'],
            'includePerms': False,  # We don't need these here
            'token_type': 'eg1'
        }
        data = FortniteClient.send_unreal_client_post_request(FortniteClient.EPIC_OAUTH_TOKEN_ENDPOINT,
                                                              params,
                                                              FortniteClient.FORTNITE_AUTHORIZATION)
        print('DEBUG: ' + str(data))
        if not data.__contains__('access_token'):
            raise Exception(data['errorMessage'])

        self._access_token = data['access_token']
        self._refresh_token = data['refresh_token']
        self._account_id = data['account_id']
        self._expires_at = time.time() + data['expires_in']
        print('DEBUG: expires at: ' + str(self.expires_at()))
        print('DEBUG: current: ' + str(time.time()))

    def refresh(self, refresh_token):
        print('DEBUG: Refresh Token...')
        params = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'includePerms': "false",  # We don't need these here
            'token_type': 'eg1'
        }
        data = FortniteClient.send_unreal_client_post_request(FortniteClient.EPIC_OAUTH_TOKEN_ENDPOINT,
                                                              params,
                                                              FortniteClient.FORTNITE_AUTHORIZATION)
        if not data.__contains__('access_token'):
            raise Exception(data['errorMessage'])

        self._access_token = data['access_token']
        self._refresh_token = data['refresh_token']
        self._account_id = data['account_id']
        self._expires_in = data['expires_in']

    def token_expired(self):
        return time.time() >= self._expires_at

    def refresh_token(self):
        r"""
        Returns current refresh token.

        :return:    OAuth2 refresh token
        """

        return self._refresh_token

    def expires_at(self):
        r"""
        Returns the time when the OAuth2 access token expires.

        :return:    Time when OAuth2 access token expires (in seconds)
        """

        return self._expires_at

    def access_token(self):
        r"""
        Returns current access token.

        :return:    OAuth2 access token
        """
        return self._access_token


class Account:

    def __init__(self, access_token):
        self._access_token = access_token

    def get_display_name_from_id(self, user_id):
        try:
            data = FortniteClient.send_fortnite_get_request(FortniteClient.FORTNITE_ACCOUNT_API +
                                                            'public/account?accountId=' + user_id,
                                                            self._access_token)
            return data
        except RequestException as ex:
            if ex.response is 404:
                raise SiteNotAvailableException()
            raise ex

    def get_display_names_from_ids(self, ids):
        try:
            url = FortniteClient.FORTNITE_ACCOUNT_API + 'public/account'
            first = True
            for user_id in ids:
                if first:
                    url = url + '?accountId=' + user_id
                    first = False
                url = url + '&accountId=' + user_id
            data = FortniteClient.send_fortnite_get_request(url,
                                                            self._access_token)
            return data
        except RequestException as ex:
            if ex.response is 404:
                raise SiteNotAvailableException()
            raise ex


class LeaderboardEntry:

    def __init__(self, data):
        r"""
        Constructs a new Fortnite\Model\ForniteLeaderboard instance.

        :param data:    Array of mapped Leaderboard
        """

        for key, value in data.items():
            if key == 'rank':
                self.rank = value
                continue
            elif key == 'accountId':
                self.accountid = value
                continue
            elif key == 'value':
                self.score = value
                continue
            elif key == 'displayName':
                self.display_name = value
                continue
            else:
                continue


class NewsEntry:

    def __init__(self, news):
        for key, value in news.items():
            if key == 'image':
                self.image_url = value
                continue
            elif key == 'hidden':
                self.hidden = value
                continue
            elif key == 'title':
                self.title = value
            elif key == 'body':
                self.body = value
                continue
            else:
                continue


class StoreEntry:

    def __init__(self, store):
        for key, value in store.items():
            if key == 'devName':
                info = self._decode_info(value)
                self.name = info[0]
                self.price = info[1]

    @staticmethod
    def _decode_info(enc_name):
        name = enc_name.replace('[VIRTUAL]', '')
        name = name.replace('1 x ', '')
        name_split = name.split(' for ')
        price_split = name_split[1].split(' ')
        price = price_split[0]
        name = name_split[0]
        return [name, price]


class Platform:

    def __init__(self, platform):
        self.solo = StatEntry(None)
        self.duo = StatEntry(None)
        self.squad = StatEntry(None)
        self.all = StatEntry(None)
        for key, value in platform.items():
            if key == 'p2':
                self.solo = StatEntry(value)
                continue
            elif key == 'p9':
                self.squad = StatEntry(value)
                continue
            elif key == 'p10':
                self.duo = StatEntry(value)
                continue
        stats_all = {
            'placetop1': self.solo.wins + self.duo.wins + self.squad.wins,
            'placetop3': self.solo.top3 + self.duo.top3 + self.squad.top3,
            'placetop5': self.solo.top5 + self.duo.top5 + self.squad.top5,
            'placetop6': self.solo.top6 + self.duo.top6 + self.squad.top6,
            'placetop10': self.solo.top10 + self.duo.top10 + self.squad.top10,
            'placetop12': self.solo.top12 + self.duo.top12 + self.squad.top12,
            'placetop25': self.solo.top25 + self.duo.top25 + self.squad.top25,
            'kills': self.solo.kills + self.duo.kills + self.squad.kills,
            'score': self.solo.score + self.duo.score + self.squad.score,
            'matchesplayed': self.solo.matches_played + self.duo.matches_played + self.squad.matches_played,
            'minutesplayed': self.solo.minutes_played + self.duo.minutes_played + self.squad.minutes_played
        }
        self.all = StatEntry(stats_all)


class StatEntry:

    def __init__(self, stats):
        self.wins = 0
        self.top3 = 0
        self.top5 = 0
        self.top6 = 0
        self.top10 = 0
        self.top12 = 0
        self.top25 = 0
        self.kills = 0
        self.matches_played = 0
        self.minutes_played = 0
        self.score = 0
        self.kills_per_game = 0
        self.score_per_match = 0
        self.win_ratio = 0
        self.deaths = 0
        self.kd = 0
        if stats is not None:
            for key, value in stats.items():
                if key == 'placetop1':
                    self.wins = value
                    continue
                elif key == 'placetop3':
                    self.top3 = value
                    continue
                elif key == 'placetop5':
                    self.top5 = value
                    continue
                elif key == 'placetop6':
                    self.top6 = value
                    continue
                elif key == 'placetop10':
                    self.top10 = value
                    continue
                elif key == 'placetop12':
                    self.top12 = value
                    continue
                elif key == 'placetop25':
                    self.top25 = value
                    continue
                elif key == 'matchesplayed':
                    self.matches_played = value
                    continue
                elif key == 'kills':
                    self.kills = value
                    continue
                elif key == 'score':
                    self.score = value
                    continue
                elif key == 'minutesplayed':
                    self.minutes_played = value
                    continue
                elif key == 'lastmodified':
                    continue

            self.kills_per_game = self.matches_played is 0 and 0 or "{0:.2f}".format(
                self.kills / self.matches_played)
            self.score_per_match = self.matches_played is 0 and 0 or "{0:.2f}".format(self.score / self.matches_played)
            self.win_ratio = self.matches_played is 0 and 0 or "{0:.2f}".format(self.wins / self.matches_played)
            self.deaths = self.matches_played - self.wins
            self.kd = self.kills is 0 and 0 or "{0:.2f}".format(self.kills / self.deaths)


class FortniteAPI:

    def __init__(self, auth):
        self._auth = auth

    def get_news(self, news_type, lang=Language.ENGLISH):
        if self._auth.token_expired():
            self._auth.refresh(self._auth.refresh_token())
        try:
            data = FortniteClient.send_fortnite_get_request(FortniteClient.FORTNITE_NEWS_API +
                                                            'pages/fortnite-game',
                                                            self._auth.access_token(),
                                                            {'Accept-Language': lang.value})
            print('[NEWS V1] ' + str(data))
            data = data[news_type.value]['news']['messages']
            print('[NEWS V2] ' + str(data))
            news = []
            for news_item in data:
                news.append(NewsEntry(news_item))
            return news
        except RequestException as ex:
            if ex.response is 404:
                raise SiteNotAvailableException()
            raise ex

    def get_store(self, lang):
        if self._auth.token_expired():
            self._auth.refresh(self._auth.refresh_token())
        try:
            data = FortniteClient.send_fortnite_get_request(FortniteClient.FORTNITE_API +
                                                            'storefront/v2/catalog',
                                                            self._auth.access_token(),
                                                            {'X-EpicGames-Language': lang.value})
            data = data['storefronts']
            print('--------------------------DAILY STORE----------------------------------------------')
            daily_store_entries = data[10]['catalogEntries']
            daily_store = []
            for entry in daily_store_entries:
                daily_store.append(StoreEntry(entry))
            for i in daily_store:
                print('{} für {} VBucks'.format(i.name, i.price))

            print('--------------------------FEATURED STORE----------------------------------------------')

            featured_store_entries = data[2]['catalogEntries']
            featured_store = []
            for entry in featured_store_entries:
                featured_store.append(StoreEntry(entry))
            for i in featured_store:
                print('{} für {} VBucks'.format(i.name, i.price))

            store = {'daily': daily_store, 'featured': featured_store}
            return store

        except RequestException as ex:
            if ex.response is 404:
                raise SiteNotAvailableException()
            raise ex

    def server_online(self):
        if self._auth.token_expired():
            self._auth.refresh(self._auth.refresh_token())
        data = FortniteClient.send_fortnite_get_request(FortniteClient.FORTNITE_STATUS_API +
                                                        'service/bulk/status?serviceId=Fortnite',
                                                        self._auth.access_token())
        status = data[0]['status']
        return status == 'UP'

    def time_to_maintenance(self):
        if self._auth.token_expired():
            self._auth.refresh(self._auth.refresh_token())
        data = FortniteClient.send_fortnite_get_request(FortniteClient.FORTNITE_STATUS_API +
                                                        'service/bulk/status?serviceId=Fortnite',
                                                        self._auth.access_token())
        if not data.__contains__('timeToShutdownInMs'):
            return 0
        time_in_ms = data[0]['timeToShutdownInMs']
        return int(time_in_ms / 1000)

    def get_stats(self, account_id, time_window=TimeWindow.ALLTIME):
        if self._auth.token_expired():
            self._auth.refresh(self._auth.refresh_token())
        data = FortniteClient.send_fortnite_get_request(FortniteClient.FORTNITE_API +
                                                        'stats/accountId/' +
                                                        account_id +
                                                        '/bulk/window/' +
                                                        time_window.value,
                                                        self._auth.access_token())
        print('[STATS V1] ' + str(data))
        if data.__contains__('errorCode'):
            raise StatNameCollectionNotFoundException()
        compiled_stats = {}
        first = True
        for stat in data:
            parsed = self._parse_stat_item(stat)
            if first:
                compiled_stats = parsed
                first = False
            compiled_stats = self._dict_merge(parsed, compiled_stats)

        print('[STATS V2] ' + str(compiled_stats))

        platforms = {}
        for key, value in compiled_stats.items():
            platforms[key] = Platform(value)

        return platforms

    @staticmethod
    def _parse_stat_item(stat):
        pieces = stat['name'].split('_')
        arr1 = {pieces[1]: stat['value']}
        arr2 = {pieces[4]: arr1}
        result = {pieces[2]: arr2}
        return result

    def _dict_merge(self, a, b):
        # SOURCE: https://www.xormedia.com/recursively-merge-dictionaries-in-python/
        """recursively merges dict's. not just simple a['key'] = b['key'], if
        both a and bhave a key who's value is a dict then dict_merge is called
        on both values and the result stored in the returned dictionary."""
        if not isinstance(b, dict):
            return b
        result = deepcopy(a)
        for k, v in b.items():
            if k in result and isinstance(result[k], dict):
                result[k] = self._dict_merge(result[k], v)
            else:
                result[k] = deepcopy(v)
        return result

    def lookup(self, username):
        if self._auth.token_expired():
            self._auth.refresh(self._auth.refresh_token())
        try:
            data = FortniteClient.send_fortnite_get_request(FortniteClient.FORTNITE_PERSONA_API +
                                                            'public/account/lookup?q=' +
                                                            username.replace(' ', '%20'),
                                                            self._auth.access_token())
            if data.__contains__('errorCode'):
                raise UserNotFoundException(username)
            return data['id']
        except RequestException as ex:
            if ex.response is 404:
                raise SiteNotAvailableException()
            raise ex

    def get_leaderboard(self, platform, news_type):
        if self._auth.token_expired():
            self._auth.refresh(self._auth.refresh_token())

        try:
            data = FortniteClient.send_fortnite_post_request(FortniteClient.FORTNITE_API +
                                                             'leaderboards/type/global/stat/br_placetop1_' +
                                                             platform.value +
                                                             '_m0' +
                                                             news_type.value +
                                                             '/window/weekly?ownertype=1&itemsPerPage=50',
                                                             self._auth.access_token())
            print(' ')
            print('[LEADERBOARD V1] ' + str(data))
            entries = data['entries']
            print('[LEADERBOARD V2] ' + str(entries))

            ids = []
            for entry in entries:
                entry['accountId'] = entry['accountId'].replace('-', '')
                ids.append(entry['accountId'])

            print('[LEADERBOARD IDs] ' + str(ids))

            accounts = Account(self._auth.access_token()).get_display_names_from_ids(ids)
            print('[LEADERBOARD ACCOUNTS] ' + str(accounts))

            for account in accounts:
                for entry in entries:
                    if entry['accountId'] == account['id']:
                        entry['displayname'] = account['displayName']
                        break

            print('[LEADERBOARD V3] ' + str(entries))
            leaderboard = []
            for entry in entries:
                leaderboard.append(LeaderboardEntry(entry))

            return leaderboard

        except RequestException as ex:
            if ex.response is 404:
                raise SiteNotAvailableException()
            raise ex

    def kill_session(self):
        FortniteClient.send_unreal_client_delete_request(FortniteClient.EPIC_OAUTH_TOKEN_KILL_ENDPOINT +
                                                         self._auth.access_token(),
                                                         self._auth.access_token())


if __name__ == '__main__':
    auth = Auth('Luc1412.game@gmail.com', 'Ak7jlm3t')
    fortnite_api = FortniteAPI(auth)
    news = fortnite_api.get_news(NewsType.BATTLEROYALE, Language.GERMAN)
    for new in news:
        print('------------------------------------------------')
        print(new.title)
        print(new.body)
        print(new.image_url)
