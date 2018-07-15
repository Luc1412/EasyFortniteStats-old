# Created by Luc1412
# This Bot is NOT affiliated with EpicGames or Fortnite! I'm only a player.
import asyncio
import json

import discord
from discord import Color, Embed, ActivityType, Forbidden, TextChannel, NotFound

bot = discord.Client()


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


class DatabaseManager:

    def __init__(self):
        self.client = None
        self.database = None
        if bool(config_manager.get_config_value('CollectStats')):
            self.connect()

    def connect(self):
        from pymongo import MongoClient
        self.client = MongoClient(config_manager.get_config_value('MongoDb.ConnectURI'))
        self.database = self.client[config_manager.get_config_value('MongoDb.Database')]

        self.setup()

    def setup(self):
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
        self.database['Stats'].insert_one(requests)
        self.database['Stats'].insert_one(servers)

    def is_setup(self):
        db_filter = {
            'name': 'Requests'
        }
        return self.database['Stats'].find_one(db_filter) is not None

    def guild_exists(self, guild):
        db_filter = {
            'id': guild.id
        }
        return self.database['Language'].find_one(db_filter) is not None

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


class LangManager:

    def __init__(self):
        import codecs

        self.german_messages = json.load(codecs.open('DE_de.json', 'r', 'utf-8-sig'))
        self.english_messages = json.load(codecs.open('EN_us.json', 'r', 'utf-8-sig'))

    def add_guild(self, guild):
        if database_manager.guild_exists(guild):
            return
        guild_doc = {
            'guild_id': str(guild.id),
            'lang': 'EN'
        }
        database_manager.add_document('Language', guild_doc)

    def get_messages(self, guild):
        try:
            lang = database_manager.get_document('Language', 'guild_id', str(guild.id))['lang']
        except TypeError:
            self.add_guild(guild)
            return '__**Error!**__ Guild has been added to Database. Please repeat the Command!'
        if lang == 'DE':
            return self.german_messages
        else:
            return self.english_messages

    def set_guild_lang(self, guild, lang):
        database_manager.set_document('Language', 'guild_id', str(guild.id), 'lang', lang)


lang_manager = LangManager()


class StatsManager:

    def add_request(self):
        old = database_manager.get_document('Stats', 'name', 'Requests')['score']
        new = old + 1
        database_manager.set_document('Stats', 'name', 'Requests', 'score', new)

    def set_guild_amount(self):
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

    def get_guild_max(self):
        return database_manager.get_document('Stats', 'name', 'Guilds')['highscore']

    def get_guild_amount(self):
        return database_manager.get_document('Stats', 'name', 'Guilds')['score']

    def get_requests(self):
        return database_manager.get_document('Stats', 'name', 'Requests')['score']


stats_manager = StatsManager()


class Utils:
    URL = 'https://api.fortnitetracker.com/v1/profile/'
    HEADER = {}

    def get_data(self, platform, username):
        import requests
        req = requests.get(self.URL + platform + '/' + username, headers=self.HEADER)
        if bool(config_manager.get_config_value('CollectStats')):
            stats_manager.add_request()
        return req.text

    def set_api_key(self):
        self.HEADER.__setitem__('TRN-Api-Key', config_manager.get_config_value('General.APIKey'))

    async def send_temp_message(self, channel, title, content, color, time):
        embed = Embed(description=content, color=color)
        embed.set_author(name=title,
                         icon_url='http://cloud.luc1412.de/index.php/s/m2b6zH2keMwTC8b/preview')
        embed.set_footer(text='© Luc1412.de', icon_url='http://cloud.luc1412.de/index.php/s/io8XkWmKfXooR83/preview')
        try:
            message = await channel.send(embed=embed)
        except Forbidden:
            return
        import asyncio
        await asyncio.sleep(time)
        await message.delete()


utils = Utils()


