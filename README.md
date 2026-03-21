# `tg-media-bot`

[English](README.md) | [Русская версия](README.ru.md)

Standalone Telegram bot for browsing and adding movies/series through Radarr and Sonarr, with optional magnet forwarding to qBittorrent.

This repository is self-contained as a bot service. It does not include Radarr, Sonarr, or qBittorrent themselves. Those services must already exist and be reachable from where the bot runs.

## Features

- password-based Telegram authorization
- list downloaded movies from Radarr
- list downloaded series from Sonarr
- search and add movies to Radarr
- search and add series to Sonarr
- optional magnet link forwarding to qBittorrent
- persistent authorized chat storage in `data/authorized_chats.json`

## Requirements

- Python `3.12+` for local runs
- reachable Radarr API
- reachable Sonarr API
- optional reachable qBittorrent Web UI API

If the bot runs in Docker, hostnames in `config.yaml` must resolve from inside the container. When running in the same Docker network, names like `radarr`, `sonarr`, and `qbittorrent` are fine. Otherwise use an IP address or DNS name reachable from the container.

## Quick Start With Docker Compose

This is the main end-user scenario: Radarr, Sonarr, and qBittorrent are already running in Docker Compose, and the bot is added as another service.

1. Create a directory for the bot config and data:

```bash
mkdir -p containers/tg-bot/data
```

2. Create `containers/tg-bot/config.yaml` from `config.example.yaml`:

```bash
cp config.example.yaml containers/tg-bot/config.yaml
```

3. Fill in the real values in the config.

What you need to set:

- `telegram.token` - your bot token from BotFather
- `telegram.password` - the password users must enter on first login
- `telegram.proxy.*` - optional proxy for Telegram Bot API only if direct Telegram access is blocked
- `radarr.server.addr` and `sonarr.server.addr` - Docker Compose service names (`radarr`, `sonarr`) when the bot is on the same network
- `radarr.auth.apikey` and `sonarr.auth.apikey` - API keys from Radarr/Sonarr settings
- `qbittorrent.*` - qBittorrent settings if you want to send magnet links from Telegram
- if you do not need qBittorrent integration, set `qbittorrent.enabled: false`

4. Add the bot service to `docker-compose.yaml`:

```yaml
services:
  tg-bot:
    image: ghcr.io/vint52/tg-media-bot:latest
    container_name: tg-bot
    depends_on: [radarr, sonarr, qbittorrent]
    environment:
      - TG_BOT_CONFIG_PATH=/app/config/config.yaml
      - AUTHORIZED_CHATS_PATH=/app/data/authorized_chats.json
    volumes:
      - ./containers/tg-bot/config.yaml:/app/config/config.yaml:ro
      - ./containers/tg-bot/data:/app/data:rw
    restart: unless-stopped
    networks: [internal]
```

5. Start the container:

```bash
docker compose up -d tg-bot
```

After startup, the bot will create `containers/tg-bot/data/authorized_chats.json` automatically if it does not exist yet.

If your services are in another Compose project, connect the bot to a shared Docker network or use IP addresses/DNS names in `config.yaml` that are reachable from inside the container.

## Configuration

The repository contains a safe example config in `config.example.yaml`.

For Docker Compose from the example above:

```bash
mkdir -p containers/tg-bot/data
cp config.example.yaml containers/tg-bot/config.yaml
```

For a local run from the repository root:

```bash
cp config.example.yaml config.yaml
```

Then replace placeholder values in `config.yaml`.

Minimal Docker Compose config example:

```yaml
telegram:
  token: "0000000000:replace-with-your-telegram-bot-token"
  password: "replace-with-bot-password"
  language: "ru"
  proxy:
    enabled: false
    type: "http"
    host: "127.0.0.1"
    port: 8080
    username: ""
    password: ""

radarr:
  server:
    addr: radarr
    port: 7878
    path: /
    ssl: false
  auth:
    apikey: "replace-with-radarr-api-key"

sonarr:
  server:
    addr: sonarr
    port: 8989
    path: /
    ssl: false
  auth:
    apikey: "replace-with-sonarr-api-key"

qbittorrent:
  enabled: true
  verify_tls: true
  server:
    addr: qbittorrent
    port: 6004
    path: /
    ssl: false
  auth:
    username: "replace-with-qbittorrent-username"
    password: "replace-with-qbittorrent-password"
  options:
    category: "tg"
    tags: []
    savepath: ""
    paused: false
    skip_checking: false
    auto_torrent_management: false
```

Required keys:

- `telegram.token`
- `telegram.password`
- `telegram.language` (`ru` or `en`, optional; if omitted, the bot auto-detects language from Telegram and falls back to `ru`)
- `radarr.server.addr`
- `radarr.server.port`
- `radarr.auth.apikey`
- `sonarr.server.addr`
- `sonarr.server.port`
- `sonarr.auth.apikey`

Optional Telegram proxy section:

