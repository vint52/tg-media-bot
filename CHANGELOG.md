# Changelog

All notable changes to this project are documented in this file.

The entries below are based on the published GitHub Releases history.

## [0.0.5] - 2026-03-22

### Changed

- improved reliability of movie and series add/delete actions
- verified Radarr and Sonarr results after timeout before reporting failure
- improved Telegram message cleanup
- removed leftover UI pieces from the old magnet-based flow

## [0.0.4] - 2026-03-22

### Added

- detailed movie and series views
- library pagination
- deletion flow for media items directly from Telegram with confirmation
- Telegram Bot API proxy support with `http`, `socks4`, and `socks5`

### Changed

- improved button labels and interface texts
- removed the separate magnet button from the main menu

## [0.0.3] - 2026-03-22

### Added

- configurable Telegram proxy support with `http`, `socks4`, and `socks5`
- media details views for library items
- media deletion flow from the bot
- pagination for library details
- updated configuration examples and documentation for proxy settings

### Notes

- Telegram proxy settings affect only Telegram Bot API traffic
- Radarr, Sonarr, and qBittorrent connections continue to use their own direct configuration
- MTProto proxies are not supported

## [0.0.2] - 2026-03-21

### Added

- configurable proxy support for Telegram Bot API connections
- new `telegram.proxy` configuration block
- support for proxy types `http`, `socks4`, and `socks5`
- proxy configuration fields: `enabled`, `type`, `host`, `port`, `username`, `password`
- updated `config.example.yaml`, `README.md`, and `README.ru.md` with proxy usage examples

### Notes

- proxy settings apply only to Telegram Bot API traffic
- Radarr, Sonarr, and qBittorrent continue to use their existing direct configuration
- MTProto proxy is not supported

## [0.0.1] - 2026-03-15

### Added

- initial public release of the standalone Telegram bot
- password-based Telegram authorization
- browsing downloaded movies from Radarr
- browsing downloaded series from Sonarr
- searching and adding movies to Radarr
- searching and adding series to Sonarr
- optional magnet link forwarding to qBittorrent
- persistent authorized chat storage
- RU/EN interface support
- Docker image support
- GHCR publishing workflow
- multi-arch image build for `linux/amd64` and `linux/arm64`
- example configuration for local run and Docker Compose deployment

### Notes

- the repository contains only the bot service
- Radarr, Sonarr, and optional qBittorrent must already be deployed and reachable