class FnStatsCommand:

    async def ex(self, user, channel, args):
        messages = lang_manager.get_messages(channel.guild)['FnStatsCommand']
        if len(args) < 2 or len(args) > 4:
            return messages['Usage'].replace('&n', '\n')
        platform = args[0].lower()
        if platform != 'pc' and platform != 'xbox' and platform != 'ps4':
            return messages['Platform']
        name = args[1].replace('%', ' ')
        player_data = utils.get_data(platform.replace('xbox', 'xbl').replace('ps4', 'psn'), name)
        import json
        player_data = json.loads(player_data)
        if player_data.__contains__('error'):
            return messages['PlayerNA']

        embed = discord.Embed(color=Color.blurple())
        embed.set_footer(text='© Luc1412.de',
                         icon_url='http://cloud.luc1412.de/index.php/s/io8XkWmKfXooR83/preview')

        if len(args) is 2:
            embed.set_author(name=messages['LTStats'].format(player_data['epicUserHandle'],
                                                             player_data['platformNameLong']),
                             icon_url='http://cloud.luc1412.de/index.php/s/m2b6zH2keMwTC8b/preview')

            lifetime_stats = player_data['lifeTimeStats']

            games_played = lifetime_stats[7]['value']
            wins = lifetime_stats[8]['value']
            deaths = int(games_played) - int(wins)
            embed.add_field(name='Score', value=lifetime_stats[6]['value'], inline=True)
            embed.add_field(name=messages['PlayedGames'], value=games_played, inline=True)
            embed.add_field(name=messages['WonGames'],
                            value="{} `[{}]`".format(wins, lifetime_stats[9]['value']), inline=True)
            embed.add_field(name='Top 3', value=lifetime_stats[2]['value'], inline=True)
            embed.add_field(name='Top 25', value=lifetime_stats[5]['value'], inline=True)
            embed.add_field(name='Kills', value=lifetime_stats[10]['value'], inline=True)
            embed.add_field(name=messages['Deaths'], value=str(deaths), inline=True)
            embed.add_field(name='K/D', value=lifetime_stats[11]['value'], inline=True)
        else:
            modus = args[2].lower()

            if modus == 'solo':
                modus_id = 'p2'
                modus_name = 'Solo '
            elif modus == 'duo':
                modus_id = 'p10'
                modus_name = 'Duo '
            elif modus == 'squad':
                modus_id = 'p9'
                modus_name = 'Squad '
            else:
                return messages['Modus']

            if len(args) == 4:
                season = args[3].lower()
                if season == '3':
                    modus_id = 'prior_' + modus_id
                    modus_name = modus_name + 'Season 3'
                    if not player_data['stats'].__contains__('prior_p2') or not player_data['stats'].__contains__(
                            'prior_p9') or not player_data['stats'].__contains__('prior_p10'):
                        return messages['PlayerNS']
                elif season == '4':
                    modus_id = 'curr_' + modus_id
                    modus_name = modus_name + 'Season 4'
                    if not player_data['stats'].__contains__('curr_p2') or not player_data['stats'].__contains__(
                            'curr_p9') or not player_data['stats'].__contains__('curr_p10'):
                        return messages['PlayerNS']
                elif season == 'all':
                    modus_name = modus_name + 'Lifetime'
                else:
                    return messages['Season']

            embed.set_author(name=modus_name + messages['CustomStats'].format(player_data['epicUserHandle']),
                             icon_url='http://cloud.luc1412.de/index.php/s/m2b6zH2keMwTC8b/preview')

            stats = player_data['stats'][modus_id]

            games_played = stats['matches']['value']
            wins = stats['top1']['value']
            deaths = int(games_played) - int(wins)

            embed.add_field(name='Score', value=stats['score']['displayValue'], inline=True)
            if stats['score'].__contains__('rank'):
                embed.add_field(name=messages['Rank'], value=stats['score']['rank'], inline=True)
            embed.add_field(name='TRN Rating(bit.ly/trn-rating)', value=stats['score']['displayValue'], inline=True)
            embed.add_field(name=messages['PlayedGames'], value=stats['matches']['displayValue'], inline=True)
            embed.add_field(name=messages['WonGames'],
                            value="{} `[{}]`".format(stats['top1']['displayValue'],
                                                     stats['top1']['percentile'] + '%' if player_data.__contains__(
                                                         'percentile') else '0%'),
                            inline=True)
            embed.add_field(name=messages['KG'], value=stats['kpg']['displayValue'], inline=True)
            embed.add_field(name=messages['SG'], value=stats['scorePerMatch']['displayValue'], inline=True)
            embed.add_field(name='Top 3', value=stats['top3']['displayValue'], inline=True)
            embed.add_field(name='Top 10', value=stats['top10']['displayValue'], inline=True)
            embed.add_field(name='Top 25', value=stats['top25']['displayValue'], inline=True)
            embed.add_field(name='Kills', value=stats['kills']['displayValue'], inline=True)
            embed.add_field(name=messages['Deaths'], value=str(deaths), inline=True)
            embed.add_field(name='K/D', value=stats['kd']['displayValue'], inline=True)
        try:
            await channel.send(embed=embed)
        except Forbidden:
            return None
        return None


