# ⚡ OverFast API
![Python](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/TeKrop/15a234815aa74059953a766a10e92688/raw/python-version.json)
[![Build Status](https://github.com/TeKrop/overfast-api/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/TeKrop/overfast-api/actions/workflows/build.yml)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=TeKrop_overfast-api&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=TeKrop_overfast-api)
![Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/TeKrop/1362ebafcd51d3f65dae7935b1d322eb/raw/pytest.json)
[![Issues](https://img.shields.io/github/issues/TeKrop/overfast-api)](https://github.com/TeKrop/overfast-api/issues)
[![Documentation](https://img.shields.io/badge/documentation-yes-brightgreen.svg)](https://overfast-api.tekrop.fr)
[![License: MIT](https://img.shields.io/github/license/TeKrop/overfast-api)](https://github.com/TeKrop/overfast-api/blob/master/LICENSE)
![Mockup OverFast API](https://files.tekrop.fr/overfast_api_logo_full_1000.png)

> OverFast API gives data about Overwatch 2 heroes, gamemodes, maps and players statistics by scraping Blizzard pages. Built with **FastAPI** and **Beautiful Soup**, and uses **nginx** as reverse proxy and **Redis** for caching. By using a specific cache system, it minimizes calls to Blizzard pages (which can be very slow), and quickly returns accurate data to users.

## Table of contents
* [✨ Live instance](#-live-instance)
* [💽 Dev environment](#-dev-environment)
* [🐋 Docker](#-docker)
* [👨‍💻 Technical details](#-technical-details)
* [🛠️ Cache System](#%EF%B8%8F-cache-system)
* [🐍 Architecture](#-architecture)
* [🤝 Contributing](#-contributing)
* [🚀 Community projects](#-community-projects)
* [🙏 Credits](#-credits)
* [📝 License](#-license)


## ✨ [Live instance](https://overfast-api.tekrop.fr)

You can see and use a live version of the API here, the root URL being the Redoc documentation : https://overfast-api.tekrop.fr/

You can also consult the Swagger UI documentation, useful for directly trying API calls : https://overfast-api.tekrop.fr/docs

## 💽 Dev environment

### Requirements
* 🐍 Python 3.11
* 🪶 Poetry

### Install

- Clone the project
- Rename `.env.example` into `.env`, and edit the configuration in order to match your needs
- Run `poetry install` to install all the dependencies (+ dev dependencies)

### Launch

```
uvicorn app.main:app --reload
```

## 🐋 Docker

### Standalone (no cache system)
```
docker build . -t tekrop/overfast-api:latest
docker run -d -p 80:80 --name overfast-api tekrop/overfast-api
```

### Definitive edition (with cache system)
First, you need to create a dotenv file (`.env`) from the `.env.example` file. You'll need to modify it following your needs in order to configure the volumes used by OverFast API, here are the configuration steps.

#### Generic settings
- `APP_PORT` is the port used by the app container. Default is `80`.
- `APP_BASE_URL` is used for the links exposed in some endpoints (players search and maps listing)
You shouldn't need to modify any other generic setting, but in case you want to check their utility, be sure to check the docstrings in the `app/config.py` file.

#### `APP_VOLUME_PATH`
It's a folder containing shared data for the app : logs, settings file (`.env`) and crontab configurations for background cache update. You just need to :

- Create the folder on your side
- Copy the `.env` file you previously created into your folder
- Copy the `overfast-crontab` file from the repo (`scripts` folder) into your folder

#### `REDIS_VOLUME_PATH`
It's a folder containing shared data for the Redis server. It will mainly contain a `dump.rdb` save file whenever the server has been stopped at least once. Be sure to create

#### `NGINX_VOLUME_PATH`
It's a folder containing shared data for the nginx server. You'll need to copy some files from the `scripts/nginx` folder of the repo into your folder :
- the `ngx_http_redis_module.so` library file, allowing nginx to directly communicate with the redis server
- the main nginx configuration (`nginx.conf`), modified in order to use the `ngx_http_redis_module` and to define the two backends used (`redis` and `app`)
- the app configuration file (`overfast-api.conf`), implementing the caching system (call `redis` backend, then if error call `app` backend)

#### Final steps
Once you set the right values in your dotenv, and you copied all the needed files in the respective folders, you can finally use the docker compose command to build everything and run the app
```
docker-compose up
```
The server will be running on the port you set (`APP_PORT`).

## 👨‍💻 Technical details

### Computed statistics values

In players career statistics, several conversions are made for convenience :
- all **duration values** are converted into **seconds** (integer)
- **percent values** are exposed as **integers** instead of a string with a percent symbol
- integer and float string representations are converted into the concerned type

### Commands

The following commands are either used :
- In an automated way, for checking if cache values need to be updated, or if a new hero has been published on Blizzard pages (the code needs to be updated if this is the case)
- In a manual way, in order to update the test fixtures used in the test suite

#### Check and update Redis cache which needs to be updated
```
python -m app.commands.check_and_update_cache
```

#### Check if there is a new hero available, and notify the developer if there is one
```
python -m app.commands.check_new_hero
```

#### Update test fixtures

Generic command (update heroes, gamemodes and roles)
```
python -m app.commands.update_test_fixtures
```

Help message (with different options)
```
usage: update_test_fixtures.py [-h] [-He] [-Ho] [-P]

Update test data fixtures by retrieving Blizzard pages directly. By default, all the tests data will be updated.

options:
  -h, --help     show this help message and exit
  -He, --heroes  update heroes test data
  -Ho, --home    update home test data (gamemodes, roles)
  -P, --players  update players test data
```

### Code Quality
The code quality is checked using the `ruff` command. I'm also using the `isort` utility for imports ordering, and `black` to enforce PEP-8 convention on my code. To check the quality of the code, you just have to run the following command :

```
ruff .
```

### Testing
The code has been tested using (a lot of) unit testing, except some rare parts which are not relevant to test. There are tests on the parsers classes, the common classes, but also on the commands (run in CLI) and the API views (using FastAPI TestClient class).

Running tests (simple)
```
python -m pytest
```
Running tests (with coverage)
```
python -m pytest --cov=app --cov-report html
```

## 🛠️ Cache System

### API Cache and Parser Cache

OverFast API includes a cache stored on a **Redis** server, and divided in two parts :
* **API Cache** : a very high level cache, linking URIs (cache key) to raw JSON data. When first doing a request, if a cache is available, the JSON data is returned as-is by the **nginx** server. The cached values are stored with an arbitrary TTL (time to leave) parameter depending on the called route.
* **Parser Cache** : a specific cache for the parser system of the OverFast API. When an HTML Blizzard page is parsed, the parsing result (JSON object) is stored, in order to minimize calls to Blizzard when doing a request with filters. The value is refreshed in the background before its expiration.

Here is the list of all TTL values configured for API Cache :
* Heroes list : 1 day
* Hero specific data : 1 day
* Roles list : 1 day
* Gamemodes list : 1 day
* Maps list : 1 day
* Players career : 1 hour
* Players search : 1 hour

### Refresh-Ahead cache system

In order to reduce the number of requests to Blizzard that API users can make, a Refresh-Ahead cache system has been implemented.

When a user requests its player career page, it will be slow for the first call (2-3s in total), as it's retrieving data from Blizzard. Then, the computed data will be stored in the Parser Cache (which will be refreshed in background), and the final data will be stored in API Cache (only created when a user makes a request).

Thanks to this system, user requests on the same career page will be very fast for all the next times.

## 🐍 Architecture
You can run the project in several ways, though I would advise the first one for better user experience.

### App (uvicorn) + Redis server (caching) + nginx
```mermaid
sequenceDiagram
    participant User
    User->>Nginx: Make an API request
    Nginx->>Redis: Make an API Cache request
    alt API Cache is available
        Redis-->>Nginx: Return API Cache data
        Nginx-->>User: Return API Cache data
    else
        Redis-->>Nginx: Return no result
        Nginx->>App: Transmit the request to Python server
        App->>Redis: Make Parser Cache request
        alt Parser Cache is available
            Redis-->>App: Return Parser Cache
        else
            Redis-->>App: Return no result
            App->>App: Parse HTML page
        end
        App-->>Nginx: Return API data
        Nginx-->>User: Return API data
    end
```

Using this way (via `docker-compose`), the response will be cached into Redis, and will be sent by nginx directly for the next times without requesting the Python server at all. It's the best performance compromise as nginx is the best for serving static content. A single request can lead to several Parser Cache requests, depending on configured Blizzard pages.

### App (uvicorn) + Redis server (caching)
```mermaid
sequenceDiagram
    participant User
    User->>App: Make an API request
    App->>Redis: Make an API Cache request
    alt API Cache is available
        Redis-->>App: Return API Cache data
        App-->>User: Return API Cache data
    else
        Redis-->>App: Return no result
        App->>Redis: Make Parser Cache request
        alt Parser Cache is available
            Redis-->>App: Return Parser Cache
        else
            Redis-->>App: Return no result
            App->>App: Parse HTML page
        end
        App-->>User: Return API data
    end
```

Using this way (by manually doing it), the response will be cached into Redis, and the cache will be checked by the Python server (`USE_API_CACHE_IN_APP` setting in `config.py` must be set to `True`). It's an acceptable compromise, but keep in mind that cache retrieval is ~100 times slower than the previous solution (tested with [wrk](https://github.com/wg/wrk)).

### App (uvicorn) only
```mermaid
sequenceDiagram
    participant User
    User->>App: Make an API request
    App-->>User: Return API data after parsing
```
Using this way (only using the image built with the `Dockerfile` alone), there will be no cache at all, and every call will make requests to Blizzard pages. I advise not to use this way unless for debugging.

## 🤝 Contributing

Contributions, issues and feature requests are welcome!

Feel free to check [issues page](https://github.com/TeKrop/overfast-api/issues).

## 🚀 Community projects

Here is a list of projects which are currently using OverFast API as a data source. You're using it in one of your projects ? Feel free to reach me by e-mail, send me a link of your project (either website URL or public git repository), and I will add it in the list :)

- Overfast API client (https://github.com/Sipixer/overfast-api-client)
- ...

## 🙏 Credits

All maps screenshots hosted by the API are owned by Blizzard. Sources :
- Blizzard Press Center (https://blizzard.gamespress.com)
- Overwatch Wiki (https://overwatch.fandom.com/wiki/)


## 📝 License

Copyright © 2021-2023 [Valentin PORCHET](https://github.com/TeKrop).

This project is [MIT](https://github.com/TeKrop/overfast-api/blob/master/LICENSE) licensed.
