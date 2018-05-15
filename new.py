import datetime
import json
import sched
import time

import requests


class ConfigManager:
    from configparser import ConfigParser
    config_values = {}
    cfg = ConfigParser()

    def __init__(self):
        self.load_config()

    def load_config(self):

        self.cfg.read('config.ini', encoding='utf-8')

        sections = self.cfg.sections()

        for section in sections:
            options = self.cfg.options(section)
            for option in options:
                value = self.cfg.get(section, option)
                self.config_values[section.lower() + '.' + option.lower()] = value

    def get_config_value(self, path):
        path = path.lower()
        if self.config_values.__contains__(path):
            return self.config_values[path]
        else:
            return '**error**'


config_manager = ConfigManager()


class PeriodicScheduler(object):

    # SOURCE: http://www.diegor.it/2014/06/19/howto-schedule-repeating-events-with-python/

    def __init__(self):
        self.scheduler = sched.scheduler(time.time, time.sleep)

    def setup(self, interval, action, actionargs=()):
        action(*actionargs)
        self.scheduler.enter(interval, 1, self.setup,
                             (interval, action, actionargs))

    def run(self):
        self.scheduler.run()


logindata = {
    'Email': 'Test'
}


class FortniteAPI:
    OAUTH_TOKEN_URL = 'https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/token'
    OAUTH_EXCHANGE_URL = 'https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/exchange'
    OAUTH_VERIFY_URL = 'https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/verify?includePerms=true'
    FortnitePVEInfo_URL = 'https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/game/v2/world/info'
    FortniteStore_URL = 'https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/storefront/v2/catalog'
    FortniteStatus_URL = 'https://lightswitch-public-service-prod06.ol.epicgames.com/lightswitch/api/service/bulk/status?serviceId=Fortnite'
    FortniteNews_URL = 'https://fortnitecontent-website-prod07.ol.epicgames.com/content/api/pages/fortnite-game'

    def _get_lookup_url(self, username):
        url = 'https://persona-public-service-prod06.ol.epicgames.com/persona/api/public/account/lookup?q='
        return url + username.replace(' ', '%20')

    def _get_brstats_url(self, account_id):
        return 'https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/stats/accountId/{}/bulk/window/alltime'.format(
            account_id)

    def _get_pvestats_url(self, account_id):
        return 'https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/game/v2/profile/{}/client/QueryProfile?profileId=collection_book_schematics0&rvn=-1'.format(
            account_id)

    def _kill_session_url(self, token):
        return 'https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/sessions/kill/' + token

    def _get_leaderboardscore_url(self, platform, groupType):
        return 'https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/leaderboards/type/global/stat/br_placetop1_{}_m0{}/window/weekly?ownertype=1&itemsPerPage=50'.format(
            platform, groupType)

    def _get_display_name_from_id_url(self, id):
        return 'https://account-public-service-prod03.ol.epicgames.com/account/api/public/account?accountId=' + id

    def check_platform(self, stats, platform):
        result = False

        for stat in stats:
            print()

    def checkToken(self):
        actual_date = datetime.datetime.now()
        expire_date = None
        if self.access_token is not None and self.expire_at is not None and expire_date < actualDate:
            self.expires_at = None
            headers = {
                'Authorization': 'basic ' + self.credentials[3]
            }
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'includePerms': True
            }
            response = json.loads(requests.post(self.OAUTH_TOKEN_URL, data, None, headers=headers).text)
            self.expires_at = response['expires_at']
            self.access_token = response['access_token']
            self.refresh_token = response['refresh_token']

    def __init__(self, credentials, options):
        self.debug = config_manager.get_config_value('General.Debug')
        self.expires_at = None
        self.access_token = None
        self.refresh_token = None
        self.code = None
        if credentials is not None and len(credentials) == 4:
            if self.debug:
                print('Fortnite-API - Credentials Params OK')
            self.credentials = credentials
        else:
            if self.debug:
                print(
                    'Fortnite-API - Please give credentials [Email, Password, Client Launcher Token, Client Fortnite Token]')

        periodic_scheduler = PeriodicScheduler()
        periodic_scheduler.setup(1, self.checkToken)
        periodic_scheduler.run()

    def login(self):
        token_config = {
            'grant_type': 'password',
            'username': self.credentials[0],
            'password': self.credentials[1],
            'includePerms': True
        }
        headers1 = {
            'Authorization': "basic " + self.credentials[2]
        }
        response = json.loads(requests.post(self.OAUTH_TOKEN_URL, token_config, True, headers=headers1).text)
        self.access_token = response['access_token']
        headers2 = {
            'Authorization': "bearer " + self.access_token
        }
        response2 = json.loads(requests.get(self.OAUTH_EXCHANGE_URL, None, headers=headers2).text)
        self.code = response2['code']
        data3 = {
            'grant_type': 'exchange_code',
            'exchange_code': self.code,
            'includePerms': True,
            'token_type': 'egl'
        }
        headers3 = {
            'Authorization': 'basic ' + self.credentials[3]
        }
        response3 = json.loads(requests.post(self.OAUTH_TOKEN_URL, data3, None, headers=headers3).text)
        self.expires_at = response3['expires_at']
        self.access_token = response3['access_token']
        self.refresh_token = response3['refresh_token']

    def lookup(self, username):
        headers = {
            'Authorization': 'bearer ' + self.access_token
        }
        response = json.loads(requests.get(self.LOOKUP_URL + username.replace(' ', '%20'), None, headers=headers))
        if response.__contains__('errorCode'):
            return None
        else:
            return response

    def checkPlayer(self, username, platform):
        user_data = self.lookup(username)
        headers = {
            'Authorization': 'bearer ' + self.access_token
        }
        response = json.loads(requests.get(self._get_brstats_url(user_data['id']), None, headers=headers).text)
        if self.check_platform(response, platform.lower()):
            return datetime
        else:
            return None


