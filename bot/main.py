from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

import requests
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from bot.config import AppConfig, load_config
from bot.qbittorrent_client import QBittorrentClient
from bot.radarr_client import RadarrClient
from bot.sonarr_client import SonarrClient
from bot.storage import AuthorizedChatsStorage


@dataclass
class AppContext:
    config: AppConfig
    storage: AuthorizedChatsStorage
    radarr_client: RadarrClient
    sonarr_client: SonarrClient
    qbittorrent_client: QBittorrentClient | None
    awaiting_password: set[int]
    awaiting_movie_query: set[int]
    awaiting_series_query: set[int]
    awaiting_magnet_link: set[int]
    movie_search_state: dict[int, "MovieSearchSession"]
    series_search_state: dict[int, "SeriesSearchSession"]


@dataclass
class MovieSearchSession:
    query: str
    results: list[dict]
    offset: int = 0


@dataclass
class SeriesSearchSession:
    query: str
    results: list[dict]
    offset: int = 0


MOVIE_SEARCH_PAGE_SIZE = 5
SERIES_SEARCH_PAGE_SIZE = 5
MAGNET_LINK_RE = re.compile(r"magnet:\?[^\s]+", re.IGNORECASE)

TRANSLATIONS = {
    "ru": {
        "button_all_series": "Все сериалы",
        "button_all_movies": "Все фильмы",
        "button_add_series": "добавить сериал",
        "button_add_movie": "добавить фильм",
        "button_add_magnet": "добавить magnet",
        "button_download": "Скачать",
        "button_more_options": "Еще варианты",
        "untitled": "Без названия",
        "rating_prefix": "Рейтинг",
        "qbittorrent_not_configured": "qBittorrent пока не настроен. Заполните раздел qbittorrent в конфиге и включите его.",
        "magnet_forward_failed": "Не удалось передать magnet-ссылку в qBittorrent.",
        "magnet_sent": "Magnet-ссылка отправлена в qBittorrent.",
        "found_options_for_query": "Нашел варианты по запросу: {query}",
        "not_all_results_shown": "Показаны не все результаты.",
        "all_results_shown": "Это все найденные варианты.",
        "already_authorized": "Вы уже авторизованы. Доступ к боту открыт.",
        "enter_password": "Введите пароль для доступа к боту.",
        "help_text": "/start - начать авторизацию\n/status - статус подключения сервисов (для авторизованных)\nИли просто отправьте magnet-ссылку после авторизации.",
        "access_denied": "Нет доступа. Используйте /start и введите пароль.",
        "qbittorrent_not_configured_short": "не настроен",
        "status_text": "Бот активен.\nRadarr: {radarr}\nSonarr: {sonarr}\nqBittorrent: {qbittorrent}",
        "series_fetch_failed": "Не удалось получить список сериалов из Sonarr.",
        "no_series_downloaded": "Скачанных сериалов пока нет.",
        "downloaded_series": "Скачанные сериалы:",
        "movies_fetch_failed": "Не удалось получить список фильмов из Radarr.",
        "no_movies_downloaded": "Скачанных фильмов пока нет.",
        "downloaded_movies": "Скачанные фильмы:",
        "enter_movie_title": "Введите название фильма для поиска.",
        "enter_series_title": "Введите название сериала для поиска.",
        "send_magnet_link": "Отправьте magnet-ссылку для добавления в qBittorrent.",
        "active_search_not_found": "Активный поиск не найден.",
        "no_more_options": "Больше вариантов нет.",
        "no_access_short": "Нет доступа.",
        "invalid_button_data": "Некорректные данные кнопки.",
        "selected_option_not_found": "Не удалось найти выбранный вариант.",
        "movie_add_failed": "Не удалось добавить фильм в Radarr.",
        "movie_added": "Фильм «{title}» добавлен в очередь на скачивание. После успешной загрузки пришлю уведомление.",
        "series_add_failed": "Не удалось добавить сериал в Sonarr.",
        "series_added": "Сериал «{title}» добавлен в очередь на скачивание. После успешной загрузки пришлю уведомление.",
        "added_short": "Добавлено",
        "password_correct": "Пароль верный. Доступ открыт.",
        "password_incorrect": "Неверный пароль. Попробуйте еще раз.",
        "invalid_magnet_link": "Нужна корректная magnet-ссылка, начинающаяся с magnet:?.",
        "enter_series_search_text": "Введите текст для поиска сериала.",
        "sonarr_search_failed": "Не удалось выполнить поиск в Sonarr.",
        "nothing_found": "Ничего не найдено. Попробуйте другое название.",
        "enter_movie_search_text": "Введите текст для поиска фильма.",
        "radarr_search_failed": "Не удалось выполнить поиск в Radarr.",
        "unknown_command": "Команда не распознана. Используйте /help.",
    },
    "en": {
        "button_all_series": "All series",
        "button_all_movies": "All movies",
        "button_add_series": "add series",
        "button_add_movie": "add movie",
        "button_add_magnet": "add magnet",
        "button_download": "Download",
        "button_more_options": "More results",
        "untitled": "Untitled",
        "rating_prefix": "Rating",
        "qbittorrent_not_configured": "qBittorrent is not configured yet. Fill in the qbittorrent section in the config and enable it.",
        "magnet_forward_failed": "Failed to forward the magnet link to qBittorrent.",
        "magnet_sent": "Magnet link has been sent to qBittorrent.",
        "found_options_for_query": "Found results for query: {query}",
        "not_all_results_shown": "Not all results are shown.",
        "all_results_shown": "These are all found results.",
        "already_authorized": "You are already authorized. Bot access is open.",
        "enter_password": "Enter the password to access the bot.",
        "help_text": "/start - begin authorization\n/status - service connection status (for authorized users)\nOr just send a magnet link after authorization.",
        "access_denied": "Access denied. Use /start and enter the password.",
        "qbittorrent_not_configured_short": "not configured",
        "status_text": "Bot is active.\nRadarr: {radarr}\nSonarr: {sonarr}\nqBittorrent: {qbittorrent}",
        "series_fetch_failed": "Failed to get the series list from Sonarr.",
        "no_series_downloaded": "There are no downloaded series yet.",
        "downloaded_series": "Downloaded series:",
        "movies_fetch_failed": "Failed to get the movie list from Radarr.",
        "no_movies_downloaded": "There are no downloaded movies yet.",
        "downloaded_movies": "Downloaded movies:",
        "enter_movie_title": "Enter a movie title to search for.",
        "enter_series_title": "Enter a series title to search for.",
        "send_magnet_link": "Send a magnet link to add it to qBittorrent.",
        "active_search_not_found": "No active search found.",
        "no_more_options": "There are no more results.",
        "no_access_short": "Access denied.",
        "invalid_button_data": "Invalid button data.",
        "selected_option_not_found": "Could not find the selected result.",
        "movie_add_failed": "Failed to add the movie to Radarr.",
        "movie_added": "Movie \"{title}\" has been added to the download queue. I will notify you after the download succeeds.",
        "series_add_failed": "Failed to add the series to Sonarr.",
        "series_added": "Series \"{title}\" has been added to the download queue. I will notify you after the download succeeds.",
        "added_short": "Added",
        "password_correct": "Password is correct. Access granted.",
        "password_incorrect": "Incorrect password. Try again.",
        "invalid_magnet_link": "A valid magnet link starting with magnet:? is required.",
        "enter_series_search_text": "Enter text to search for a series.",
        "sonarr_search_failed": "Failed to search in Sonarr.",
        "nothing_found": "Nothing was found. Try a different title.",
        "enter_movie_search_text": "Enter text to search for a movie.",
        "radarr_search_failed": "Failed to search in Radarr.",
        "unknown_command": "Command not recognized. Use /help.",
    },
}


