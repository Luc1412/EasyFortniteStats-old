import asyncio
import datetime
import json
import logging
import os
import sys
import time
from datetime import time

import aiohttp
import discord
from PIL import Image
from discord import ActivityType, Embed, Color, Activity, Status

from fortnite_stats_api import Auth, FortniteAPI, UserNotFoundException, StatNameCollectionNotFoundException

bot = discord.Client()

status_lock = False


# #######################################################
# ################### CONFIG MANAGER ####################
# #######################################################
class ConfigManager:
    from configparser import ConfigParser
    _config_values = {}
    cfg = ConfigParser()

    def __init__(self):
        self._load_config()

    def _load_config(self):

        self.cfg.read('configs/config.ini', encoding='utf-8')

        sections = self.cfg.sections()

        for section in sections:
            options = self.cfg.options(section)
            for option in options:
                value = self.cfg.get(section, option)
                self._config_values[section.lower() + '.' + option.lower()] = value

    def get_config_value(self, path):
        path = path.lower()
        if self._config_values.__contains__(path):
            return self._config_values[path]
        else:
            return '**error**'

    def set_temp_config_value(self, path, value):
        self._config_values[path] = value


config_manager = ConfigManager()

# #######################################################
# ################## INITIALIZING API ###################
# #######################################################
auth = Auth(config_manager.get_config_value('API.Email'), config_manager.get_config_value('API.Password'))
fortnite_api = FortniteAPI(auth)


# #######################################################
# ################## DATABASE MANAGER ###################
# #######################################################
class DatabaseManager:

    def __init__(self):
        self.client = None
        self.database = None
        self._connect()

    def _connect(self):
        from pymongo import MongoClient
        self.client = MongoClient(config_manager.get_config_value('MongoDb.ConnectURI'))
        self.database = self.client[config_manager.get_config_value('MongoDb.Database')]

        self._setup()

    def _setup(self):
        if self.is_setup():
            return
        requests = {
            'name': 'Requests',
            'score': 0
        }
        servers = {
            'name': 'Guilds',
            'score': 0,
            'highscore': 0
        }
        self.database['Stats'].insert_many([requests, servers])

    def is_setup(self):
        db_filter = {
            'name': 'Requests'
        }
        return self.database['Stats'].find_one(db_filter) is not None

    def guild_exists(self, guild):
        db_filter = {
            'id': guild.id
        }
        return self.database['GuildData'].find_one(db_filter) is not None

    def add_guild(self, guild):
        if self.guild_exists(guild):
            return
        guild_doc = {
            'guild_id': str(guild.id),
            'lang': 'EN',
            'has_donator': False,
            'custom_api-key': ''
        }
        self.add_document('GuildData', guild_doc)

    def get_document(self, collection, key, value):
        db_filter = {
            key: value
        }
        return self.database[collection].find_one(db_filter)

    def set_document(self, collection, filter_key, filer_value, key, value):
        document = self.get_document(collection, filter_key, filer_value)
        document[key] = value
        db_filter = {
            filter_key: filer_value
        }
        update_operation = {
            "$set": document
        }
        self.database[collection].update_one(db_filter, update_operation, upsert=False)

    def add_document(self, collection, document):
        self.database[collection].insert_one(document)


database_manager = DatabaseManager()


# #######################################################
# #################### LANG MANAGER #####################
# #######################################################
class LangManager:

    def __init__(self):
        import codecs

        self.german_messages = json.load(codecs.open('configs/DE_de.json', 'r', 'utf-8-sig'))
        self.english_messages = json.load(codecs.open('configs/EN_us.json', 'r', 'utf-8-sig'))

    def get_messages(self, guild, messages):
        try:

            lang = database_manager.get_document('GuildData', 'guild_id', str(guild.id))['lang']
            print(lang)

            if lang == 'DE':
                return self.german_messages[messages]
            else:
                return self.english_messages[messages]
        except (TypeError, KeyError):
            database_manager.add_guild(guild)
            return '__**Error!**__ Guild has been added to Database. Please repeat the Command!'

    @staticmethod
    def set_guild_lang(guild, lang):
        database_manager.set_document('GuildData', 'guild_id', str(guild.id), 'lang', lang)


lang_manager = LangManager()


# #######################################################
# #################### USER MANAGER #####################
# #######################################################
class UserManager:

    @staticmethod
    def add_user(user):
        user_doc = {
            'id': user.id,
            'fn_name': 'None',
            'platform': 'None',
            'output_type': 1
        }
        database_manager.add_document('UserData', user_doc)

    @staticmethod
    def user_exists(user):
        db_filter = {
            'id': user.id
        }
        return database_manager.database['UserData'].find_one(db_filter) is not None

    def set_player_name(self, user, name, platform):
        if not self.user_exists(user):
            self.add_user(user)
        database_manager.set_document('UserData', 'id', user.id, 'fn_name', name)
        database_manager.set_document('UserData', 'id', user.id, 'platform', platform)

    def set_output_type(self, user, output_type):
        if not self.user_exists(user):
            self.add_user(user)
        database_manager.set_document('UserData', 'id', user.id, 'output_type', output_type)

    @staticmethod
    def get_user_data(user):
        return database_manager.get_document('UserData', 'id', user.id)


user_manager = UserManager()


# #######################################################
# #################### STATS MANAGER ####################
# #######################################################
class StatsManager:

    @staticmethod
    def add_request():
        old = database_manager.get_document('Stats', 'name', 'Requests')['score']
        new = old + 1
        database_manager.set_document('Stats', 'name', 'Requests', 'score', new)

    @staticmethod
    def get_requests():
        return database_manager.get_document('Stats', 'name', 'Requests')['score']

    @staticmethod
    def set_guild_amount():
        curr_guild_amount = len(bot.guilds)
        guild_document = database_manager.get_document('Stats', 'name', 'Guilds')
        old_guild_amount = guild_document['score']
        if curr_guild_amount == old_guild_amount:
            return
        database_manager.set_document('Stats', 'name', 'Guilds', 'score', curr_guild_amount)
        highscore = guild_document['highscore']
        if curr_guild_amount <= highscore:
            return
        database_manager.set_document('Stats', 'name', 'Guilds', 'highscore', curr_guild_amount)

    @staticmethod
    def get_guild_max():
        return database_manager.get_document('Stats', 'name', 'Guilds')['highscore']

    @staticmethod
    def get_guild_amount():
        return len(bot.guilds)

    @staticmethod
    def get_user_amount():
        return database_manager.database['UserData'].count()


stats_manager = StatsManager()


