from __future__ import annotations

import requests

from bot.config import MediaServiceConfig


class RadarrClient:
    def __init__(self, config: MediaServiceConfig) -> None:
        self.base_url = config.base_url
        self.api_key = config.auth.apikey

    def _headers(self) -> dict[str, str]:
        return {"X-Api-Key": self.api_key}

    def search_movie(self, query: str) -> list[dict]:
        response = requests.get(
            f"{self.base_url}/api/v3/movie/lookup",
            headers=self._headers(),
            params={"term": query},
            timeout=10,
        )
        response.raise_for_status()
        movies = response.json()
        if not isinstance(movies, list):
            return []

        return sorted(
            movies,
            key=lambda item: (
                str(item.get("title", "")).lower(),
                int(item.get("year", 0) or 0),
            ),
        )

    def _get_default_quality_profile_id(self) -> int:
        response = requests.get(
            f"{self.base_url}/api/v3/qualityprofile",
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        profiles = response.json()
        if not profiles:
            raise RuntimeError("В Radarr не найден ни один quality profile.")
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
            raise RuntimeError("В Radarr не найдена root folder.")
        return str(folders[0]["path"])

    def add_movie(self, movie: dict) -> dict:
        tmdb_id = int(movie.get("tmdbId", 0) or 0)
        if tmdb_id <= 0:
            raise ValueError("Нельзя добавить фильм без tmdbId.")

        quality_profile_id = int(movie.get("qualityProfileId", 0) or 0)
        if quality_profile_id <= 0:
            quality_profile_id = self._get_default_quality_profile_id()

        root_folder_path = str(movie.get("rootFolderPath", "")).strip()
        if not root_folder_path:
            root_folder_path = self._get_default_root_folder()

        payload = {
            "title": movie.get("title"),
            "year": movie.get("year"),
            "tmdbId": tmdb_id,
            "titleSlug": movie.get("titleSlug"),
            "images": movie.get("images", []),
            "qualityProfileId": quality_profile_id,
            "rootFolderPath": root_folder_path,
            "minimumAvailability": movie.get("minimumAvailability") or "announced",
            "monitored": True,
            "addOptions": {"searchForMovie": True},
        }

        response = requests.post(
            f"{self.base_url}/api/v3/movie",
            headers=self._headers(),
            json=payload,
            timeout=10,
        )
        if response.status_code >= 400:
            error_text = response.text.lower()
            if "has already been added" in error_text:
                raise ValueError("Этот фильм уже добавлен в Radarr.")
            response.raise_for_status()

        return response.json()

    def get_downloaded_movies(self) -> list[dict]:
        response = requests.get(
            f"{self.base_url}/api/v3/movie",
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()

        movies_list = response.json()
        downloaded = []
        for movie in movies_list:
            if int(movie.get("sizeOnDisk", 0) or 0) > 0:
                downloaded.append(movie)

        return sorted(downloaded, key=lambda item: str(item.get("title", "")).lower())
