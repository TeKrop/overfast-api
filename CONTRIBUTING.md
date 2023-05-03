# 🤝 OverFast API Contribution Guide

## 📝 Introduction
This guide aims to help you in contributing in OverFast API. The first step for you will be to understand how to technically contribute. In order to do this, you'll have to fork the repo, you can follow the [official GitHub documentation](https://docs.github.com/en/get-started/quickstart/contributing-to-projects) for more details.

As of now, only some specific stuff can easily be updated by anyone, even without any knowledge in Python or FastAPI framework. If I take too much time to update them, don't hesitate to make a PR if you need up-to-date data :
- The CSV file containing some specific heroes statistics, like health, armor and shields
- The CSV file containing the list of maps of the game

## 🦸 Heroes statistics
The CSV file containing heroes statistics data is located in `app/data/heroes_stats.csv`. Data is divided into 4 columns :
- `key` : Key of the hero name, used in URLs of the API (and by Blizzard for their pages)
- `health` : Health of the hero
- `armor` : Armor of the hero, mainly possessed by tanks
- `shields` : Shields of the hero

## 🗺️ Maps list
The CSV file containing maps list is located in `app/data/maps.csv`. Data is divided into 5 columns :
- `key` : Key of the map, used in URLs of the API, and for the name of the corresponding screenshot file
- `name` : Name of the map (in english)
- `gamemodes` : List of gamemodes in which the map is playable by default
- `location` : The location of the map, with the city and country (if relevant)
- `country_code` : Country code of the map location if any. Don't fill this value if not relevant (ex: Horizon Lunar Colony)

When adding a new map in the list, don't forget to also add its corresponding screenshot in the `static/maps` folder. File format must be `jpg`, and the name must be the value of the `key` in the CSV file. To retrieve screenshots, don't hesitate to consult the [Blizzard Press Center](https://blizzard.gamespress.com).

## 🤔 Other contributions
For any other contribution you wish to make, feel free to reach me directly or check [issues page](https://github.com/TeKrop/overfast-api/issues).