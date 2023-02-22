# ⚡ OverFast API
![Python](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/TeKrop/15a234815aa74059953a766a10e92688/raw/python-version.json)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Code Quality](https://github.com/TeKrop/overfast-api/actions/workflows/ruff.yml/badge.svg)](https://github.com/TeKrop/overfast-api/actions/workflows/ruff.yml)
![Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/TeKrop/1362ebafcd51d3f65dae7935b1d322eb/raw/pytest.json)
[![Issues](https://img.shields.io/github/issues/TeKrop/overfast-api)](https://github.com/TeKrop/overfast-api/issues)
[![Documentation](https://img.shields.io/badge/documentation-yes-brightgreen.svg)](https://overfast-api.tekrop.fr)
[![License: MIT](https://img.shields.io/github/license/TeKrop/overfast-api)](https://github.com/TeKrop/overfast-api/blob/master/LICENSE)
![Mockup OverFast API](https://files.tekrop.fr/overfast_api_logo_full_1000.png)

> OverFast API gives data about Overwatch 2 heroes, gamemodes, maps and players statistics by scraping Blizzard pages. Built with **FastAPI** and **Beautiful Soup**, and uses **nginx** as reverse proxy and **Redis** for caching. By using a specific cache system, it minimizes calls to Blizzard pages (which can be very slow), and quickly returns accurate data to users.

## Table of contents
* [✨ Live instance](#-live-instance)
* [💽 Installation](#-installation)
* [🐋 Docker](#-docker)
* [👨‍💻 Technical details](#-technical-details)
* [🛠️ Cache System](#%EF%B8%8F-cache-system)
* [🐍 Architecture](#-architecture)
* [🤝 Contributing](#-contributing)
* [🙏 Credits](#-credits)
* [📝 License](#-license)


## ✨ [Live instance](https://overfast-api.tekrop.fr)

You can see and use a live version of the API here, the root URL being the Redoc documentation : https://overfast-api.tekrop.fr/.

If you want to use the API, and you have the possibility to host your own instance, don't hesitate do it (at least for production environment), in order to not overload the live version i'm hosting.

## 💽 Installation

### Requirements
* Python 3.11
* Poetry
* Docker & Docker Compose (production)

### Install process

- Clone the project
- Create a `config.py` file from the `config.example.py` template file (inside `overfastapi` folder)
- Edit the configuration file to match your needs
- Finally, simply run `poetry install` to install all the dependencies (+ dev dependencies)

### Launch

```
uvicorn overfastapi.main:app --reload
```

## 🐋 Docker

### Standalone (no cache system)
```
cp overfastapi/config.example.py overfastapi/config.py
docker build . -t tekrop/overfast-api:latest
docker run -d -p 80:80 --name overfast-api tekrop/overfast-api
```

### Definitive edition (with cache system)
First, you need to create a dotenv file (`.env`) from the `.env.example` file. You'll need to modify it following your needs in order to configure the volumes used by OverFast API, here are the configuration steps.

- `APP_VOLUME_PATH` will be a folder containing shared data for the app :
    - the app logs folders
    - the configuration file (`config.py`). You need to copy the `overfastapi/config.example.py` file into the folder, default values should suit your needs
    - crontab configurations for background cache update, you just need to copy the `overfast-crontab` file from the repo into your folder

- `REDIS_VOLUME_PATH` will be a folder containing shared data for the Redis server. It will mainly a `dump.rdb` save file whenever the server has been stopped.

- `NGINX_VOLUME_PATH` will be a folder containing shared data for the nginx server. All files can be retrieve in the `nginx` folder of the project :
    - the `ngx_http_redis_module.so` library file, allowing nginx to directly communicate with the redis server
    - the main nginx configuration (`nginx.conf`), modified in order to use the `ngx_http_redis_module` and to define the two backends used (redis and uvicorn)
    - the app configuration file (`overfast-api.conf`), implementing the caching system (call redis backend, then if error call uvicorn backend)

- `APP_PORT` is the port used by the app. Default is `80`.

- Once you set the right values in your dotenv, and you copied all the needed files in the respective folders, you can finally use the docker compose command to build everything and run the app
```
docker-compose up
```

- The server will be running on the port you set (`APP_PORT`).

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
python -m overfastapi.commands.check_and_update_cache
```

#### Check if there is a new hero available, and notify the developer if there is one
```
python -m overfastapi.commands.check_new_hero
```

#### Update test fixtures

Generic command (update heroes, gamemodes and roles)
```
python -m overfastapi.commands.update_test_fixtures
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
python -m pytest --cov=overfastapi --cov-report html
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

### Python (uvicorn) + Redis server (caching) + nginx
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
        Nginx->>Python: Transmit the request to Python server
        Python->>Redis: Make Parser Cache request
        alt Parser Cache is available
            Redis-->>Python: Return Parser Cache
        else
            Redis-->>Python: Return no result
            Python->>Python: Parse HTML page
        end
        Python-->>Nginx: Return API data
        Nginx-->>User: Return API data
    end
```

Using this way (via `docker-compose`), the response will be cached into Redis, and will be sent by nginx directly for the next times without requesting the Python server at all. It's the best performance compromise as nginx is the best for serving static content. A single request can lead to several Parser Cache requests, depending on configured Blizzard pages.

### Python (uvicorn) + Redis server (caching)
```mermaid
sequenceDiagram
    participant User
    User->>Python: Make an API request
    Python->>Redis: Make an API Cache request
    alt API Cache is available
        Redis-->>Python: Return API Cache data
        Python-->>User: Return API Cache data
    else
        Redis-->>Python: Return no result
        Python->>Redis: Make Parser Cache request
        alt Parser Cache is available
            Redis-->>Python: Return Parser Cache
        else
            Redis-->>Python: Return no result
            Python->>Python: Parse HTML page
        end
        Python-->>User: Return API data
    end
```

Using this way (by manually doing it), the response will be cached into Redis, and the cache will be checked by the Python server (`USE_API_CACHE_IN_APP` setting in `config.py` must be set to `True`). It's an acceptable compromise.

### Python (uvicorn) only
```mermaid
sequenceDiagram
    participant User
    User->>Python: Make an API request
    Python-->>User: Return API data after parsing
```
Using this way (only using the image built with the `Dockerfile` alone), there will be no cache at all, and every call will make requests to Blizzard pages. I advise not to use this way unless for debugging.

## 🤝 Contributing

Contributions, issues and feature requests are welcome!

Feel free to check [issues page](https://github.com/TeKrop/overfast-api/issues).


## 🙏 Credits

All maps screenshots hosted by the API are owned by Blizzard. Sources :
- Blizzard Press Center (https://blizzard.gamespress.com)
- Overwatch Wiki (https://overwatch.fandom.com/wiki/)


## 📝 License

Copyright © 2021-2023 [Valentin PORCHET](https://github.com/TeKrop).

This project is [MIT](https://github.com/TeKrop/overfast-api/blob/master/LICENSE) licensed.
