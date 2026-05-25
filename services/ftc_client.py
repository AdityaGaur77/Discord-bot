"""
FTCScout REST API client — api.ftcscout.org/rest/v1

No API key required. A single aiohttp.ClientSession is reused for all requests.
Call init_session() at bot startup and close_session() at shutdown.
"""

import aiohttp
import logging
from typing import Optional

log = logging.getLogger(__name__)

BASE           = "https://api.ftcscout.org/rest/v1"
CURRENT_SEASON = 2025  # DECODE (2025-2026 season)

_session: Optional[aiohttp.ClientSession] = None


async def init_session() -> None:
    global _session
    _session = aiohttp.ClientSession()


async def close_session() -> None:
    global _session
    if _session and not _session.closed:
        await _session.close()
        _session = None


async def _get(path: str, params: dict = None) -> Optional[dict | list]:
    """GET request to the FTCScout REST API. Returns None on 404 or error."""
    global _session
    if _session is None or _session.closed:
        # Lazy fallback — shouldn't normally happen if setup_hook called init_session
        log.warning("FTC session not initialised — creating ad-hoc session")
        _session = aiohttp.ClientSession()
    try:
        async with _session.get(
            f"{BASE}{path}",
            params=params or {},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 404:
                return None
            if resp.status != 200:
                log.warning("FTCScout API %s -> HTTP %s", path, resp.status)
                return None
            return await resp.json()
    except aiohttp.ClientError as e:
        log.error("FTCScout API request failed: %s", e)
        return None


# -- Teams -------------------------------------------------------------------

async def get_team(team_number: int) -> Optional[dict]:
    """GET /teams/:number"""
    return await _get(f"/teams/{team_number}")


async def get_team_quick_stats(team_number: int, season: int = CURRENT_SEASON) -> Optional[dict]:
    """GET /teams/:number/quick-stats?season=Int"""
    return await _get(f"/teams/{team_number}/quick-stats", {"season": season})


async def get_team_events(team_number: int, season: int = CURRENT_SEASON) -> Optional[list]:
    """GET /teams/:number/events/:season"""
    return await _get(f"/teams/{team_number}/events/{season}")


async def get_team_awards(team_number: int, season: int = None) -> Optional[list]:
    """GET /teams/:number/awards?season=Int"""
    params = {"season": season} if season else {}
    return await _get(f"/teams/{team_number}/awards", params)


# -- Events ------------------------------------------------------------------

async def get_event(event_code: str, season: int = CURRENT_SEASON) -> Optional[dict]:
    """GET /events/:season/:code"""
    return await _get(f"/events/{season}/{event_code.upper()}")


async def get_event_teams(event_code: str, season: int = CURRENT_SEASON) -> Optional[list]:
    """GET /events/:season/:code/teams"""
    return await _get(f"/events/{season}/{event_code.upper()}/teams")


async def get_event_matches(event_code: str, season: int = CURRENT_SEASON) -> Optional[list]:
    """GET /events/:season/:code/matches"""
    return await _get(f"/events/{season}/{event_code.upper()}/matches")


async def get_event_awards(event_code: str, season: int = CURRENT_SEASON) -> Optional[list]:
    """GET /events/:season/:code/awards"""
    return await _get(f"/events/{season}/{event_code.upper()}/awards")


# -- Convenience helpers -----------------------------------------------------

async def get_rankings(event_code: str, season: int = CURRENT_SEASON) -> Optional[list]:
    """Rankings = event teams sorted by stats.rank."""
    teams = await get_event_teams(event_code, season)
    if teams is None:
        return None
    return sorted(teams, key=lambda t: (t.get("stats") or {}).get("rank", 9999))


async def get_scores(event_code: str, season: int = CURRENT_SEASON) -> Optional[list]:
    """Only played matches."""
    matches = await get_event_matches(event_code, season)
    if matches is None:
        return None
    return [m for m in matches if m.get("hasBeenPlayed")]


async def get_schedule(event_code: str, season: int = CURRENT_SEASON) -> Optional[list]:
    """Only unplayed matches."""
    matches = await get_event_matches(event_code, season)
    if matches is None:
        return None
    return [m for m in matches if not m.get("hasBeenPlayed")]
