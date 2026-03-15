from __future__ import annotations

import requests

from bot.config import QBittorrentConfig


class QBittorrentClient:
    def __init__(self, config: QBittorrentConfig) -> None:
        self.base_url = config.base_url
        self.username = config.auth.username
        self.password = config.auth.password
        self.options = config.options
        self.session = requests.Session()
        self.session.verify = config.verify_tls

    def _headers(self) -> dict[str, str]:
        return {"Referer": f"{self.base_url}/"}

    def _login(self) -> None:
        response = self.session.post(
            f"{self.base_url}/api/v2/auth/login",
            data={"username": self.username, "password": self.password},
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        if response.text.strip() != "Ok.":
            raise ValueError("Не удалось авторизоваться в qBittorrent. Проверьте логин и пароль.")

    def add_magnet(self, magnet_url: str) -> None:
        self._login()

        payload = {
            "urls": magnet_url,
            "paused": "true" if self.options.paused else "false",
            "skip_checking": "true" if self.options.skip_checking else "false",
            "autoTMM": "true" if self.options.auto_torrent_management else "false",
        }
        if self.options.category:
            payload["category"] = self.options.category
        if self.options.tags:
            payload["tags"] = ",".join(self.options.tags)
        if self.options.savepath:
            payload["savepath"] = self.options.savepath

        response = self.session.post(
            f"{self.base_url}/api/v2/torrents/add",
            data=payload,
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()

        response_text = response.text.strip()
        if response_text and response_text != "Ok.":
            raise ValueError(f"qBittorrent отклонил magnet-ссылку: {response_text}")

    def get_version(self) -> str:
        self._login()
        response = self.session.get(
            f"{self.base_url}/api/v2/app/version",
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.text.strip()