class FNHelpCommandCommand:

    async def ex(self, member, channel, args):
        messages = lang_manager.get_messages(channel.guild)['FNHelpCommand']
        embed = Embed(color=Color.from_rgb(103, 211, 242))
        embed.set_thumbnail(url="http://cloud.luc1412.de/index.php/s/AgB45pbLxtSsmm2/preview")
        embed.set_author(name=messages['Head'],
                         icon_url='http://cloud.luc1412.de/index.php/s/m2b6zH2keMwTC8b/preview')
        embed.set_footer(text='© Luc1412.de',
                         icon_url='http://cloud.luc1412.de/index.php/s/io8XkWmKfXooR83/preview')
        embed.add_field(name='Commands:',
                        value=messages['NormalHelp'],
                        inline=False)
        if member.guild_permissions.administrator:
            embed.add_field(name='Admin Commands:', value=messages['AdminHelp'], inline=False)
        if member.id == 262511457948663809:
            embed.add_field(name='Operator Commands',
                            value='`!fnannounce <Text>` **-** Send a message to all guild administrators!')
        try:
            await member.send(embed=embed)
        except Forbidden:
            return lang_manager.get_messages(channel.guild)['DMFail'].format(member.mention)
        return None


class FnRdmName:
    names = {
        1: 'Junk Junction',
        2: 'Anarchy Acres',
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
        18: 'Moisty Mire',
        19: 'Flush Factory',
        20: 'Lucky Landing'
    }

    async def ex(self, member, channel, args):
        messages = lang_manager.get_messages(channel.guild)['FnRdmNameCommand']
        from random import randint
        rdm_number = randint(1, 20)
        location = self.names.get(rdm_number)
        embed = Embed(color=Color.from_rgb(randint(0, 255), randint(0, 255), randint(0, 255)),
                      description=messages['Out'].format(location))
        await channel.send(embed=embed)


class FNInfoCommand:

    async def ex(self, member, channel, args):
        messages = lang_manager.get_messages(channel.guild)['FNInfoCommand']
        embed = Embed(color=Color.dark_gold(),
                      description=messages['Desc'].format('EasyFortniteStats',
                                                          bot.get_user(262511457948663809).name + '#' + bot.get_user(
                                                              262511457948663809).discriminator,
                                                          '[@luc141201](https://twitter.com/luc141201)',
                                                          'https://Luc1412.de',
                                                          1.0,
                                                          len(bot.guilds),
                                                          stats_manager.get_guild_max(),
                                                          stats_manager.get_requests()))
        embed.set_thumbnail(url="http://cloud.luc1412.de/index.php/s/AgB45pbLxtSsmm2/preview")
        embed.set_author(name=messages['Head'],
                         icon_url='http://cloud.luc1412.de/index.php/s/m2b6zH2keMwTC8b/preview')
        try:
            await channel.send(embed=embed)
        except Forbidden:
            return None


class FNLangCommand:

    async def ex(self, member, channel, args):
        messages = lang_manager.get_messages(channel.guild)['FNLangCommand']
        if not member.guild_permissions.administrator:
            return None
        if len(args) is not 1:
            return messages['Usage']
        lang = args[0].upper()
        if not lang == "DE":
            if not lang == "EN":
                return messages['Usage']
        lang_manager.set_guild_lang(channel.guild, lang)
        messages = lang_manager.get_messages(channel.guild)['FNLangCommand']
        await utils.send_temp_message(channel,
                                      messages['SuccessHead'],
                                      messages['SuccessDesc'].format('English' if lang == 'EN' else 'Deutsch'),
                                      Color.from_rgb(76, 209, 55),
                                      15)
        return None


# !fn
# !fn setname <Name> - Set a user name!
# !fn help - Get Help page


commands = {
    'fnstats': FnStatsCommand(),
    'fnhelp': FNHelpCommandCommand(),
    'fninfo': FNInfoCommand(),
    'fnlang': FNLangCommand(),
    'fnrdmname': FnRdmName()
}


