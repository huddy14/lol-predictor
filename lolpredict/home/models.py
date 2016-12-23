from django.db import models

# Create your models here.
class ChampionImage(models.Model):
    keys = models.IntegerField()
    url = models.CharField(max_length=60)
