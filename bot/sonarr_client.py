from __future__ import annotations

import requests

from bot.config import MediaServiceConfig


class SonarrClient:
    def __init__(self, config: MediaServiceConfig) -> None:
        self.base_url = config.base_url
        self.api_key = config.auth.apikey

    def _headers(self) -> dict[str, str]:
        return {"X-Api-Key": self.api_key}

    def search_series(self, query: str) -> list[dict]:
        response = requests.get(
            f"{self.base_url}/api/v3/series/lookup",
            headers=self._headers(),
            params={"term": query},
            timeout=10,
        )
        response.raise_for_status()
        series = response.json()
        if not isinstance(series, list):
            return []

        return sorted(series, key=lambda item: str(item.get("title", "")).lower())

    def _get_default_quality_profile_id(self) -> int:
        response = requests.get(
            f"{self.base_url}/api/v3/qualityprofile",
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        profiles = response.json()
        if not profiles:
            raise RuntimeError("В Sonarr не найден ни один quality profile.")
        return int(profiles[0]["id"])

    def _get_default_language_profile_id(self) -> int:
        response = requests.get(
            f"{self.base_url}/api/v3/languageprofile",
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        profiles = response.json()
        if not profiles:
            raise RuntimeError("В Sonarr не найден ни один language profile.")
        return int(profiles[0]["id"])

    def _get_default_root_folder(self) -> str:
        response = requests.get(
            f"{self.base_url}/api/v3/rootfolder",
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        folders = response.json()
        if not folders:
            raise RuntimeError("В Sonarr не найдена root folder.")
        return str(folders[0]["path"])

    def add_series(self, series: dict) -> dict:
        tvdb_id = int(series.get("tvdbId", 0) or 0)
        if tvdb_id <= 0:
            raise ValueError("Нельзя добавить сериал без tvdbId.")

        quality_profile_id = int(series.get("qualityProfileId", 0) or 0)
        if quality_profile_id <= 0:
            quality_profile_id = self._get_default_quality_profile_id()

        language_profile_id = int(series.get("languageProfileId", 0) or 0)
        if language_profile_id <= 0:
            language_profile_id = self._get_default_language_profile_id()

        root_folder_path = str(series.get("rootFolderPath", "")).strip()
        if not root_folder_path:
            root_folder_path = self._get_default_root_folder()

        seasons = series.get("seasons")
        if not isinstance(seasons, list):
            seasons = []

        payload = {
            "title": series.get("title"),
            "tvdbId": tvdb_id,
            "titleSlug": series.get("titleSlug"),
            "images": series.get("images", []),
            "qualityProfileId": quality_profile_id,
            "languageProfileId": language_profile_id,
            "rootFolderPath": root_folder_path,
            "seasonFolder": True,
            "monitored": True,
            "seasons": seasons,
            "addOptions": {"searchForMissingEpisodes": True},
        }

        response = requests.post(
            f"{self.base_url}/api/v3/series",
            headers=self._headers(),
            json=payload,
            timeout=10,
        )
        if response.status_code >= 400:
            error_text = response.text.lower()
            if "has already been added" in error_text:
                raise ValueError("Этот сериал уже добавлен в Sonarr.")
            response.raise_for_status()

        return response.json()

    def get_downloaded_series(self) -> list[dict]:
        response = requests.get(
            f"{self.base_url}/api/v3/series",
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()

        series_list = response.json()
        downloaded = []
        for series in series_list:
            statistics = series.get("statistics") or {}
            if int(statistics.get("sizeOnDisk", 0) or 0) > 0:
                downloaded.append(series)

        return sorted(downloaded, key=lambda item: str(item.get("title", "")).lower())
