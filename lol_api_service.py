import requests as rq
import asyncio
import time
from datetime import datetime as dt
BASE_URL = ''
API_KEY = 'RGAPI-64ED5E8D-88A5-479F-88A8-F5C3656EBDBF'

#regions
BRAZIL = 'br'
EUROPE_NORDIC_EAST = 'eune'
NORTH_AMERICA = 'na'
EUROPE_WEST = 'euw'
KOREA = 'kr'
RUSSIA = 'ru'

#newest api versions as for 22.11.16
api_version = {
    'current-game' : 1.0,
    'summoner' : 1.4,
    'champion' : 1.2,
    'stats' : 1.3
}

# platforms ids
platforms = {
    BRAZIL: 'BR1',
    EUROPE_NORDIC_EAST: 'EUN1',
    EUROPE_WEST: 'EUW1',
    NORTH_AMERICA: 'NA1',
    RUSSIA: 'RU',
}

class Player:

    def __init__(self, summoner_id, champion_id, team, winrate = 0, total_games = 0):
        self.summoner_id = summoner_id
        self.champion_id = champion_id
        self.team = team
        self.winrate = winrate
        self.total_games = total_games

class RiotService:

    def __init__(self, region):
        self.region = region

    def get_current_game(self, summoner_id):
        request = rq.get(
            'https://{region}.api.pvp.net/observer-mode/rest/consumer/getSpectatorGameInfo/{platform}/{player_id}?api_key={api_key}'.format(
                region = self.region,
                platform = platforms[self.region],
                player_id = summoner_id,
                api_key = API_KEY)
        )
        return  request.json()

    def create_player_list(self, current_game):
        champions = [Player(c['summonerId'], c['championId'], c['teamId']) for c in current_game['participants']]
        return champions


    def get_summoner_id(self, summoner_name):
        request = rq.get(
            'https://{region}.api.pvp.net/api/lol/{region}/v{api_v}/summoner/by-name/{summoner}?api_key={api_key}'.format(
                region = self.region,
                api_v = api_version['summoner'],
                summoner = summoner_name,
                api_key = API_KEY)
        )
        return request.json()[summoner_name.replace(" ","").lower()]['id']

    async def get_champion_winrate(self, player):
        request = rq.get(
            'https://{region}.api.pvp.net/api/lol/{region}/v{api_v}/stats/by-summoner/{summ_id}/ranked?season=SEASON{year}&api_key={api_key}'.format(
                region = self.region,
                api_v = api_version['stats'],
                summ_id = player.summoner_id,
                year = 2015,#dt.today().year,
                api_key = API_KEY
            )
        )
        champions =  request.json()['champions']
        if champions is not None:
            for champion in champions:
                if champion['id'] == player.champion_id:
                    print(champion)
                    player.winrate, player.total_games = self.calculate_winrate(champion)
                    return
        return

    def calculate_winrate(self, champion_info):
        print(champion_info)
        print(champion_info['stats']['totalSessionsWon'])
        total_won = champion_info['stats']['totalSessionsWon']
        total = total_won + champion_info['stats']['totalSessionsLost']

        print(total, total_won)

        winrate = total_won / total
        return winrate, total

    async def get_winrates_for_each_player(self, players):
        winrates = [self.get_champion_winrate(p) for p in players]
        await asyncio.wait(winrates)
        print('winrates obtained')




service = RiotService('eune')
id = service.get_summoner_id('Dj Bialy')
match = service.get_current_game(id)
print(id)
print(match)
player = service.create_player_list(match)

el = asyncio.get_event_loop()
for p in player:
    print(p.champion_id,p.summoner_id,p.team, p.winrate, p.total_games)

try:
    el.run_until_complete(service.get_winrates_for_each_player(player))
finally:
    el.close()

for p in player:
    print(p.champion_id,p.summoner_id,p.team, p.winrate, p.total_games)





