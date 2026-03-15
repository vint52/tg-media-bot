# `tg-media-bot`

[English](README.md) | [Русская версия](README.ru.md)

Отдельный Telegram-бот для просмотра и добавления фильмов/сериалов через Radarr и Sonarr с опциональной отправкой magnet-ссылок в qBittorrent.

Этот репозиторий содержит только сам сервис бота. В него не входят Radarr, Sonarr и qBittorrent. Эти сервисы должны быть уже развернуты и доступны из окружения, где запускается бот.

## Возможности

- авторизация в Telegram по паролю
- просмотр загруженных фильмов из Radarr
- просмотр загруженных сериалов из Sonarr
- поиск и добавление фильмов в Radarr
- поиск и добавление сериалов в Sonarr
- опциональная отправка magnet-ссылок в qBittorrent
- постоянное хранение авторизованных чатов в `data/authorized_chats.json`

## Требования

- Python `3.12+` для локального запуска
- доступный API Radarr
- доступный API Sonarr
- опционально доступный Web UI API qBittorrent

Если бот запускается в Docker, хосты в `config.yaml` должны резолвиться изнутри контейнера. Если все сервисы находятся в одной Docker-сети, подойдут имена вроде `radarr`, `sonarr` и `qbittorrent`. В остальных случаях укажите IP-адрес или DNS-имя, доступные из контейнера.

## Быстрый старт через Docker Compose

Ниже показан основной пользовательский сценарий: Radarr, Sonarr и qBittorrent уже работают в Docker Compose, а бот подключается к ним как отдельный сервис.

1. Создайте каталог для конфига и данных бота:

```bash
mkdir -p containers/tg-bot/data
```

2. Создайте `containers/tg-bot/config.yaml` на основе `config.example.yaml`:

```bash
cp config.example.yaml containers/tg-bot/config.yaml
```

3. Укажите в конфиге реальные значения.

Что нужно заполнить:

- `telegram.token` - токен бота от BotFather
- `telegram.password` - пароль, который будут вводить пользователи при первом входе
- `radarr.server.addr` и `sonarr.server.addr` - имена сервисов в Docker Compose (`radarr`, `sonarr`), если бот находится в той же сети
- `radarr.auth.apikey` и `sonarr.auth.apikey` - API-ключи из настроек Radarr/Sonarr
- `qbittorrent.*` - параметры qBittorrent, если хотите отправлять magnet-ссылки из Telegram
- если qBittorrent не нужен, установите `qbittorrent.enabled: false`
4. Добавьте сервис бота в `docker-compose.yaml`:

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

5. Запустите контейнер:

```bash
docker compose up -d tg-bot
```

После запуска бот автоматически создаст файл `containers/tg-bot/data/authorized_chats.json`, если его еще нет.

Если ваши сервисы находятся в другом Compose-проекте, подключите бот к общей Docker-сети или укажите в `config.yaml` IP-адреса/DNS-имена, доступные из контейнера.

## Конфигурация

В репозитории уже есть безопасный пример конфига в `config.example.yaml`.

Для Docker Compose из примера выше:

```bash
mkdir -p containers/tg-bot/data
cp config.example.yaml containers/tg-bot/config.yaml
```

Для локального запуска из корня репозитория:

```bash
cp config.example.yaml config.yaml
```

Затем замените значения-заглушки в `config.yaml`.

Минимальный пример конфига для Docker Compose:

```yaml
telegram:
  token: "0000000000:replace-with-your-telegram-bot-token"
  password: "replace-with-bot-password"
  language: "ru"

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

Обязательные ключи:

- `telegram.token`
- `telegram.password`
- `telegram.language` (`ru` или `en`, необязательно; если ключ отсутствует, бот автоматически определяет язык по Telegram и использует `ru` как запасной вариант)
- `radarr.server.addr`
- `radarr.server.port`
- `radarr.auth.apikey`
- `sonarr.server.addr`
- `sonarr.server.port`
- `sonarr.auth.apikey`

Опциональный раздел qBittorrent:

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

Пути окружения во время выполнения:

- `TG_BOT_CONFIG_PATH`: путь к YAML-конфигу
- `AUTHORIZED_CHATS_PATH`: путь к JSON-файлу с авторизованными чатами

Пути по умолчанию внутри контейнера:

- конфиг: `/app/config/config.yaml`
- данные: `/app/data/authorized_chats.json`

## Локальный запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
TG_BOT_CONFIG_PATH="$PWD/config.yaml" \
AUTHORIZED_CHATS_PATH="$PWD/data/authorized_chats.json" \
python -m bot.main
```

## Сборка Docker-образа

Соберите образ из корня репозитория:

```bash
docker build -t tg-media-bot .
```

## Запуск в Docker

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

Если Radarr, Sonarr и qBittorrent работают в другом Docker Compose проекте, подключите этот контейнер к той же Docker-сети или используйте в `config.yaml` хосты/IP-адреса, доступные из контейнера.

## Использование образа из GHCR

Готовый опубликованный образ:

```text
ghcr.io/vint52/tg-media-bot:latest
```

Скачать и запустить:

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

## Публикация в GHCR

В репозитории уже есть workflow GitHub Actions: `.github/workflows/docker-publish.yml`.

Он публикует образ в:

```text
ghcr.io/<repository-owner>/tg-media-bot
```

Автоматические триггеры публикации:

- push в `main`
- push в `master`
- git-теги по шаблону `v*`
- ручной запуск через `workflow_dispatch`

Ручная публикация с локальной машины:

```bash
echo "<github-token>" | docker login ghcr.io -u <github-username> --password-stdin
docker build -t ghcr.io/<github-owner>/tg-media-bot:latest .
docker push ghcr.io/<github-owner>/tg-media-bot:latest
```

У токена должно быть разрешение на запись пакетов.

## Авторизация в Telegram

1. Отправьте боту `/start`.
2. Введите пароль из `telegram.password`.
3. После успешной авторизации бот сохранит ваш `chat_id` в `AUTHORIZED_CHATS_PATH`.
4. После этого можно искать фильмы и сериалы через кнопки бота, а при включенном `qbittorrent.enabled: true` еще и отправлять magnet-ссылки.

Язык интерфейса бота можно принудительно задать через `telegram.language` в конфиге. Если ключ отсутствует, бот использует `language_code` пользователя Telegram и при необходимости переключается на `ru`.

## Работа с magnet-ссылками через qBittorrent

Когда `qbittorrent.enabled: true`, бот принимает magnet-ссылки двумя способами:

1. Нажмите `добавить magnet` и отправьте magnet-ссылку.
2. Или просто отправьте ссылку `magnet:?` сразу после авторизации.

Бот передаст URL magnet-ссылки в qBittorrent через Web UI API.

## Устранение неполадок

- `Config not found`: проверьте `TG_BOT_CONFIG_PATH` и путь к смонтированному файлу.
- Ошибки вида `Missing ...` в конфиге: замените значения-заглушки в `config.yaml`.
- Бот запускается, но не может достучаться до сервисов: проверьте хосты, порты, Docker-сеть и API-ключи.
- Действия с qBittorrent не работают: проверьте доступность Web UI, учетные данные и `qbittorrent.enabled: true`.
- После перезапуска пропадает доступ в Telegram: проверьте, что `AUTHORIZED_CHATS_PATH` указывает на постоянный том с правом записи.