# #######################################################
# ################## COOLDOWN MANAGER ###################
# #######################################################
class CommandCooldownManager:
    user_list = {}

    def add_user(self, user):
        self.user_list[user.id] = time.time() + int(config_manager.get_config_value('General.CommandCooldown'))

    def get_cooldown_time(self, user):
        if not self.user_list.__contains__(user.id):
            return 0
        entry_time = self.user_list.get(user.id)
        current_time = time.time()
        if current_time < entry_time:
            wait_time = int((current_time - entry_time) * -1)
            return wait_time
        return 0


cooldown_manager = CommandCooldownManager()


# #######################################################
# ################### LOGGING MANAGER ###################
# #######################################################
class LoggingManager:

    def __init__(self):
        import gzip
        import shutil
        if os.path.isfile('logs//latest.log'):
            filename = None
            index = 1
            date = datetime.datetime.now().strftime('%Y-%m-%d')
            while filename is None:
                check_filename = '{}-{}.log.gz'.format(date, index)
                if os.path.isfile('logs//{}'.format(check_filename)):
                    index = index + 1
                else:
                    filename = check_filename
            with open('logs//latest.log', 'rb') as f_in, gzip.open('logs//{}'.format(filename), 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
            os.remove('logs//latest.log')

        self._logger = logging.getLogger('efs')
        self._logger.setLevel(logging.DEBUG)
        log_formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')

        file_handler = logging.FileHandler(filename='logs//latest.log', encoding='utf-8', mode='w')
        file_handler.setFormatter(log_formatter)
        self._logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        self._logger.addHandler(console_handler)

    def debug(self, message):
        self._logger.debug(message)

    def info(self, message):
        self._logger.info(message)

    def warning(self, message):
        self._logger.warning(message)

    def error(self, message):
        self._logger.error(message)


logging_manager = LoggingManager()


# #######################################################
# ######################## UTILS ########################
# #######################################################
class Utils:

    @staticmethod
    async def update_server_count():
        dbltoken = config_manager.get_config_value('DBL-API.DBLToken')
        url = 'https://discordbots.org/api/bots/' + str(bot.user.id) + '/stats'
        headers = {"Authorization": dbltoken}
        payload = {'server_count': len(bot.guilds)}
        async with aiohttp.ClientSession() as aioclient:
            await aioclient.post(url, data=payload, headers=headers)

    @staticmethod
    async def send_temp_message(channel, title, content, color, delete_after):
        embed = Embed(description=content, color=color)
        embed.set_author(name=title,
                         icon_url=config_manager.get_config_value('URLs.Icon_Small_URL'))
        embed.set_footer(text='© Luc1412.de', icon_url=config_manager.get_config_value('URLs.Footer_Icon_URL'))
        try:
            await channel.send(embed=embed, delete_after=delete_after)
        except discord.Forbidden:
            return None

    @staticmethod
    def get_displayname(sys_name):
        sys_name = sys_name.lower()
        if sys_name == 'xb1':
            return 'XBox One'
        elif sys_name == 'psn' or sys_name == 'ps4':
            return 'Playstation 4'
        elif sys_name == 'pc':
            return 'PC'
        return None

    @staticmethod
    async def get_upload_channel():
        return bot.get_channel(int(config_manager.get_config_value('Channel.UploadChannel')))

    @staticmethod
    async def get_error_channel():
        return bot.get_channel(int(config_manager.get_config_value('Channel.ErrorChannel')))

    @staticmethod
    async def get_info_channel():
        return bot.get_channel(int(config_manager.get_config_value('Channel.InfoChannel')))

    @staticmethod
    def get_places():
        names = {
            1: 'Junk Junction',
            2: 'Lazy Links',
            3: 'Risky Reels',
            4: 'Haunted Hills',
            5: 'Pleasant Park',
            6: 'Wailing Woods',
            7: 'Loot Lake',
            8: 'Tomato Town',
            9: 'Snobby Shores',
            10: 'Tilted Towers',
            11: 'Dusty Devot',
            12: 'Lonely Lodge',
            13: 'Retail Row',
            14: 'Greasy Grove',
            15: 'Shifty Shafts',
            16: 'Salty Springs',
            17: 'Fatal Fields',
            18: 'Paradise Palms',
            19: 'Flush Factory',
            20: 'Lucky Landing'
        }
        return names

    @staticmethod
    def get_locations():
        locations = {
            1: (225, 35),  # Hall in north
            2: (170, 40),  # Junk Junktion
            3: (395, 110),  # Motel
            4: (540, 160),  # Lazy Links
            5: (760, 115),  # Risky Reels
            6: (130, 170),  # Haunted Hills
            7: (270, 250),  # Pleasant Park
            8: (175, 283),  # Forest house
            9: (130, 360),  # Rocket base
            10: (380, 330),  # 2 industrial buildings on Loot Lake
            11: (435, 325),  # House in the middle of Loot Lake
            12: (680, 270),  # Tomato Town
            13: (850, 210),  # Wailing Woods
            14: (750, 365),  # Container storage
            15: (925, 375),  # Lonely Lodge
            16: (990, 470),  # Superheroes Base
            17: (865, 465),  # Camping ground
            18: (770, 500),  # Retail Row
            19: (610, 450),  # Dusty Devot
            20: (595, 410),  # old Dusty Depot halls next to the crater
            21: (365, 455),  # Tilted Towers
            22: (220, 445),  # Swimming hall
            23: (70, 415),  # Snobby Shores
            24: (115, 480),  # Viking village
            25: (210, 590),  # Greasy Grove
            26: (365, 625),  # Shifty Shafts
            27: (570, 590),  # Salty Springs
            28: (355, 720),  # Small village next to the big chair
            29: (430, 805),  # Industrial area with the disco
            30: (350, 865),  # Flush Factory
            31: (575, 905),  # Lucky Landings
            32: (615, 735),  # Fatal Fields
            33: (500, 680),  # Mountain with house
            34: (700, 840),  # Filling station in the desert
            35: (780, 880),  # Wild Western village
            36: (880, 800),  # Scrap yard in the desert
            37: (840, 715),  # Paradise Palms
            38: (760, 640),  # Bridge in the desert
            39: (865, 590),  # Diner
            40: (930, 560),  # Race course

        }
        return locations


utils = Utils()


# #######################################################
# ################## PLAYER COMMANDS ####################
# #######################################################
class FNCommand:

    @staticmethod
    async def ex(member, channel, args):
        messages = lang_manager.get_messages(channel.guild, 'FnCommand')
        if type(messages) is str:
            return messages
        cooldown_time = cooldown_manager.get_cooldown_time(member)
        if cooldown_time > 0:
            return messages['CooldownMsg'].format(cooldown_time)
        cooldown_manager.add_user(member)

        args_len = len(args)

        if args_len is 0:
            if not user_manager.user_exists(member):
                return messages['NoLink']
            start = time.time()
            user_data = user_manager.get_user_data(member)
            player_name, platform = user_data['fn_name'], user_data['platform']
            try:
                async with channel.typing():
                    account_id = fortnite_api.lookup(player_name)
                    player_data = fortnite_api.get_stats(account_id)

                    lifetime_stats = player_data[platform]
                    output_type = user_data['output_type']

                    stats_message = Embed(color=Color.blurple())
                    stats_message.set_footer(text='© Luc1412.de',
                                             icon_url=config_manager.get_config_value('URLs.Footer_Icon_URL'))
                    stats_message.set_author(name=messages['Stats'].format(player_name,
                                                                           utils.get_displayname(platform)),
                                             icon_url=config_manager.get_config_value("URLs.Icon_Small_URL"))

                    if output_type is 0:
                        stats_message.add_field(name=messages['Alltime'],
                                                value=messages['StatsMessage'].format(lifetime_stats.all.score,
                                                                                      lifetime_stats.all.score_per_match,
                                                                                      lifetime_stats.all.minutes_played,
                                                                                      lifetime_stats.all.matches_played,
                                                                                      lifetime_stats.all.wins,
                                                                                      lifetime_stats.all.win_ratio,
                                                                                      lifetime_stats.all.top3,
                                                                                      lifetime_stats.all.top25,
                                                                                      lifetime_stats.all.kills,
                                                                                      lifetime_stats.all.kills_per_game,
                                                                                      lifetime_stats.all.deaths,
                                                                                      lifetime_stats.all.kd),
                                                inline=True)
                        stats_message.add_field(name='Solo',
                                                value=messages['StatsMessage'].format(lifetime_stats.solo.score,
                                                                                      lifetime_stats.solo.score_per_match,
                                                                                      lifetime_stats.solo.minutes_played,
                                                                                      lifetime_stats.solo.matches_played,
                                                                                      lifetime_stats.solo.wins,
                                                                                      lifetime_stats.solo.win_ratio,
                                                                                      lifetime_stats.solo.top3,
                                                                                      lifetime_stats.solo.top25,
                                                                                      lifetime_stats.solo.kills,
                                                                                      lifetime_stats.solo.kills_per_game,
                                                                                      lifetime_stats.solo.deaths,
                                                                                      lifetime_stats.solo.kd),
                                                inline=True)
                        stats_message.add_field(name='Duo',
                                                value=messages['StatsMessage'].format(lifetime_stats.duo.score,
                                                                                      lifetime_stats.duo.score_per_match,
                                                                                      lifetime_stats.duo.minutes_played,
                                                                                      lifetime_stats.duo.matches_played,
                                                                                      lifetime_stats.duo.wins,
                                                                                      lifetime_stats.duo.win_ratio,
                                                                                      lifetime_stats.duo.top3,
                                                                                      lifetime_stats.duo.top25,
                                                                                      lifetime_stats.duo.kills,
                                                                                      lifetime_stats.duo.kills_per_game,
                                                                                      lifetime_stats.duo.deaths,
                                                                                      lifetime_stats.duo.kd),
                                                inline=True)
                        stats_message.add_field(name='Squad',
                                                value=messages['StatsMessage'].format(lifetime_stats.squad.score,
                                                                                      lifetime_stats.squad.score_per_match,
                                                                                      lifetime_stats.squad.minutes_played,
                                                                                      lifetime_stats.squad.matches_played,
                                                                                      lifetime_stats.squad.wins,
                                                                                      lifetime_stats.squad.win_ratio,
                                                                                      lifetime_stats.squad.top3,
                                                                                      lifetime_stats.squad.top25,
                                                                                      lifetime_stats.squad.kills,
                                                                                      lifetime_stats.squad.kills_per_game,
                                                                                      lifetime_stats.squad.deaths,
                                                                                      lifetime_stats.squad.kd),
                                                inline=True)
                        try:
                            await channel.send(embed=stats_message)
                            end = time.time()
                            logging_manager.info('Took {} seconds to fetch stats!'
                                                 .format(datetime.timedelta(seconds=end - start)))
                        except discord.Forbidden:
                            return None
                    elif output_type is 1:
                        print()
                    elif output_type is 3:
                        print()
            except UserNotFoundException:
                return messages['WrongName'].format(player_name)

        else:
            arg1 = args[0].lower()
            if arg1 == 'help':
                help_message = Embed(color=Color.from_rgb(103, 211, 242))
                help_message.set_thumbnail(url=config_manager.get_config_value('URLs.Icon_Big_URL'))
                help_message.set_author(name=messages['HelpHead'],
                                        icon_url=config_manager.get_config_value('URLs.Icon_Small_URL'))
                help_message.set_footer(text='© Luc1412.de',
                                        icon_url=config_manager.get_config_value('URLs.Footer_Icon_URL'))
                help_message.add_field(name='Commands:',
                                       value=messages['UserHelp'],
                                       inline=False)
                if member.guild_permissions.administrator:
                    help_message.add_field(name='Admin Commands:',
                                           value=messages['AdminHelp'],
                                           inline=False)
                help_message.add_field(name=messages['ExtensionTitle'],
                                       value=messages['HelpExtension'],
                                       inline=False)
                try:
                    await member.send(embed=help_message)
                except discord.Forbidden:
                    return messages['DMFail'].format(member.mention)
            elif arg1 == 'info':
                import sys
                import os
                import psutil
                process = psutil.Process(os.getpid())
                memory_used = process.memory_info().rss
                available_mem = psutil.virtual_memory().free + memory_used
                percent = "{0:.2f}".format(100 / available_mem * memory_used)
                memory_used = int(memory_used / 1048576)
                available_mem = int(available_mem / 1048576)
                ping1 = time.perf_counter()
                upload_channel = await utils.get_upload_channel()
                await upload_channel.send(
                    'Ping from {}'.format(channel.guild.region))
                ping2 = time.perf_counter()
                ping = round((ping2 - ping1) * 1000)

                info_message = Embed(color=Color.dark_blue())

                info_message.add_field(name=messages['ProjectInfo'],
                                       value='**Name:** ' + config_manager.get_config_value('Info.Name') + '\n' +
                                             messages['Author'] + config_manager.get_config_value(
                                           'Info.Author') + '\n' +
                                             '**Twitter:** [@luc141201]({})'.format(
                                                 config_manager.get_config_value('Info.Twitter')) + '\n' +
                                             messages['Website'] + config_manager.get_config_value(
                                           'Info.Website') + '\n' +
                                             '**Version:** ' + config_manager.get_config_value('Info.Version') + '\n' +
                                             '\n~~---------------------------------------------~~')

                info_message.add_field(name=messages['ServerStats'],
                                       value='**Python Version:** ' + "{}.{}.{}".format(sys.version_info[0],
                                                                                        sys.version_info[1],
                                                                                        sys.version_info[2]) + '\n' +
                                             '**Discord.py[recode] Version:** ' + discord.__version__ + '\n' +
                                             messages['UpTime'] + str(datetime.timedelta(
                                           seconds=int(time.time() - process.create_time()))) + '\n' +
                                             messages['RamUsage'].format(memory_used, available_mem, percent) + '\n' +
                                             '**Ping**: {} ms'.format(ping) + '\n' +
                                             '\n~~---------------------------------------------~~')

                info_message.add_field(name=messages['BotStats'],
                                       value=messages['ServerAmount'] + str(len(bot.guilds)) + '\n' +
                                             messages['HighestServerAmount'] + str(
                                           stats_manager.get_guild_max()) + '\n' +
                                             messages['RequestAmount'] + str(stats_manager.get_requests()) + '\n' +
                                             messages['LinkedUser'] + str(stats_manager.get_user_amount()) + '\n' +
                                             '\n~~---------------------------------------------~~')

                info_message.set_thumbnail(url=config_manager.get_config_value('URLs.Icon_Big_URL'))
                info_message.set_author(name=messages['InfoHead'],
                                        icon_url=config_manager.get_config_value('URLs.Icon_Small_URL'))

                try:
                    await channel.send(embed=info_message)
                except discord.Forbidden:
                    return None
            elif arg1 == 'lang':
                if not member.guild_permissions.administrator:
                    return messages['PermFail']
                if args_len is not 2:
                    return messages['LangFail']
                arg2 = args[1].upper()
                if not arg2 == 'DE':
                    if not arg2 == 'EN':
                        return messages['LangFail']
                lang_manager.set_guild_lang(channel.guild, arg2)
                await utils.send_temp_message(channel,
                                              messages['LangChangeHead'],
                                              messages['LangChangeDesc'].format(
                                                  arg2 == 'DE' and 'Deutsch' or arg2 == 'EN' and 'English'),
                                              Color.from_rgb(76, 209, 55),
                                              15)
            elif arg1 == 'rdm':
                if args_len is not 2:
                    return messages['RdmFail']
                arg2 = args[1].lower()
                if arg2 == 'name':
                    from random import randint
                    rdm_number = randint(1, len(utils.get_places()))
                    name = utils.get_places().get(rdm_number)
                    r = randint(0, 255)
                    g = randint(0, 255)
                    b = randint(0, 255)
                    rdm_name_message = Embed(color=Color.from_rgb(r, g, b),
                                             description=messages['RandomName'].format(name))
                    rdm_name_message.set_footer(text='© Luc1412.de',
                                                icon_url=config_manager.get_config_value('URLs.Footer_Icon_URL'))
                    rdm_name_message.set_author(name='Random Name Generator',
                                                icon_url=config_manager.get_config_value("URLs.Icon_Small_URL"))
                    try:
                        await channel.send(embed=rdm_name_message)
                    except discord.Forbidden:
                        return None
                    return None
                elif arg2 == 'location' or arg2 == 'loc':
                    old_time = time.time()
                    from random import randint
                    import io
                    async with channel.typing():
                        rdm_number = randint(1, len(utils.get_locations()))
                        location = utils.get_locations().get(rdm_number)
                        map = Image.open('assets/images/map.jpg')
                        marker = Image.open('assets/images/marker.png')
                        map.paste(marker, location, marker)
                        obj = io.BytesIO()
                        map.save(obj, format="JPEG")
                        obj.seek(0)
                        r = randint(0, 255)
                        g = randint(0, 255)
                        b = randint(0, 255)
                        rdm_loc_message = Embed(color=Color.from_rgb(r, g, b),
                                                description=messages['RdmLoc']['Invoke'] + messages['RdmLoc'][
                                                    str(rdm_number)])
                        rdm_loc_message.set_footer(text='© Luc1412.de',
                                                   icon_url=config_manager.get_config_value('URLs.Footer_Icon_URL'))
                        rdm_loc_message.set_author(name='Random Location Generator',
                                                   icon_url=config_manager.get_config_value("URLs.Icon_Small_URL"))
                        try:
                            upload_channel = await Utils.get_upload_channel()
                            message_n = await upload_channel.send(file=discord.File(obj, 'Location.jpg'))
                            rdm_loc_message.set_image(url=message_n.attachments[0].url)
                            await channel.send(embed=rdm_loc_message)
                        except discord.Forbidden:
                            return None
                    new_time = time.time()
                    logging_manager.info('Seconds to send rdm Loc: ' + str(new_time - old_time))
                    return None
                else:
                    return messages['RdmFail']
            elif arg1 == 'map':
                old_time = time.time()
                async with channel.typing():
                    try:
                        upload_channel = await Utils.get_upload_channel()
                        message_n = await upload_channel.send(file=discord.File('assets/images/map.jpg', 'Map.jpg'))
                        map_message = discord.Embed(description=messages['MapInfo'], color=Color.blurple())
                        map_message.set_footer(text='© Luc1412.de',
                                               icon_url=config_manager.get_config_value('URLs.Footer_Icon_URL'))
                        map_message.set_author(name='Fortnite Map',
                                               icon_url=config_manager.get_config_value("URLs.Icon_Small_URL"))
                        map_message.set_image(url=message_n.attachments[0].url)
                        await channel.send(embed=map_message)
                    except discord.Forbidden:
                        return None
                new_time = time.time()
                logging_manager.info('Seconds to send Map: ' + str(new_time - old_time))
                return None
            elif arg1 == 'donate':
                donate_message = discord.Embed(description=messages['DonateMessage'],
                                               color=Color.from_rgb(204, 142, 53))
                donate_message.set_footer(text='© Luc1412.de',
                                          icon_url=config_manager.get_config_value('URLs.Footer_Icon_URL'))
                donate_message.set_author(name='Fortnite Donate',
                                          icon_url=config_manager.get_config_value("URLs.Icon_Small_URL"))
                try:
                    await channel.send(embed=donate_message)
                except discord.Forbidden:
                    return
            elif arg1 == 'vote':
                donate_message = discord.Embed(description=messages['VoteMessage'],
                                               color=Color.from_rgb(64, 64, 122))
                donate_message.set_footer(text='© Luc1412.de',
                                          icon_url=config_manager.get_config_value('URLs.Footer_Icon_URL'))
                donate_message.set_author(name='Fortnite Donate',
                                          icon_url=config_manager.get_config_value("URLs.Icon_Small_URL"))
                try:
                    await channel.send(embed=donate_message)
                except discord.Forbidden:
                    return
            elif arg1 == 'status':
                async with channel.typing():
                    if fortnite_api.server_online():
                        color = Color.from_rgb(39, 174, 96)
                        desc = messages['StatusUp']
                        maintenance = fortnite_api.time_to_maintenance()
                        print(maintenance)
                        if maintenance is not 0:
                            desc = desc.format(
                                messages['MaintenanceIn'].format(datetime.timedelta(seconds=maintenance)))
                        else:
                            desc = desc.format(messages['NoMaintenance'])
                    else:
                        color = Color.from_rgb(192, 57, 43)
                        desc = messages['StatusDown']
                    status_message = discord.Embed(description=desc, color=color)
                    status_message.set_footer(text='© Luc1412.de',
                                              icon_url=config_manager.get_config_value('URLs.Footer_Icon_URL'))
                    status_message.set_author(name='Fortnite Status',
                                              icon_url=config_manager.get_config_value("URLs.Icon_Small_URL"))
                    try:
                        await channel.send(embed=status_message)
                    except discord.Forbidden:
                        return None
                return None
            elif arg1 == 'type':
                if args_len is not 2:
                    return messages['TypeHelp']
                arg2 = args[1].lower()
                try:
                    output_type = int(arg2)
                    if output_type > 3 or output_type < 1:
                        return messages['WrongNumber']
                    if output_type is 3:
                        return messages['TypeNA']
                    user_manager.set_output_type(member, output_type)
                    utils.send_temp_message(channel,
                                            messages['TypeSuccessHead'],
                                            messages['TypeSuccessDesc'].format(output_type),
                                            Color.from_rgb(76, 209, 55),
                                            15)
                    return None
                except TypeError:
                    return messages['TypeNumber']
            elif arg1 == 'link':
                if args_len < 3:
                    return messages['LinkFail']
                platform = args[1].lower()
                if platform != 'pc' and platform != 'xbox' and platform != 'ps4':
                    return messages['WrongPlatform']
                platform = platform.replace('xbox', 'xb1')
                name = args[2]
                for i in range(3, args_len):
                    name = name + ' ' + args[i]

                async with channel.typing():
                    try:
                        account_id = fortnite_api.lookup(name)
                        player_data = fortnite_api.get_stats(account_id)

                        try:
                            player_data[platform]
                            user_manager.set_player_name(member, name, platform)
                            await utils.send_temp_message(channel,
                                                          messages['LinkHead'],
                                                          messages['LinkDesc'].format(utils.get_displayname(platform),
                                                                                      name),
                                                          Color.from_rgb(76, 209, 55),
                                                          10)
                        except KeyError:
                            return messages['PlayerNoPlatform']
                    except UserNotFoundException:
                        return messages['WrongName'].format(name)
                return None
            elif arg1 == 'ps4':
                if args_len < 2:
                    return messages['Ps4Fail']
                start = time.time()
                first = True
                player_name = ''
                for i in range(1, args_len):
                    if first:
                        player_name = args[i]
                        first = False
                        continue
                    player_name = player_name + ' ' + args[i]
                print(player_name)
                try:
                    account_id = fortnite_api.lookup(player_name)
                    player_data = fortnite_api.get_stats(account_id)
                    try:
                        async with channel.typing():
                            lifetime_stats = player_data['ps4']
                            output_type = 1
                            if user_manager.user_exists(member):
                                output_type = user_manager.get_user_data(member)['output_type']

                            stats_message = Embed(color=Color.blurple())
                            stats_message.set_footer(text='© Luc1412.de',
                                                     icon_url=config_manager.get_config_value('URLs.Footer_Icon_URL'))
                            stats_message.set_author(name=messages['Stats'].format(player_name,
                                                                                   utils.get_displayname('ps4')),
                                                     icon_url=config_manager.get_config_value("URLs.Icon_Small_URL"))

                            if output_type is 0:
                                stats_message.add_field(name=messages['Alltime'],
                                                        value=messages['StatsMessage'].format(lifetime_stats.all.score,
                                                                                              lifetime_stats.all.score_per_match,
                                                                                              lifetime_stats.all.minutes_played,
                                                                                              lifetime_stats.all.matches_played,
                                                                                              lifetime_stats.all.wins,
                                                                                              lifetime_stats.all.win_ratio,
                                                                                              lifetime_stats.all.top3,
                                                                                              lifetime_stats.all.top25,
                                                                                              lifetime_stats.all.kills,
                                                                                              lifetime_stats.all.kills_per_game,
                                                                                              lifetime_stats.all.deaths,
                                                                                              lifetime_stats.all.kd),
                                                        inline=True)
                                stats_message.add_field(name='Solo',
                                                        value=messages['StatsMessage'].format(lifetime_stats.solo.score,
                                                                                              lifetime_stats.solo.score_per_match,
                                                                                              lifetime_stats.solo.minutes_played,
                                                                                              lifetime_stats.solo.matches_played,
                                                                                              lifetime_stats.solo.wins,
                                                                                              lifetime_stats.solo.win_ratio,
                                                                                              lifetime_stats.solo.top3,
                                                                                              lifetime_stats.solo.top25,
                                                                                              lifetime_stats.solo.kills,
                                                                                              lifetime_stats.solo.kills_per_game,
                                                                                              lifetime_stats.solo.deaths,
                                                                                              lifetime_stats.solo.kd),
                                                        inline=True)
                                stats_message.add_field(name='Duo',
                                                        value=messages['StatsMessage'].format(lifetime_stats.duo.score,
                                                                                              lifetime_stats.duo.score_per_match,
                                                                                              lifetime_stats.duo.minutes_played,
                                                                                              lifetime_stats.duo.matches_played,
                                                                                              lifetime_stats.duo.wins,
                                                                                              lifetime_stats.duo.win_ratio,
                                                                                              lifetime_stats.duo.top3,
                                                                                              lifetime_stats.duo.top25,
                                                                                              lifetime_stats.duo.kills,
                                                                                              lifetime_stats.duo.kills_per_game,
                                                                                              lifetime_stats.duo.deaths,
                                                                                              lifetime_stats.duo.kd),
                                                        inline=True)
                                stats_message.add_field(name='Squad',
                                                        value=messages['StatsMessage'].format(
                                                            lifetime_stats.squad.score,
                                                            lifetime_stats.squad.score_per_match,
                                                            lifetime_stats.squad.minutes_played,
                                                            lifetime_stats.squad.matches_played,
                                                            lifetime_stats.squad.wins,
                                                            lifetime_stats.squad.win_ratio,
                                                            lifetime_stats.squad.top3,
                                                            lifetime_stats.squad.top25,
                                                            lifetime_stats.squad.kills,
                                                            lifetime_stats.squad.kills_per_game,
                                                            lifetime_stats.squad.deaths,
                                                            lifetime_stats.squad.kd),
                                                        inline=True)
                                try:
                                    await channel.send(embed=stats_message)
                                    end = time.time()
                                    logging_manager.info('Took {} seconds to fetch stats!'
                                                         .format(datetime.timedelta(seconds=end - start)))
                                except discord.Forbidden:
                                    return None
                            elif output_type is 1:
                                print()
                            elif output_type is 3:
                                print()
                    except KeyError:
                        return messages['PlayerNoPlatform']
                except UserNotFoundException:
                    return messages['WrongName'].format(player_name)
                except StatNameCollectionNotFoundException:
                    return messages['PlayerNoPlatform']
                return None
            elif arg1 == 'xbox':
                if args_len < 2:
                    return messages['XboxFail']
                start = time.time()
                first = True
                player_name = ''
                for i in range(1, args_len):
                    if first:
                        player_name = args[i]
                        first = False
                        continue
                    player_name = player_name + ' ' + args[i]
                print(player_name)
                try:
                    account_id = fortnite_api.lookup(player_name)
                    player_data = fortnite_api.get_stats(account_id)
                    try:
                        async with channel.typing():
                            lifetime_stats = player_data['xb1']
                            output_type = 1
                            if user_manager.user_exists(member):
                                output_type = user_manager.get_user_data(member)['output_type']

                            stats_message = Embed(color=Color.blurple())
                            stats_message.set_footer(text='© Luc1412.de',
                                                     icon_url=config_manager.get_config_value('URLs.Footer_Icon_URL'))
                            stats_message.set_author(name=messages['Stats'].format(player_name,
                                                                                   utils.get_displayname('xb1')),
                                                     icon_url=config_manager.get_config_value("URLs.Icon_Small_URL"))

                            if output_type is 0:
                                stats_message.add_field(name=messages['Alltime'],
                                                        value=messages['StatsMessage'].format(lifetime_stats.all.score,
                                                                                              lifetime_stats.all.score_per_match,
                                                                                              lifetime_stats.all.minutes_played,
                                                                                              lifetime_stats.all.matches_played,
                                                                                              lifetime_stats.all.wins,
                                                                                              lifetime_stats.all.win_ratio,
                                                                                              lifetime_stats.all.top3,
                                                                                              lifetime_stats.all.top25,
                                                                                              lifetime_stats.all.kills,
                                                                                              lifetime_stats.all.kills_per_game,
                                                                                              lifetime_stats.all.deaths,
                                                                                              lifetime_stats.all.kd),
                                                        inline=True)
                                stats_message.add_field(name='Solo',
                                                        value=messages['StatsMessage'].format(lifetime_stats.solo.score,
                                                                                              lifetime_stats.solo.score_per_match,
                                                                                              lifetime_stats.solo.minutes_played,
                                                                                              lifetime_stats.solo.matches_played,
                                                                                              lifetime_stats.solo.wins,
                                                                                              lifetime_stats.solo.win_ratio,
                                                                                              lifetime_stats.solo.top3,
                                                                                              lifetime_stats.solo.top25,
                                                                                              lifetime_stats.solo.kills,
                                                                                              lifetime_stats.solo.kills_per_game,
                                                                                              lifetime_stats.solo.deaths,
                                                                                              lifetime_stats.solo.kd),
                                                        inline=True)
                                stats_message.add_field(name='Duo',
                                                        value=messages['StatsMessage'].format(lifetime_stats.duo.score,
                                                                                              lifetime_stats.duo.score_per_match,
                                                                                              lifetime_stats.duo.minutes_played,
                                                                                              lifetime_stats.duo.matches_played,
                                                                                              lifetime_stats.duo.wins,
                                                                                              lifetime_stats.duo.win_ratio,
                                                                                              lifetime_stats.duo.top3,
                                                                                              lifetime_stats.duo.top25,
                                                                                              lifetime_stats.duo.kills,
                                                                                              lifetime_stats.duo.kills_per_game,
                                                                                              lifetime_stats.duo.deaths,
                                                                                              lifetime_stats.duo.kd),
                                                        inline=True)
                                stats_message.add_field(name='Squad',
                                                        value=messages['StatsMessage'].format(
                                                            lifetime_stats.squad.score,
                                                            lifetime_stats.squad.score_per_match,
                                                            lifetime_stats.squad.minutes_played,
                                                            lifetime_stats.squad.matches_played,
                                                            lifetime_stats.squad.wins,
                                                            lifetime_stats.squad.win_ratio,
                                                            lifetime_stats.squad.top3,
                                                            lifetime_stats.squad.top25,
                                                            lifetime_stats.squad.kills,
                                                            lifetime_stats.squad.kills_per_game,
                                                            lifetime_stats.squad.deaths,
                                                            lifetime_stats.squad.kd),
                                                        inline=True)
                                try:
                                    await channel.send(embed=stats_message)
                                    end = time.time()
                                    logging_manager.info('Took {} seconds to fetch stats!'
                                                         .format(datetime.timedelta(seconds=end - start)))
                                except discord.Forbidden:
                                    return None
                            elif output_type is 1:
                                print()
                            elif output_type is 3:
                                print()
                    except KeyError:
                        return messages['PlayerNoPlatform']
                except UserNotFoundException:
                    return messages['WrongName'].format(player_name)
                except StatNameCollectionNotFoundException:
                    return messages['PlayerNoPlatform']
                return None
            else:
                start = time.time()
                first = True
                player_name = ''
                for i in range(0, args_len):
                    if first:
                        player_name = args[i]
                        first = False
                        continue
                    player_name = player_name + ' ' + args[i]
                try:
                    account_id = fortnite_api.lookup(player_name)
                    player_data = fortnite_api.get_stats(account_id)
                    try:
                        async with channel.typing():
                            lifetime_stats = player_data['pc']
                            output_type = 1
                            if user_manager.user_exists(member):
                                output_type = user_manager.get_user_data(member)['output_type']

                            stats_message = Embed(color=Color.blurple())
                            stats_message.set_footer(text='© Luc1412.de',
                                                     icon_url=config_manager.get_config_value('URLs.Footer_Icon_URL'))
                            stats_message.set_author(name=messages['Stats'].format(player_name,
                                                                                   utils.get_displayname('pc')),
                                                     icon_url=config_manager.get_config_value("URLs.Icon_Small_URL"))

                            if output_type is 0:
                                stats_message.add_field(name=messages['Alltime'],
                                                        value=messages['StatsMessage'].format(lifetime_stats.all.score,
                                                                                              lifetime_stats.all.score_per_match,
                                                                                              lifetime_stats.all.minutes_played,
                                                                                              lifetime_stats.all.matches_played,
                                                                                              lifetime_stats.all.wins,
                                                                                              lifetime_stats.all.win_ratio,
                                                                                              lifetime_stats.all.top3,
                                                                                              lifetime_stats.all.top25,
                                                                                              lifetime_stats.all.kills,
                                                                                              lifetime_stats.all.kills_per_game,
                                                                                              lifetime_stats.all.deaths,
                                                                                              lifetime_stats.all.kd),
                                                        inline=True)
                                stats_message.add_field(name='Solo',
                                                        value=messages['StatsMessage'].format(lifetime_stats.solo.score,
                                                                                              lifetime_stats.solo.score_per_match,
                                                                                              lifetime_stats.solo.minutes_played,
                                                                                              lifetime_stats.solo.matches_played,
                                                                                              lifetime_stats.solo.wins,
                                                                                              lifetime_stats.solo.win_ratio,
                                                                                              lifetime_stats.solo.top3,
                                                                                              lifetime_stats.solo.top25,
                                                                                              lifetime_stats.solo.kills,
                                                                                              lifetime_stats.solo.kills_per_game,
                                                                                              lifetime_stats.solo.deaths,
                                                                                              lifetime_stats.solo.kd),
                                                        inline=True)
                                stats_message.add_field(name='Duo',
                                                        value=messages['StatsMessage'].format(lifetime_stats.duo.score,
                                                                                              lifetime_stats.duo.score_per_match,
                                                                                              lifetime_stats.duo.minutes_played,
                                                                                              lifetime_stats.duo.matches_played,
                                                                                              lifetime_stats.duo.wins,
                                                                                              lifetime_stats.duo.win_ratio,
                                                                                              lifetime_stats.duo.top3,
                                                                                              lifetime_stats.duo.top25,
                                                                                              lifetime_stats.duo.kills,
                                                                                              lifetime_stats.duo.kills_per_game,
                                                                                              lifetime_stats.duo.deaths,
                                                                                              lifetime_stats.duo.kd),
                                                        inline=True)
                                stats_message.add_field(name='Squad',
                                                        value=messages['StatsMessage'].format(
                                                            lifetime_stats.squad.score,
                                                            lifetime_stats.squad.score_per_match,
                                                            lifetime_stats.squad.minutes_played,
                                                            lifetime_stats.squad.matches_played,
                                                            lifetime_stats.squad.wins,
                                                            lifetime_stats.squad.win_ratio,
                                                            lifetime_stats.squad.top3,
                                                            lifetime_stats.squad.top25,
                                                            lifetime_stats.squad.kills,
                                                            lifetime_stats.squad.kills_per_game,
                                                            lifetime_stats.squad.deaths,
                                                            lifetime_stats.squad.kd),
                                                        inline=True)
                                try:
                                    await channel.send(embed=stats_message)
                                    end = time.time()
                                    logging_manager.info('Took {} seconds to fetch stats!'
                                                         .format(datetime.timedelta(seconds=end - start)))
                                except discord.Forbidden:
                                    return None
                            elif output_type is 1:
                                print()
                            elif output_type is 3:
                                print()
                    except KeyError:
                        return messages['PlayerNoPlatform']
                except UserNotFoundException:
                    return messages['WrongName'].format(player_name)
                except StatNameCollectionNotFoundException:
                    return messages['PlayerNoPlatform']
                return None
        return None

        # !fn [TimeWindow]
        # !fn <Name> [TimeWindow]
        # !fn xbox <Name> [TimeWindow]
        # !fn ps4 <Name> [TimeWindow]
        # !fn link <Console> <Name>
        # !fn type <Type>
        # !fn map
        # !fn status
        # !fn help
        # !fn info
        # !fn lang <Lang>
        # !fn rdm name
        # !fn rdm loc

        # !fn <Name>                        !fn                 !fn Luc1412
        # !fn <Name> [TimeWindow]    !fn Luc1412 Current
        # !fn [TimeWindow]           !fn Current


# ########################################################
# #################### DEBUG COMMAND #####################
# ########################################################
class FNDebug:

    @staticmethod
    async def ex(member, channel, args):
        if not str(member.id) == '262511457948663809':
            return None
        if len(args) < 1:
            return None
        arg1 = args[0].lower()
        if arg1 == 'guildid':
            await utils.send_temp_message(channel,
                                          'DEBUG',
                                          'Guild ID: **{}**'.format(str(channel.guild.id)),
                                          Color.orange(),
                                          30)
            return None
        elif arg1 == 'roles':
            role_message = ''
            for role in channel.guild.roles:
                role_message = role_message + role.mention + ' ID: ' + role.id + '\n'
            await utils.send_temp_message(channel,
                                          'DEBUG',
                                          role_message,
                                          Color.orange(),
                                          10)
            return None
        elif arg1 == 'status':
            global status_lock
            if status_lock:
                status_lock = False
                activity = Activity(type=ActivityType.listening,
                                    name='{}fn help | {} Server'.format(
                                        config_manager.get_config_value('General.Prefix'),
                                        len(bot.guilds)))
                await bot.change_presence(activity=activity, status=Status.online)
                await utils.send_temp_message(channel,
                                              'DEBUG',
                                              'Updating Presence to normal!',
                                              Color.orange(),
                                              15)
            else:
                if len(args) < 3:
                    return 'Please use **!fndebug status <Type(l,p,w)> <Message>**'
                status_lock = True
                first = True
                status = ''
                for i in range(2, len(args)):
                    if first:
                        status = args[i]
                        first = False
                        continue

                    status = status + ' ' + args[i]

                actv_type = args[1]
                if actv_type == 'l':
                    actv = ActivityType.listening
                elif actv_type == 'w':
                    actv = ActivityType.watching
                else:
                    actv = ActivityType.playing

                activity = Activity(type=actv,
                                    name=status)
                await bot.change_presence(activity=activity, status=Status.online)
                logging_manager.info('Updating Presence to "{}"...'.format(status))
                await utils.send_temp_message(channel,
                                              'DEBUG',
                                              'Updating Presence to "{}"...'.format(status),
                                              Color.orange(),
                                              15)
        elif arg1 == 'restart':
            # TODO Message in Info + Start message! (Stop Command)
            restart_message = discord.Embed(description='Bot reboots in 5 seconds...', color=Color.red())
            await channel.send(embed=restart_message)
            await asyncio.sleep(5)
            sys.exit('Restart')
        return None


# #######################################################
# ################## REGISTER COMMANDS ##################
# #######################################################
commands = {
    'fn': FNCommand(),
    'fndebug': FNDebug()
}


# #######################################################
# ################## COMMAND HANDLER ####################
# #######################################################
@bot.event
async def on_message(message):
    if type(message.channel) is not discord.TextChannel:
        return
    if message.author.bot:
        return
    if message.content.startswith(config_manager.get_config_value('General.Prefix')):
        invoke = message.content[len(config_manager.get_config_value('General.Prefix')):].split(' ')[0].lower()
        args = message.content.split(' ')[1:]
        if commands.__contains__(invoke):
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            except discord.NotFound:
                pass
            error = await commands.get(invoke).ex(message.author, message.channel, args)
            if error is not None:
                messages = lang_manager.get_messages(message.author.guild, 'CommandError')
                if type(messages) is str:
                    messages = 'ERROR'
                await utils.send_temp_message(message.channel,
                                              messages,
                                              '{} {}'.format(message.author.mention, error), Color.red(),
                                              15)
        return

    mentions = message.mentions
    if not mentions.__contains__(bot.user):
        return
    messages = lang_manager.get_messages(message.channel.guild, 'FnCommand')
    channel = message.channel
    try:
        await channel.send(messages['MentionMessage'].format(bot.user.mention))
    except discord.Forbidden:
        return


# #######################################################
# ################### ERROR HANDLING ####################
# #######################################################
@bot.event
async def on_error(event, *args, **kwargs):
    import traceback
    logging_manager.error(traceback.format_exc())

    error_message = discord.Embed(description='```python\n' + traceback.format_exc() + '\n```',
                                  color=Color.from_rgb(194, 54, 22))
    error_message.set_author(name='An error occurred!',
                             icon_url=config_manager.get_config_value('URLs.Icon_Small_URL'))
    format_time = datetime.datetime.fromtimestamp(time.time()).strftime('%d.%m.%Y %H:%M:%S')
    error_message.set_footer(text='© Luc1412.de | ' + format_time,
                             icon_url=config_manager.get_config_value('URLs.Footer_Icon_URL'))
    error_channel = await utils.get_error_channel()
    await error_channel.send(embed=error_message)


@bot.event
async def on_guild_join(guild):
    await utils.update_server_count()
    database_manager.add_guild(guild)
    embed = Embed(color=Color.from_rgb(76, 209, 55),
                  description="Hello I'm <@{}>,\nIf you want to change the language to German use `!fnlang <DE/EN>`.\n"
                              " English is the default language!".format(bot.user.id))
    embed.set_thumbnail(url=config_manager.get_config_value('URLs.Icon_Big_URL'))
    embed.set_author(name='Introduction',
                     icon_url=config_manager.get_config_value('URLs.Icon_Small_URL'))
    embed.set_footer(text='© Luc1412.de',
                     icon_url=config_manager.get_config_value('URLs.Footer_Icon_URL'))
    embed.add_field(name='About the bot',
                    value='Currently I can show you your Fortnite stats, generate you an random location and show you the current Fortnite Map.\n'
                          'You can use `!fn help` to view all available commands. ',
                    inline=False)
    embed.add_field(name='Planed features',
                    value='- Graphical and animated stats\n'
                          '- Suggest me something on my [Discord](https://Luc1412.de/discord) !',
                    inline=False)
    embed.add_field(name='Important Links',
                    value="[Bot Webpage](https://Luc1412.de/easyfortnitestats)\n"
                          "[Developer's Twitter](https://twitter.com/luc141201)\n"
                          "[Support Server](https://discord.gg/Sw5RbXD)",
                    inline=False)
    embed.add_field(name='Support me',
                    value='If you like the bot, you are welcome to support me. I pay monthly for the server on which the bot runs and would be happy about every donation\n'
                          'If you type `!fn donate`, you got more information!\n\n'
                          'You can also support me for free by voting for the bot.\n\n'
                          'Type `!fn vote`')
    for member in guild.members:
        if member.bot:
            continue
        if member.guild_permissions.administrator:
            try:
                await member.send(embed=embed)
            except discord.Forbidden:
                return

    channel = await utils.get_info_channel()
    new_server_message = discord.Embed(description='**Name:** {}\n'
                                                   '**ID:** {}\n'
                                                   '**Region:** {}\n'
                                                   '**User Amount:** {}\n'
                                                   '**Owner:** {}\n'
                                                   '**Exists since:** {}\n'
                                                   '**Is Verified:** {}\n'
                                                   '**Is in VIP Region:** {}\n'
                                                   '**Special Splash:** {}\n'
                                                   '**Has More Emojis:** {}'.format(guild.name,
                                                                                    str(guild.id),
                                                                                    guild.region,
                                                                                    str(guild.member_count),
                                                                                    guild.owner.mention,
                                                                                    guild.created_at,
                                                                                    str(guild.features.__contains__(
                                                                                        'VERIFIED')),
                                                                                    str(guild.features.__contains__(
                                                                                        'VIP_REGIONS')),
                                                                                    guild.splash,
                                                                                    str(guild.features.__contains__(
                                                                                        'MORE_EMOJI'))))
    new_server_message.set_thumbnail(url=guild.icon_url)
    new_server_message.set_author(name='New Server! 🎉',
                                  icon_url=config_manager.get_config_value('URLs.Icon_Small_URL'))
    new_server_message.set_footer(text='© Luc1412.de',
                                  icon_url=config_manager.get_config_value('URLs.Footer_Icon_URL'))
    await channel.send(embed=new_server_message)


@bot.event
async def on_guild_remove(guild):
    await utils.update_server_count()


async def update():
    import asyncio
    while True:

        if not status_lock:
            logging_manager.info('Updating Presence...')
            activity = Activity(type=ActivityType.listening,
                                name='{}fn help | {} Server'.format(
                                    config_manager.get_config_value('General.Prefix'),
                                    len(bot.guilds)))
            await bot.change_presence(activity=activity, status=Status.online)
        stats_manager.set_guild_amount()
        await asyncio.sleep(600)

        if not status_lock:
            logging_manager.info('Updating Presence...')
            activity = Activity(type=ActivityType.listening,
                                name='{}fn help | {} User'.format(
                                    config_manager.get_config_value('General.Prefix'),
                                    stats_manager.get_user_amount()))
            await bot.change_presence(activity=activity, status=Status.online)
        stats_manager.set_guild_amount()
        await asyncio.sleep(600)


@bot.event
async def on_ready():
    bot.loop.create_task(update())
    logging_manager.info('Bot was successfully enabled!')
    await utils.update_server_count()


if __name__ == '__main__':
    bot.run(config_manager.get_config_value('General.Token'))