- `telegram.proxy.enabled`
- `telegram.proxy.type` (`http`, `socks4`, `socks5`)
- `telegram.proxy.host`
- `telegram.proxy.port`
- `telegram.proxy.username`
- `telegram.proxy.password`

Optional qBittorrent section:

- `qbittorrent.enabled`
- `qbittorrent.verify_tls`
- `qbittorrent.server.addr`
- `qbittorrent.server.port`
- `qbittorrent.server.path`
- `qbittorrent.server.ssl`
- `qbittorrent.auth.username`
- `qbittorrent.auth.password`
- `qbittorrent.options.category`
- `qbittorrent.options.tags`
- `qbittorrent.options.savepath`
- `qbittorrent.options.paused`
- `qbittorrent.options.skip_checking`
- `qbittorrent.options.auto_torrent_management`

Telegram proxy notes:

- The `telegram.proxy` block affects only Telegram Bot API traffic. Radarr, Sonarr, and qBittorrent continue to use direct connections from their own config blocks.
- Supported proxy types in the current stack are `http`, `socks4`, and `socks5`.
- MTProto proxies are not supported in this project because the bot uses `aiogram` with Telegram Bot API over HTTPS, not an MTProto client such as Telethon or Pyrogram.

Runtime paths:

- `TG_BOT_CONFIG_PATH`: path to YAML config file
- `AUTHORIZED_CHATS_PATH`: path to authorized chat storage JSON

Default container paths:

- config: `/app/config/config.yaml`
- data: `/app/data/authorized_chats.json`

## Local Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
TG_BOT_CONFIG_PATH="$PWD/config.yaml" \
AUTHORIZED_CHATS_PATH="$PWD/data/authorized_chats.json" \
python -m bot.main
```

## Docker Build

Build the image from the repository root:

```bash
docker build -t tg-media-bot .
```

## Docker Run

```bash
mkdir -p data
docker run -d \
  --name tg-media-bot \
  --restart unless-stopped \
  -e TG_BOT_CONFIG_PATH=/app/config/config.yaml \
  -e AUTHORIZED_CHATS_PATH=/app/data/authorized_chats.json \
  -v "$(pwd)/config.yaml:/app/config/config.yaml:ro" \
  -v "$(pwd)/data:/app/data" \
  tg-media-bot
```

If Radarr, Sonarr, and qBittorrent are running in another Docker Compose project, connect this container to the same Docker network or use reachable hostnames/IPs in `config.yaml`.

## Use From GHCR

Published image:

```text
ghcr.io/vint52/tg-media-bot:latest
```

Pull and run:

```bash
docker pull ghcr.io/vint52/tg-media-bot:latest
docker run -d \
  --name tg-media-bot \
  --restart unless-stopped \
  -e TG_BOT_CONFIG_PATH=/app/config/config.yaml \
  -e AUTHORIZED_CHATS_PATH=/app/data/authorized_chats.json \
  -v "$(pwd)/config.yaml:/app/config/config.yaml:ro" \
  -v "$(pwd)/data:/app/data" \
  ghcr.io/vint52/tg-media-bot:latest
```

## Publish To GHCR

This repository includes GitHub Actions workflow `.github/workflows/docker-publish.yml`.

It publishes to:

```text
ghcr.io/<repository-owner>/tg-media-bot
```

Automatic publish triggers:

- push to `main`
- push to `master`
- git tags matching `v*`
- manual run via `workflow_dispatch`

Manual publish from a local machine:

```bash
echo "<github-token>" | docker login ghcr.io -u <github-username> --password-stdin
docker build -t ghcr.io/<github-owner>/tg-media-bot:latest .
docker push ghcr.io/<github-owner>/tg-media-bot:latest
```

Your token needs permission to write packages.

## Telegram Auth Flow

1. Send `/start` to the bot.
2. Enter the password from `telegram.password`.
3. After successful authorization, the bot stores your `chat_id` in `AUTHORIZED_CHATS_PATH`.
4. You can then browse and search movies or series through the bot buttons, and if `qbittorrent.enabled: true`, also send magnet links.

The bot interface language can be forced through `telegram.language` in the config file. If the key is omitted, the bot uses the Telegram user's `language_code` and falls back to `ru`.

## qBittorrent Magnet Flow

When `qbittorrent.enabled: true`, the bot accepts magnet links in two ways:

1. Press `add magnet` and send a magnet link.
2. Or send a `magnet:?` link directly after authorization.

The bot forwards the magnet URL to qBittorrent through the Web UI API.

## Troubleshooting

- `Config not found`: check `TG_BOT_CONFIG_PATH` and the mounted file path.
- `Missing ...` config errors: fill in placeholder values in `config.yaml`.
- Bot starts but cannot reach services: verify hostnames, ports, Docker networking, and API keys.
- qBittorrent actions fail: confirm Web UI access, credentials, and `qbittorrent.enabled: true`.
- No Telegram access after restart: check that `AUTHORIZED_CHATS_PATH` points to a writable persistent volume.
