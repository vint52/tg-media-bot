from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

import yaml


@dataclass(frozen=True)
class ServiceServerConfig:
    addr: str
    port: int
    path: str
    ssl: bool


@dataclass(frozen=True)
class ServiceAuthConfig:
    apikey: str


@dataclass(frozen=True)
class MediaServiceConfig:
    server: ServiceServerConfig
    auth: ServiceAuthConfig

    @property
    def base_url(self) -> str:
        scheme = "https" if self.server.ssl else "http"
        normalized_path = self.server.path.strip("/") if self.server.path else ""
        if normalized_path:
            return f"{scheme}://{self.server.addr}:{self.server.port}/{normalized_path}"
        return f"{scheme}://{self.server.addr}:{self.server.port}"


@dataclass(frozen=True)
class TelegramConfig:
    token: str
    password: str
    language: str | None
    proxy: "TelegramProxyConfig | None"


@dataclass(frozen=True)
class TelegramProxyConfig:
    enabled: bool
    type: str
    host: str
    port: int
    username: str | None
    password: str | None

    @property
    def url(self) -> str:
        credentials = ""
        if self.username:
            credentials = quote(self.username, safe="")
            if self.password:
                credentials = f"{credentials}:{quote(self.password, safe='')}"
            credentials = f"{credentials}@"
        return f"{self.type}://{credentials}{self.host}:{self.port}"


@dataclass(frozen=True)
class QBittorrentAuthConfig:
    username: str
    password: str


@dataclass(frozen=True)
class QBittorrentOptionsConfig:
    category: str | None
    tags: list[str]
    savepath: str | None
    paused: bool
    skip_checking: bool
    auto_torrent_management: bool


@dataclass(frozen=True)
class QBittorrentConfig:
    server: ServiceServerConfig
    auth: QBittorrentAuthConfig
    options: QBittorrentOptionsConfig
    verify_tls: bool

    @property
    def base_url(self) -> str:
        scheme = "https" if self.server.ssl else "http"
        normalized_path = self.server.path.strip("/") if self.server.path else ""
        if normalized_path:
            return f"{scheme}://{self.server.addr}:{self.server.port}/{normalized_path}"
        return f"{scheme}://{self.server.addr}:{self.server.port}"


@dataclass(frozen=True)
class AppConfig:
    telegram: TelegramConfig
    radarr: MediaServiceConfig
    sonarr: MediaServiceConfig
    qbittorrent: QBittorrentConfig | None
    admin_notify_id: str | None


def _parse_service(raw: dict[str, Any], service_name: str) -> MediaServiceConfig:
    server = raw.get("server", {})
    auth = raw.get("auth", {})
    apikey = str(auth.get("apikey", "")).strip()
    if not apikey:
        raise ValueError(f"Missing {service_name}.auth.apikey")

    return MediaServiceConfig(
        server=ServiceServerConfig(
            addr=str(server.get("addr", "")).strip(),
            port=int(server.get("port", 0)),
            path=str(server.get("path", "/")),
            ssl=bool(server.get("ssl", False)),
        ),
        auth=ServiceAuthConfig(apikey=apikey),
    )


def _parse_string_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(raw, str):
        return [item.strip() for item in raw.split(",") if item.strip()]
    return []


def _parse_language(raw: Any) -> str | None:
    if raw is None:
        return None

    language = str(raw).strip().lower()
    if not language:
        return None
    if language not in {"ru", "en"}:
        raise ValueError("Unsupported telegram.language. Expected one of: ru, en")
    return language


def _parse_telegram_proxy(raw: dict[str, Any]) -> TelegramProxyConfig | None:
    if not raw:
        return None

    enabled = bool(raw.get("enabled", False))
    proxy_type = str(raw.get("type", "")).strip().lower()
    host = str(raw.get("host", "")).strip()
    port = int(raw.get("port", 0))
    username = str(raw.get("username", "")).strip() or None
    password = str(raw.get("password", "")).strip() or None

    if not enabled:
        return None

    supported_types = {"http", "socks4", "socks5"}
    if proxy_type not in supported_types:
        supported = ", ".join(sorted(supported_types))
        raise ValueError(f"Unsupported telegram.proxy.type. Expected one of: {supported}")
    if not host:
        raise ValueError("Missing telegram.proxy.host")
    if port <= 0:
        raise ValueError("Missing telegram.proxy.port")
    if password and not username:
        raise ValueError("telegram.proxy.username is required when password is set")

    return TelegramProxyConfig(
        enabled=True,
        type=proxy_type,
        host=host,
        port=port,
        username=username,
        password=password,
    )


def _parse_qbittorrent(raw: dict[str, Any]) -> QBittorrentConfig | None:
    if not raw:
        return None

    if not bool(raw.get("enabled", True)):
        return None

    server = raw.get("server", {})
    auth = raw.get("auth", {})
    options = raw.get("options", {})

    addr = str(server.get("addr", "")).strip()
    port = int(server.get("port", 0))
    username = str(auth.get("username", "")).strip()
    password = str(auth.get("password", "")).strip()

    if not addr:
        raise ValueError("Missing qbittorrent.server.addr")
    if port <= 0:
        raise ValueError("Missing qbittorrent.server.port")
    if not username:
        raise ValueError("Missing qbittorrent.auth.username")
    if not password:
        raise ValueError("Missing qbittorrent.auth.password")

    return QBittorrentConfig(
        server=ServiceServerConfig(
            addr=addr,
            port=port,
            path=str(server.get("path", "/")).strip() or "/",
            ssl=bool(server.get("ssl", False)),
        ),
        auth=QBittorrentAuthConfig(username=username, password=password),
        options=QBittorrentOptionsConfig(
            category=str(options.get("category", "")).strip() or None,
            tags=_parse_string_list(options.get("tags", [])),
            savepath=str(options.get("savepath", "")).strip() or None,
            paused=bool(options.get("paused", False)),
            skip_checking=bool(options.get("skip_checking", False)),
            auto_torrent_management=bool(options.get("auto_torrent_management", False)),
        ),
        verify_tls=bool(raw.get("verify_tls", True)),
    )


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as config_file:
        raw = yaml.safe_load(config_file) or {}

    telegram_raw = raw.get("telegram", {})
    token = str(telegram_raw.get("token", "")).strip()
    password = str(telegram_raw.get("password", "")).strip()
    if not token:
        raise ValueError("Missing telegram.token")
    if not password:
        raise ValueError("Missing telegram.password")
    language = _parse_language(telegram_raw.get("language"))
    proxy = _parse_telegram_proxy(telegram_raw.get("proxy", {}))

    return AppConfig(
        telegram=TelegramConfig(token=token, password=password, language=language, proxy=proxy),
        radarr=_parse_service(raw.get("radarr", {}), "radarr"),
        sonarr=_parse_service(raw.get("sonarr", {}), "sonarr"),
        qbittorrent=_parse_qbittorrent(raw.get("qbittorrent", {})),
        admin_notify_id=str(raw.get("adminNotifyId", "")).strip() or None,
    )