@bot.event
async def on_message(message):
    if type(message.channel) is not TextChannel:
        return
    if message.author == bot.user:
        if message.channel.guild.id == 443432012095946753:
            if message.content == 'update':
                activity = discord.Activity(type=ActivityType.listening,
                                            name='{}fnhelp |{}'.format(
                                                config_manager.get_config_value('General.Prefix'),
                                                len(bot.guilds)))
                await bot.change_presence(activity=activity)
                stats_manager.set_guild_amount()
    if message.author.bot:
        return
    if message.content.startswith(config_manager.get_config_value('General.Prefix')):
        invoke = message.content[len(config_manager.get_config_value('General.Prefix')):].split(' ')[0]
        args = message.content.split(' ')[1:]
        if commands.__contains__(invoke.lower()):
            try:
                await message.delete()
            except Forbidden:
                pass
            except NotFound:
                pass
            error = await commands.get(invoke).ex(message.author, message.channel, args)
            if error is not None:
                await utils.send_temp_message(message.channel,
                                              lang_manager.get_messages(message.author.guild)['CommandError'],
                                              '{} {}'.format(message.author.mention, error), Color.red(),
                                              15)


@bot.event
async def on_guild_join(guild):
    lang_manager.add_guild(guild)
    embed = Embed(color=Color.from_rgb(76, 209, 55),
                  description="Hello I'm <@{}>,\nIf you want to change the language to German use `!fnlang <DE/EN>`.\n English is the default language!".format(
                      bot.user.id))
    embed.set_thumbnail(url="http://cloud.luc1412.de/index.php/s/AgB45pbLxtSsmm2/preview")
    embed.set_author(name='Introduction',
                     icon_url='http://cloud.luc1412.de/index.php/s/m2b6zH2keMwTC8b/preview')
    embed.set_footer(text='© Luc1412.de',
                     icon_url='http://cloud.luc1412.de/index.php/s/io8XkWmKfXooR83/preview')
    embed.add_field(name='About Me',
                    value='Currently I can show you your Fortnite stats. You can use `!fnhelp` to view all available commands. You, as an Guild Administrator, can see all commands. Guild members can only see the commands they can use.',
                    inline=False)
    embed.add_field(name='Planed features',
                    value='- A random name command (Displays a random name to drop, like TiltedTowers or DustyDevot)\n- A random location command(Like the random name command, but a little bit more advanced)\n- Display Map\n- Suggest me something on my [Discord](https://Luc1412.de/discord) !',
                    inline=False)
    embed.add_field(name='Important Links',
                    value="[Bot Webpage](https://Luc1412.de/easyfortnitestats)\n[Developer's Twitter](https://twitter.com/luc141201)\n[Discord Server](https://Luc1412.de/discord)",
                    inline=False)
    for member in guild.members:
        if member.bot:
            continue
        if member.guild_permissions.administrator:
            try:
                await member.send(embed=embed)
            except Forbidden:
                return


@asyncio.coroutine
def update():
    while True:
        activity = discord.Activity(type=ActivityType.listening,
                                    name='{}fnhelp | {} Servers'.format(
                                        config_manager.get_config_value('General.Prefix'),
                                        len(bot.guilds)))
        yield from bot.change_presence(activity=activity)
        yield from asyncio.sleep(10000)


@bot.event
async def on_ready():
    if bool(config_manager.get_config_value('CollectStats')):
        task = asyncio.Task(update())
    print('Bot was successfully enabled!')
    print(bot.latency)


if __name__ == '__main__':
    utils.set_api_key()
    print(utils.HEADER)
    bot.run(config_manager.get_config_value('General.Token'))

# https://discordapp.com/api/oauth2/authorize?client_id=443303689411887104&permissions=8&scope=bot
# Passwd: XteazI8xIPrJybFK

# class FNAnnounceCommand:

# async def ex(self, member, channel, args):
# if not member.id == 262511457948663809:
# return
# if len(args) < 1:
# return 'Please use !fnstats <Text>'
# text = ''
# for word in args:
# if text == '':
# text = word
# continue
# print(word + str(type(word)))
# text = text + ' ' + word

# embed = Embed(color=Color.gold(), description=text)
# embed.set_author(name='EasyFortniteStats Announcement',
# icon_url='http://cloud.luc1412.de/index.php/s/m2b6zH2keMwTC8b/preview')
# embed.set_footer(text='© Luc1412.de',
# icon_url='http://cloud.luc1412.de/index.php/s/io8XkWmKfXooR83/preview')

# for member in bot.get_all_members():
# if member.guild_permissions.administrator:
# print(member.name)
# if member.id == 262511457948663809:
# await member.send(embed=embed)

# return None
