import requests as rq
import asyncio
import grequests
import time
from datetime import datetime as dt, timedelta
BASE_URL = ''
#API_KEY = 'RGAPI-64ED5E8D-88A5-479F-88A8-F5C3656EBDBF'
API_KEY = '9c5a2d19-598d-489f-af61-1f24f4115946'

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
    'stats' : 1.3,
    'matchlist' : 2.2,
    'match' : 2.2
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

    def __init__(self, summoner_id, champion_id, team, winrate = 0, total_games = 0, win = None):
        self.summoner_id = summoner_id
        self.champion_id = champion_id
        self.team = team
        self.winrate = winrate
        self.total_games = total_games
        self.win = win



class ServiceException(Exception):

    def __init__(self, error_code):
        self.error_code = error_code

    def __str__(self):
        return self._errors[self.error_code]

    _errors = {
        400 : "Bad request",
        401 : "Unauthorized",
        402 : "Blacklisted key",
        404 : "Game data not found",
        429 : "Too many requests",
        500 : "Internal server error",
        503 : "Service unavailable",
        504 : "Gateway timeout",
    }

def check_response(response):
    if response.status_code in [400, 401, 403, 404, 429, 500, 503, 504]:
        raise ServiceException(response.status_code)
    else: response.raise_for_status()


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
        check_response(request)
        return request.json()

    def create_player_list(self, current_game):
        players = [Player(c['summonerId'], c['championId'], c['teamId']) for c in current_game['participants']]
        return players


    def get_summoner_id(self, summoner_name):
        request = rq.get(
            'https://{region}.api.pvp.net/api/lol/{region}/v{api_v}/summoner/by-name/{summoner}?api_key={api_key}'.format(
                region = self.region,
                api_v = api_version['summoner'],
                summoner = summoner_name,
                api_key = API_KEY)
        )
        check_response(request)
        return request.json()[summoner_name.replace(" ","").lower()]['id']

    async def get_champion_winrate(self, player):
        request = rq.get(
            'https://{region}.api.pvp.net/api/lol/{region}/v{api_v}/stats/by-summoner/{summ_id}/normal?season=SEASON{year}&api_key={api_key}'.format(
                region = self.region,
                api_v = api_version['stats'],
                summ_id = player.summoner_id,
                year = dt.today().year,
                api_key = API_KEY
            )
        )
        check_response(request)
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

    def get_matchlist_by_summoner_id(self, summoner_id):
        request = rq.get(
            'https://{region}.api.pvp.net/api/lol/{region}/v{version}/matchlist/by-summoner/{id}?beginTime={epochTimestamp}&api_key={api_key}'.format(
                region = self.region,
                version = api_version['matchlist'],
                id = summoner_id,
                epochTimestamp = (dt.today() - timedelta(days=5)).strftime('%s'), #picking begin date to start 2 weeks ago and converting to epoch time
                api_key = API_KEY
            )
        )

        check_response(request)
        matches = []
        for match in request.json()['matches']:
            if match['queue'] == 'RANKED_FLEX_SR' or match['queue'] == 'RANKED_SOLO_5x5':
                matches.append(match['matchId'])
        return matches

    def get_match_by_id(self, match_id):
        request = rq.get(
            'https://{region}.api.pvp.net/api/lol/{region}/v{version}/match/{id}?api_key={api_key}'.format(
                region = self.region,
                version = api_version['match'],
                id = match_id,
                api_key = API_KEY
            )
        )

        check_response(request)
        return request.json()

    def get_all_summoners_id_from_match(self, match_id=None, match=None):
        if match_id is None and match is None: pass
        if match is None: match = self.get_match_by_id(match_id)

        s_ids = [p_id['player']['summonerId'] for p_id in match['participantIdentities']]
        c_ids = [p['championId'] for p in match['participants']]

        return s_ids, c_ids


    def create_match_database(self,count = 1000):
        players_id = set()
        matches_id = set()

        match_id = self.get_matchlist_by_summoner_id(self.get_summoner_id('slodkii'))[0]
        players = self.get_all_summoners_id_from_match(match_id)
        m_ids = []
        while len(matches_id) < count:
            time.sleep(1)
            for player_id in players:
                m_ids = self.get_matchlist_by_summoner_id(player_id)
                print(m_ids)
                matches_id.update(m_ids)
                time.sleep(1)
            players =  self.get_all_summoners_id_from_match(m_ids[-1])
        return matches_id



service = RiotService('na')
id = service.get_summoner_id('Dyrus')
print(id)

matches =  service.get_matchlist_by_summoner_id(id)
print(matches)

match = service.get_match_by_id(1858198944)
print(match)

ids = service.get_all_summoners_id_from_match(match_id=matches[0])[0]
print(ids)

matches_ids = service.create_match_database()
matches = []
with open('matchData-NA', 'r') as out:
    for line in out:
        matches.append(int(line))

print(matches[5465])
for i,m_id in enumerate(matches):
    if i > 16:
        break
    match = service.get_match_by_id(m_id)
    time.sleep(4.5)
    blue_team = match['teams'][0]
    b_won = blue_team['winner']
    s_ids, c_ids = service.get_all_summoners_id_from_match(match = match)
    print(b_won,s_ids, c_ids)

# match = service.get_current_game(id)
# print(id)
# print(match)
# player = service.create_player_list(match)
#
# time.sleep(1)
#
# el = asyncio.get_event_loop()
# for p in player:
#     print(p.champion_id,p.summoner_id,p.team, p.winrate, p.total_games)
#
# try:
#     el.run_until_complete(service.get_winrates_for_each_player(player))
# finally:
#     el.close()
#
# for p in player:
#     print(p.champion_id,p.summoner_id,p.team, p.winrate, p.total_games)