def _translate(language: str, key: str, **kwargs: object) -> str:
    template = TRANSLATIONS[language][key]
    return template.format(**kwargs)


def _resolve_language(configured_language: str | None, user_language_code: str | None) -> str:
    if configured_language in TRANSLATIONS:
        return configured_language

    normalized = (user_language_code or "").strip().lower()
    if normalized.startswith("ru"):
        return "ru"
    if normalized.startswith("en"):
        return "en"
    return "ru"


def _main_menu_keyboard(language: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=_translate(language, "button_all_series")),
                KeyboardButton(text=_translate(language, "button_all_movies")),
            ],
            [
                KeyboardButton(text=_translate(language, "button_add_series")),
                KeyboardButton(text=_translate(language, "button_add_movie")),
            ],
            [KeyboardButton(text=_translate(language, "button_add_magnet"))],
        ],
        resize_keyboard=True,
    )


def _build_dispatcher(context: AppContext) -> Dispatcher:
    dp = Dispatcher()

    def _user_language_code(message: Message | None = None, callback: CallbackQuery | None = None) -> str | None:
        if message is not None and message.from_user is not None:
            return message.from_user.language_code
        if callback is not None and callback.from_user is not None:
            return callback.from_user.language_code
        return None

    def _language_for_message(message: Message) -> str:
        return _resolve_language(context.config.telegram.language, _user_language_code(message=message))

    def _language_for_callback(callback: CallbackQuery) -> str:
        return _resolve_language(context.config.telegram.language, _user_language_code(callback=callback))

    def _t(language: str, key: str, **kwargs: object) -> str:
        return _translate(language, key, **kwargs)

    def _reset_pending_inputs(chat_id: int) -> None:
        context.awaiting_movie_query.discard(chat_id)
        context.awaiting_series_query.discard(chat_id)
        context.awaiting_magnet_link.discard(chat_id)

    def _extract_magnet_link(message_text: str) -> str | None:
        match = MAGNET_LINK_RE.search(message_text)
        if not match:
            return None
        return match.group(0)

    async def _submit_magnet_link(message: Message, magnet_link: str, language: str) -> None:
        if context.qbittorrent_client is None:
            await message.answer(_t(language, "qbittorrent_not_configured"))
            return

        try:
            context.qbittorrent_client.add_magnet(magnet_link)
        except ValueError as exc:
            await message.answer(str(exc))
            return
        except requests.RequestException:
            await message.answer(_t(language, "magnet_forward_failed"))
            return

        await message.answer(_t(language, "magnet_sent"))

    def _movie_title(movie: dict, language: str) -> str:
        title = str(movie.get("title", "")).strip()
        if title:
            return title
        return _t(language, "untitled")

    def _movie_year(movie: dict) -> str:
        year = movie.get("year")
        if year in (None, ""):
            return "n/a"
        return str(year)

    def _movie_poster_url(movie: dict) -> str | None:
        images = movie.get("images")
        if not isinstance(images, list):
            return None

        for image in images:
            if not isinstance(image, dict):
                continue
            if str(image.get("coverType", "")).lower() != "poster":
                continue

            remote_url = str(image.get("remoteUrl", "")).strip()
            if remote_url:
                return remote_url
            local_url = str(image.get("url", "")).strip()
            if local_url:
                return local_url

        return None

    def _movie_rating_line(movie: dict, language: str) -> str:
        ratings = movie.get("ratings")
        if not isinstance(ratings, dict):
            return ""

        def _extract(source: str) -> str | None:
            raw = ratings.get(source)
            if not isinstance(raw, dict):
                return None
            value = raw.get("value")
            if value in (None, "", 0):
                return None
            try:
                return f"{float(value):.1f}"
            except (TypeError, ValueError):
                return None

        parts: list[str] = []
        imdb = _extract("imdb")
        if imdb:
            parts.append(f"IMDb {imdb}")
        tmdb = _extract("tmdb")
        if tmdb:
            parts.append(f"TMDB {tmdb}")
        rotten = _extract("rottenTomatoes")
        if rotten:
            parts.append(f"RT {rotten}")
        metacritic = _extract("metacritic")
        if metacritic:
            parts.append(f"MC {metacritic}")

        if not parts:
            return ""
        return f"{_t(language, 'rating_prefix')}: " + " | ".join(parts)

    def _series_title(series: dict, language: str) -> str:
        title = str(series.get("title", "")).strip()
        if title:
            return title
        return _t(language, "untitled")

    def _series_year(series: dict) -> str:
        year = series.get("year")
        if year in (None, ""):
            return "n/a"
        return str(year)

    def _series_poster_url(series: dict) -> str | None:
        images = series.get("images")
        if not isinstance(images, list):
            return None

        for image in images:
            if not isinstance(image, dict):
                continue
            if str(image.get("coverType", "")).lower() != "poster":
                continue

            remote_url = str(image.get("remoteUrl", "")).strip()
            if remote_url:
                return remote_url
            local_url = str(image.get("url", "")).strip()
            if local_url:
                return local_url

        return None

    def _series_rating_line(series: dict, language: str) -> str:
        ratings = series.get("ratings")
        if not isinstance(ratings, dict):
            return ""

        def _extract(source: str) -> str | None:
            raw = ratings.get(source)
            if not isinstance(raw, dict):
                return None
            value = raw.get("value")
            if value in (None, "", 0):
                return None
            try:
                return f"{float(value):.1f}"
            except (TypeError, ValueError):
                return None

        parts: list[str] = []
        imdb = _extract("imdb")
        if imdb:
            parts.append(f"IMDb {imdb}")
        tmdb = _extract("tmdb")
        if tmdb:
            parts.append(f"TMDB {tmdb}")
        rotten = _extract("rottenTomatoes")
        if rotten:
            parts.append(f"RT {rotten}")
        metacritic = _extract("metacritic")
        if metacritic:
            parts.append(f"MC {metacritic}")

        if not parts:
            return ""
        return f"{_t(language, 'rating_prefix')}: " + " | ".join(parts)

    async def _send_movie_results_page(message: Message, session: MovieSearchSession, language: str) -> None:
        start = session.offset
        end = min(start + MOVIE_SEARCH_PAGE_SIZE, len(session.results))
        page_movies = session.results[start:end]

        if start == 0:
            await message.answer(_t(language, "found_options_for_query", query=session.query))

        for index, movie in enumerate(page_movies, start=start + 1):
            tmdb_id = int(movie.get("tmdbId", 0) or 0)
            card_text = f"{index}. {_movie_title(movie, language)} ({_movie_year(movie)})"
            rating_line = _movie_rating_line(movie, language)
            if rating_line:
                card_text = f"{card_text}\n{rating_line}"
            markup: InlineKeyboardMarkup | None = None
            if tmdb_id > 0:
                markup = InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(
                            text=_t(language, "button_download"),
                            callback_data=f"movie_add:{tmdb_id}",
                        )
                    ]]
                )

            poster_url = _movie_poster_url(movie)
            if poster_url:
                try:
                    await message.answer_photo(photo=poster_url, caption=card_text, reply_markup=markup)
                    continue
                except Exception:
                    # Если Telegram не принимает URL постера, отправляем текстовый вариант.
                    pass
            await message.answer(card_text, reply_markup=markup)

        if end < len(session.results):
            await message.answer(
                _t(language, "not_all_results_shown"),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text=_t(language, "button_more_options"), callback_data="movie_more")]
                    ]
                ),
            )
        else:
            await message.answer(_t(language, "all_results_shown"))

        session.offset = end

    def _find_movie_by_tmdb(chat_id: int, tmdb_id: int) -> dict | None:
        session = context.movie_search_state.get(chat_id)
        if not session:
            return None

        for movie in session.results:
            if int(movie.get("tmdbId", 0) or 0) == tmdb_id:
                return movie
        return None

    async def _send_series_results_page(message: Message, session: SeriesSearchSession, language: str) -> None:
        start = session.offset
        end = min(start + SERIES_SEARCH_PAGE_SIZE, len(session.results))
        page_series = session.results[start:end]

        if start == 0:
            await message.answer(_t(language, "found_options_for_query", query=session.query))

        for index, series in enumerate(page_series, start=start + 1):
            tvdb_id = int(series.get("tvdbId", 0) or 0)
            card_text = f"{index}. {_series_title(series, language)} ({_series_year(series)})"
            rating_line = _series_rating_line(series, language)
            if rating_line:
                card_text = f"{card_text}\n{rating_line}"
            markup: InlineKeyboardMarkup | None = None
            if tvdb_id > 0:
                markup = InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(
                            text=_t(language, "button_download"),
                            callback_data=f"series_add:{tvdb_id}",
                        )
                    ]]
                )

            poster_url = _series_poster_url(series)
            if poster_url:
                try:
                    await message.answer_photo(photo=poster_url, caption=card_text, reply_markup=markup)
                    continue
                except Exception:
                    # Если Telegram не принимает URL постера, отправляем текстовый вариант.
                    pass
            await message.answer(card_text, reply_markup=markup)

        if end < len(session.results):
            await message.answer(
                _t(language, "not_all_results_shown"),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text=_t(language, "button_more_options"), callback_data="series_more")]
                    ]
                ),
            )
        else:
            await message.answer(_t(language, "all_results_shown"))

        session.offset = end

    def _find_series_by_tvdb(chat_id: int, tvdb_id: int) -> dict | None:
        session = context.series_search_state.get(chat_id)
        if not session:
            return None

        for series in session.results:
            if int(series.get("tvdbId", 0) or 0) == tvdb_id:
                return series
        return None

    @dp.message(CommandStart())
    async def start_handler(message: Message) -> None:
        chat_id = message.chat.id
        language = _language_for_message(message)
        if context.storage.is_authorized(chat_id):
            await message.answer(
                _t(language, "already_authorized"),
                reply_markup=_main_menu_keyboard(language),
            )
            return

        context.awaiting_password.add(chat_id)
        await message.answer(_t(language, "enter_password"))

    @dp.message(Command("help"))
    async def help_handler(message: Message) -> None:
        language = _language_for_message(message)
        await message.answer(_t(language, "help_text"))

    @dp.message(Command("status"))
    async def status_handler(message: Message) -> None:
        chat_id = message.chat.id
        language = _language_for_message(message)
        if not context.storage.is_authorized(chat_id):
            await message.answer(_t(language, "access_denied"))
            return

        qb_status = _t(language, "qbittorrent_not_configured_short")
        if context.qbittorrent_client is not None:
            qb_status = context.qbittorrent_client.base_url

        await message.answer(
            _t(
                language,
                "status_text",
                radarr=context.radarr_client.base_url,
                sonarr=context.sonarr_client.base_url,
                qbittorrent=qb_status,
            )
        )

    @dp.message(F.text.in_({TRANSLATIONS["ru"]["button_all_series"], TRANSLATIONS["en"]["button_all_series"]}))
    async def all_series_handler(message: Message) -> None:
        chat_id = message.chat.id
        language = _language_for_message(message)
        if not context.storage.is_authorized(chat_id):
            await message.answer(_t(language, "access_denied"))
            return

        try:
            series = context.sonarr_client.get_downloaded_series()
        except requests.RequestException:
            await message.answer(_t(language, "series_fetch_failed"))
            return

        if not series:
            await message.answer(_t(language, "no_series_downloaded"))
            return

        lines = [_t(language, "downloaded_series")]
        lines.extend(
            f"{index}. {item.get('title', _t(language, 'untitled'))}" for index, item in enumerate(series, start=1)
        )
        await message.answer("\n".join(lines))

    @dp.message(F.text.in_({TRANSLATIONS["ru"]["button_all_movies"], TRANSLATIONS["en"]["button_all_movies"]}))
    async def all_movies_handler(message: Message) -> None:
        chat_id = message.chat.id
        language = _language_for_message(message)
        if not context.storage.is_authorized(chat_id):
            await message.answer(_t(language, "access_denied"))
            return

        try:
            movies = context.radarr_client.get_downloaded_movies()
        except requests.RequestException:
            await message.answer(_t(language, "movies_fetch_failed"))
            return

        if not movies:
            await message.answer(_t(language, "no_movies_downloaded"))
            return

        lines = [_t(language, "downloaded_movies")]
        lines.extend(
            f"{index}. {item.get('title', _t(language, 'untitled'))}" for index, item in enumerate(movies, start=1)
        )
        await message.answer("\n".join(lines))

    @dp.message(F.text.in_({TRANSLATIONS["ru"]["button_add_movie"], TRANSLATIONS["en"]["button_add_movie"]}))
    async def add_movie_prompt_handler(message: Message) -> None:
        chat_id = message.chat.id
        language = _language_for_message(message)
        if not context.storage.is_authorized(chat_id):
            await message.answer(_t(language, "access_denied"))
            return

        _reset_pending_inputs(chat_id)
        context.awaiting_movie_query.add(chat_id)
        await message.answer(_t(language, "enter_movie_title"))

    @dp.message(F.text.in_({TRANSLATIONS["ru"]["button_add_series"], TRANSLATIONS["en"]["button_add_series"]}))
    async def add_series_prompt_handler(message: Message) -> None:
        chat_id = message.chat.id
        language = _language_for_message(message)
        if not context.storage.is_authorized(chat_id):
            await message.answer(_t(language, "access_denied"))
            return

        _reset_pending_inputs(chat_id)
        context.awaiting_series_query.add(chat_id)
        await message.answer(_t(language, "enter_series_title"))

    @dp.message(F.text.in_({TRANSLATIONS["ru"]["button_add_magnet"], TRANSLATIONS["en"]["button_add_magnet"]}))
    async def add_magnet_prompt_handler(message: Message) -> None:
        chat_id = message.chat.id
        language = _language_for_message(message)
        if not context.storage.is_authorized(chat_id):
            await message.answer(_t(language, "access_denied"))
            return

        _reset_pending_inputs(chat_id)
        context.awaiting_magnet_link.add(chat_id)
        await message.answer(_t(language, "send_magnet_link"))

    @dp.callback_query(F.data == "movie_more")
    async def movie_more_handler(callback: CallbackQuery) -> None:
        message = callback.message
        if message is None:
            await callback.answer()
            return

        language = _language_for_callback(callback)
        chat_id = message.chat.id
        session = context.movie_search_state.get(chat_id)
        if not session:
            await callback.answer(_t(language, "active_search_not_found"), show_alert=True)
            return

        if session.offset >= len(session.results):
            await callback.answer(_t(language, "no_more_options"), show_alert=True)
            return

        await message.edit_reply_markup(reply_markup=None)
        await _send_movie_results_page(message, session, language)
        await callback.answer()

    @dp.callback_query(F.data == "series_more")
    async def series_more_handler(callback: CallbackQuery) -> None:
        message = callback.message
        if message is None:
            await callback.answer()
            return

        language = _language_for_callback(callback)
        chat_id = message.chat.id
        session = context.series_search_state.get(chat_id)
        if not session:
            await callback.answer(_t(language, "active_search_not_found"), show_alert=True)
            return

        if session.offset >= len(session.results):
            await callback.answer(_t(language, "no_more_options"), show_alert=True)
            return

        await message.edit_reply_markup(reply_markup=None)
        await _send_series_results_page(message, session, language)
        await callback.answer()

    @dp.callback_query(F.data.startswith("movie_add:"))
    async def movie_add_handler(callback: CallbackQuery) -> None:
        message = callback.message
        if message is None:
            await callback.answer()
            return

        language = _language_for_callback(callback)
        chat_id = message.chat.id
        if not context.storage.is_authorized(chat_id):
            await callback.answer(_t(language, "no_access_short"), show_alert=True)
            return

        try:
            tmdb_id = int(str(callback.data).split(":", maxsplit=1)[1])
        except (IndexError, ValueError):
            await callback.answer(_t(language, "invalid_button_data"), show_alert=True)
            return

        movie = _find_movie_by_tmdb(chat_id, tmdb_id)
        if not movie:
            await callback.answer(_t(language, "selected_option_not_found"), show_alert=True)
            return

        try:
            created = context.radarr_client.add_movie(movie)
        except ValueError as exc:
            await message.answer(str(exc))
            await callback.answer()
            return
        except requests.RequestException:
            await message.answer(_t(language, "movie_add_failed"))
            await callback.answer()
            return

        title = created.get("title") or movie.get("title") or _t(language, "untitled")
        context.movie_search_state.pop(chat_id, None)
        await message.answer(_t(language, "movie_added", title=title))
        await callback.answer(_t(language, "added_short"))

    @dp.callback_query(F.data.startswith("series_add:"))
    async def series_add_handler(callback: CallbackQuery) -> None:
        message = callback.message
        if message is None:
            await callback.answer()
            return

        language = _language_for_callback(callback)
        chat_id = message.chat.id
        if not context.storage.is_authorized(chat_id):
            await callback.answer(_t(language, "no_access_short"), show_alert=True)
            return

        try:
            tvdb_id = int(str(callback.data).split(":", maxsplit=1)[1])
        except (IndexError, ValueError):
            await callback.answer(_t(language, "invalid_button_data"), show_alert=True)
            return

        series = _find_series_by_tvdb(chat_id, tvdb_id)
        if not series:
            await callback.answer(_t(language, "selected_option_not_found"), show_alert=True)
            return

        try:
            created = context.sonarr_client.add_series(series)
        except ValueError as exc:
            await message.answer(str(exc))
            await callback.answer()
            return
        except requests.RequestException:
            await message.answer(_t(language, "series_add_failed"))
            await callback.answer()
            return

        title = created.get("title") or series.get("title") or _t(language, "untitled")
        context.series_search_state.pop(chat_id, None)
        await message.answer(_t(language, "series_added", title=title))
        await callback.answer(_t(language, "added_short"))

    @dp.message(F.text)
    async def text_handler(message: Message) -> None:
        chat_id = message.chat.id
        message_text = (message.text or "").strip()
        language = _language_for_message(message)

        if chat_id in context.awaiting_password:
            if message_text == context.config.telegram.password:
                context.storage.add_chat(chat_id)
                context.awaiting_password.discard(chat_id)
                await message.answer(
                    _t(language, "password_correct"),
                    reply_markup=_main_menu_keyboard(language),
                )
            else:
                await message.answer(_t(language, "password_incorrect"))
            return

        if not context.storage.is_authorized(chat_id):
            await message.answer(_t(language, "access_denied"))
            return

        magnet_link = _extract_magnet_link(message_text)
        if magnet_link:
            _reset_pending_inputs(chat_id)
            await _submit_magnet_link(message, magnet_link, language)
            return

        if chat_id in context.awaiting_magnet_link:
            await message.answer(_t(language, "invalid_magnet_link"))
            return

        if chat_id in context.awaiting_series_query:
            if not message_text:
                await message.answer(_t(language, "enter_series_search_text"))
                return

            context.awaiting_series_query.discard(chat_id)
            try:
                series = context.sonarr_client.search_series(message_text)
            except requests.RequestException:
                await message.answer(_t(language, "sonarr_search_failed"))
                return

            if not series:
                await message.answer(_t(language, "nothing_found"))
                return

            session = SeriesSearchSession(query=message_text, results=series)
            context.series_search_state[chat_id] = session
            await _send_series_results_page(message, session, language)
            return

        if chat_id in context.awaiting_movie_query:
            if not message_text:
                await message.answer(_t(language, "enter_movie_search_text"))
                return

            context.awaiting_movie_query.discard(chat_id)
            try:
                movies = context.radarr_client.search_movie(message_text)
            except requests.RequestException:
                await message.answer(_t(language, "radarr_search_failed"))
                return

            if not movies:
                await message.answer(_t(language, "nothing_found"))
                return

            session = MovieSearchSession(query=message_text, results=movies)
            context.movie_search_state[chat_id] = session
            await _send_movie_results_page(message, session, language)
            return

        await message.answer(_t(language, "unknown_command"))

    return dp


async def run_bot() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    config_path = Path(os.getenv("TG_BOT_CONFIG_PATH", "/app/config/config.yaml"))
    storage_path = Path(os.getenv("AUTHORIZED_CHATS_PATH", "/app/data/authorized_chats.json"))

    config = load_config(config_path)
    qbittorrent_client = None
    if config.qbittorrent is not None:
        qbittorrent_client = QBittorrentClient(config.qbittorrent)

    context = AppContext(
        config=config,
        storage=AuthorizedChatsStorage(storage_path),
        radarr_client=RadarrClient(config.radarr),
        sonarr_client=SonarrClient(config.sonarr),
        qbittorrent_client=qbittorrent_client,
        awaiting_password=set(),
        awaiting_movie_query=set(),
        awaiting_series_query=set(),
        awaiting_magnet_link=set(),
        movie_search_state={},
        series_search_state={},
    )

    bot = Bot(token=config.telegram.token)
    dp = _build_dispatcher(context)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