def login():
    tokenConfig = {
        'grant_type': 'password',
        'username': 'Luc1412.game@gmail.com',
        'password': 'Ak7jlm3t',
        'includePerms': True
    }
    headers1 = {
        'Authorization': "basic MzRhMDJjZjhmNDQxNGUyOWIxNTkyMTg3NmRhMzZmOWE6ZGFhZmJjY2M3Mzc3NDUwMzlkZmZlNTNkOTRmYzc2Y2Y="
    }
    response1 = json.loads(
        requests.post('https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/token', tokenConfig,
                      True,
                      headers=headers1).text)
    print(response1)
    access_token = response1['access_token']
    headers2 = {
        'Authorization': "bearer " + access_token
    }
    response2 = json.loads(
        requests.get('https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/exchange', None,
                     headers=headers2).text)
    print(response2)
    code = response2['code']
    data3 = {
        'grant_type': 'exchange_code',
        'exchange_code': code,
        'includePerms': True,
        'token_type': 'egl'
    }
    headers3 = {
        'Authorization': 'basic ZWM2ODRiOGM2ODdmNDc5ZmFkZWEzY2IyYWQ4M2Y1YzY6ZTFmMzFjMjExZjI4NDEzMTg2MjYyZDM3YTEzZmM4NGQ='
    }
    response3 = json.loads(
        requests.post('https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/token', data3, None,
                      headers=headers3).text)
    print(response3)

    headers = {
        'Authorization': 'bearer ' + access_token
    }
    user_data = json.loads(requests.get(
        'https://persona-public-service-prod06.ol.epicgames.com/persona/api/public/account/lookup?q=' + 'Luc1412'.replace(
            ' ', '%20'), None, headers=headers).text)
    print(user_data)

    headers = {
        'Authorization': 'bearer ' + access_token
    }
    response = json.loads(requests.get(
        'https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/stats/accountId/' + user_data[
            'id'] + '/bulk/window/alltime', None, headers=headers).text)
    print(response)


if __name__ == '__main__':
    login()
