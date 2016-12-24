from django.shortcuts import render

from .service import regions
from .service import RiotService
from .naive_bayes import train_naive_bayes
import os

# Create your views here.

def index(request):

    return render(request, 'home/index.html', {'regions':regions})


def search(request):
    if request.method == 'GET':
        api = RiotService(request.GET['region'])
        summoner_id = api.get_summoner_id(request.GET['summoner'])
        current_match = api.get_current_game(summoner_id)
        data = api.get_data_from_current_match(current_match)
        predict = data['data']
        players = data['players']
        red = []
        blue = []

        clf = train_naive_bayes(os.getcwd()+'/database/matchData')

        probability = clf.predict_proba(predict)[0]
        probability[0] = round(probability[0] * 100, 2)
        probability[1] = round(probability[1] * 100, 2)
        for player in players:
            if player.team == 200:
                red.append(player)
            elif player.team == 100:
                blue.append(player)
        return render(request, 'home/search.html', {'name':request.GET['summoner'], 'region':request.GET['region'], 'regions':regions, 'red':red, 'blue':blue, 'prediction':probability})
    return render(request, 'home/search.html', {'name': 'nie dziala post'})
