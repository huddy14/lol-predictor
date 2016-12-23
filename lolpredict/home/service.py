import requests as rq
import asyncio
import grequests
import random
import time
from datetime import datetime as dt, timedelta
import csv

BASE_URL = ''
# API_KEY = 'RGAPI-64ED5E8D-88A5-479F-88A8-F5C3656EBDBF'
API_KEY = '9c5a2d19-598d-489f-af61-1f24f4115946'

# regions
BRAZIL = 'br'
EUROPE_NORDIC_EAST = 'eune'
NORTH_AMERICA = 'na'
EUROPE_WEST = 'euw'
KOREA = 'kr'
RUSSIA = 'ru'

regions = ['br', 'eune', 'na', 'euw', 'kr', 'ru']

# newest api versions as for 22.11.16
api_version = {
    'current-game': 1.0,
    'summoner': 1.4,
    'champion': 1.2,
    'stats': 1.3,
    'matchlist': 2.2,
    'match': 2.2,
    'static-data': 1.2
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
    def __init__(self, summoner_id=None, champion_id=None, team=None, winrate=0, total_games=0, win=None, lane=None,
                 role=None):
        self.summoner_id = summoner_id
        self.champion_id = champion_id
        self.team = team
        self.winrate = winrate
        self.total_games = total_games
        self.win = win
        self.lane = lane
        self.role = role

    def __str__(self):
        return


class Match:
    def __init__(self):
        # blue team stats
        self.bt_stats = []
        # red team stats
        self.rt_stats = []
        # winner
        self.winner = 0


class ServiceException(Exception):
    """ Custom exception class to map the API server errors
        And provide useful messages on what went wrong
    """

    def __init__(self, error_code):
        self.error_code = error_code

    def __str__(self):
        return self._errors[self.error_code]

    _errors = {
        400: "Bad request",
        401: "Unauthorized",
        402: "Blacklisted key",
        404: "Game data not found",
        429: "Too many requests",
        500: "Internal server error",
        503: "Service unavailable",
        504: "Gateway timeout",
    }


def check_response(response):
    """ Method is invoked in each of API calls to check if API errors occured
    """
    if response.status_code in [400, 401, 403, 404, 429, 500, 503, 504]:
        raise ServiceException(response.status_code)
    else:
        response.raise_for_status()


class RiotService:
    """ Class that provides a set of methods to communicate with Riot API service
        Region needs to be provided when initializing

    """

    def __init__(self, region):
        self.region = region

    def get_current_game(self, summoner_id):
        """ gets current match for specified id and returns id as json object
            if player is not in the game will throw exception 404 game data not found

        """
        request = rq.get(
            'https://{region}.api.pvp.net/observer-mode/rest/consumer/getSpectatorGameInfo/{platform}/{player_id}?api_key={api_key}'.format(
                region=self.region,
                platform=platforms[self.region],
                player_id=summoner_id,
                api_key=API_KEY)
        )
        check_response(request)
        return request.json()

    def create_player_list(self, current_game):
        """ creates a player list out of a custom match
            returns an array of custom Player objects with summonerdId, championId and teamId populated

        """
        players = [Player(c['summonerId'], c['championId'], c['teamId']) for c in current_game['participants']]
        return players

    def get_summoner_id(self, summoner_name):
        """ returns summoner_id given summoner name"""
        request = rq.get(
            'https://{region}.api.pvp.net/api/lol/{region}/v{api_v}/summoner/by-name/{summoner}?api_key={api_key}'.format(
                region=self.region,
                api_v=api_version['summoner'],
                summoner=summoner_name,
                api_key=API_KEY)
        )
        check_response(request)
        return request.json()[summoner_name.replace(" ", "").lower()]['id']

    def get_champion_winrate(self, summoner_id, champion_id):
        """ returns a win ratio and total games played for specified summoner and champion

        """
        request = rq.get(
            'https://{region}.api.pvp.net/api/lol/{region}/v{api_v}/stats/by-summoner/{summ_id}/ranked?season=SEASON{year}&api_key={api_key}'
                .format(
                region=self.region,
                api_v=api_version['stats'],
                summ_id=summoner_id,
                year=dt.today().year,
                api_key=API_KEY
            )
        )
        try:
            check_response(request)
            champions = request.json()['champions']
            if champions is not None:
                for champion in champions:
                    if champion['id'] == champion_id:
                        total_won = champion['stats']['totalSessionsWon']
                        total = total_won + champion['stats']['totalSessionsLost']

                        winrate = total_won / total
                        return [winrate, total]
            return 0, 0
        except ServiceException:
            return 0, 0

    async def get_winrates_for_each_player(self, players):
        winrates = [self.get_champion_winrate(p) for p in players]
        await asyncio.wait(winrates)
        print('winrates obtained')

    def get_matchlist_by_summoner_id(self, summoner_id):
        """ returns a list of match ids from ranked solo queue for a specified summoner id
            games are not older than 14 days

        """
        request = rq.get(
            'https://{region}.api.pvp.net/api/lol/{region}/v{version}/matchlist/by-summoner/{id}?beginTime={epochTimestamp}&api_key={api_key}'.format(
                region=self.region,
                version=api_version['matchlist'],
                id=summoner_id,
                epochTimestamp=(dt.today() - timedelta(days=14)).strftime('%s'),
                # picking begin date to start 2 weeks ago and converting to epoch time
                api_key=API_KEY
            )
        )

        check_response(request)
        matches = []
        for match in request.json()['matches']:
            if match['queue'] == 'RANKED_SOLO_5x5':
                matches.append(match['matchId'])
        return matches

    def get_match_by_id(self, match_id):
        """ returns match information in json formatt given a specific match id

        """
        request = rq.get(
            'https://{region}.api.pvp.net/api/lol/{region}/v{version}/match/{id}?api_key={api_key}'.format(
                region=self.region,
                version=api_version['match'],
                id=match_id,
                api_key=API_KEY
            )
        )
        print(self.region, request)
        check_response(request)
        return request.json()

    def get_summs_and_champs_from_match(self, match_id=None, match=None):
        """ getting list of all summoners and champions from a particular match"""
        if match_id is None: pass
        if match is None: match = self.get_match_by_id(match_id)

        s_ids = [p_id['player']['summonerId'] for p_id in match['participantIdentities']]
        c_ids = [p['championId'] for p in match['participants']]

        return s_ids, c_ids

    def create_match_database(self, summoner_name, count=1000):
        """ creates a list of unique match ids given a summoner name as a seed
            it looks out a match, generate summoner id lists and looks up thier matches
            if the match id is unique its than added to match_ids list
            this steps are repeated until the match_ids length reaches the specified count value

        """
        match_ids = set()

        match_id = self.get_matchlist_by_summoner_id(self.get_summoner_id(summoner_name))[0]
        players = self.get_summs_and_champs_from_match(match_id)
        m_ids = []
        while len(match_ids) < count:
            time.sleep(1)
            for player_id in players:
                m_ids = self.get_matchlist_by_summoner_id(player_id)
                print(m_ids)
                match_ids.update(m_ids)
                time.sleep(1)
            players = self.get_summs_and_champs_from_match(m_ids[-1])

        # save matches id to file
        with open('matchIds', 'w') as out:
            for id in match_ids:
                out.write(str(id) + '\n')
        return match_ids

    def get_data_from_match(self, match):
        # table returns champId, winRate, totalGames, team (x10 fro each player) and winner team
        data = []
        winner_set = False
        for p, pid in zip(match['participants'], match['participantIdentities']):
            if not winner_set:
                if p['stats']['winner'] and p['teamId'] == 100:
                    winner = 0
                else:
                    winner = 1
                winner_set = True

            data.append(p['championId'])
            winrate, total = self.get_champion_winrate(pid['player']['summonerId'], p['championId'])
            # not to exceed call limits
            time.sleep(1.2)
            data.append(winrate)
            data.append(total)
            data.append(p['teamId'])

        data.append(winner)
        print(data)
        return data

    def get_champions_id_name_dict(self):
        """ populates a dictionary with key: champion id and value: champion name"""

        request = rq.get(
            'https://global.api.pvp.net/api/lol/static-data/{region}/v{version}/champion?champData=image&api_key={api_key}'.format(
                region=self.region,
                version=api_version['static-data'],
                api_key=API_KEY
            )
        )
        check_response(request)
        id_name = {}
        ids = []
        for champ in request.json()['data'].keys():
            c = request.json()['data'][champ]
            ids.append(c['id'])
            print(c['id'], c['key'])
            id_name[c['id']] = c['key']

        return {'dict': id_name, 'ids': ids}

    def create_analysis_file(self):
        with open('matchIds', 'r') as out:

            with open('matchData', 'w') as file:
                writer = csv.writer(file)
                writer.writerow(create_csv_header())
                for i, line in enumerate(out):
                    print(line)
                    if line != '' and line is not None:
                        match = self.get_match_by_id(int(line))
                        data = self.get_data_from_match(match)
                        print(data)
                        writer.writerow(data)
                    if (i > 200): break

    def create_analysis_file1(self, ids):
        with open('matchData', 'w') as file:
            writer = csv.writer(file)
            writer.writerow(create_csv_header())
            size = len(ids) - 1
            for i in range(50000):
                match = []
                for j in range(10):
                    match.append(ids[random.randint(0, size)])
                    match.append(random.random())
                    match.append(random.randint(0,250))
                    if j < 5:
                        match.append(100)
                    else:
                        match.append(200)
                match.append(random.randint(0, 1))
                writer.writerow(match)

def create_csv_header():
    header = []
    for i in range(1, 11):
        header.append('ChampId' + str(i))
        header.append('WinRation' + str(i))
        header.append('TotalMatches' + str(i))
        header.append('Team' + str(i))
    header.append('Winner')
    return header;


print(create_csv_header())
service1 = RiotService('na')
#service1.create_analysis_file()

ids = service1.get_champions_id_name_dict()['ids']
service1.create_analysis_file1(ids)

def create_mock_data(ids):
    size = len(ids) - 1

    final = []
    for i in range(10):
        match = []
        for j in range(10):
            match.append(ids[random.randint(0, size)])
            match.append(random.random())
            match.append(random.randint(250))
            if j < 5:
                match.append(100)
            else:
                match.append(200)
        match.append(random.randint(0, 1))
        final.append(match)

# print(keys)
# print(keys[99])
# #matches_ids = service.create_match_database('Dyrus')
# matches = []
# with open('matchIds', 'r') as out:
#     for line in out:
#         matches.append(int(line))
#
# print(matches[5465])
#
# match = service.get_match_by_id(matches[3])
# service.get_data_from_match(match)

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
