from django.shortcuts import render

from .service import regions
from .service import RiotService


# Create your views here.

def index(request):

    return render(request, 'home/index.html', {'regions':regions})


def search(request):
    if request.method == 'GET':
        api = RiotService(request.GET['region'])
        summoner_id = api.get_summoner_id(request.GET['summoner'])
        current_match = api.get_current_game(summoner_id)
        players = api.create_player_list(current_game=current_match)
        red = []
        blue = []
        for player in players:
            if player.team == 200:
                red.append(player)
            elif player.team == 100:
                blue.append(player)
        return render(request, 'home/search.html', {'name':request.GET['summoner'], 'region':request.GET['region'], 'regions':regions, 'red':red, 'blue':blue})
    return render(request, 'home/search.html', {'name': 'nie dziala post'})
