"""
FTCScout REST API client — api.ftcscout.org/rest/v1
Docs: https://ftcscout.org/api/rest

No API key required. Routes are stable and explicitly documented.
Switched from GraphQL to REST because the REST routes have known field names.
"""

import aiohttp
import logging
from typing import Optional

log = logging.getLogger(__name__)

BASE = "https://api.ftcscout.org/rest/v1"
CURRENT_SEASON = 2024  # INTO THE DEEP (2024-2025 season)


async def _get(path: str, params: dict = None) -> Optional[dict | list]:
    """GET request to the FTCScout REST API. Returns None on 404 or error."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
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
    """GET /teams/:number  =>  Team fields: number, name, schoolName, city, stateProv, country, rookieYear"""
    return await _get(f"/teams/{team_number}")


async def get_team_quick_stats(team_number: int, season: int = CURRENT_SEASON) -> Optional[dict]:
    """
    GET /teams/:number/quick-stats?season=Int
    Returns QuickStats type. Fields include tot, auto, dc, eg, opr
    each as { value, rank }, plus wins, losses, ties at the top level.
    Returns None (404) if team has no events in that season.
    """
    return await _get(f"/teams/{team_number}/quick-stats", {"season": season})


async def get_team_events(team_number: int, season: int = CURRENT_SEASON) -> Optional[list]:
    """GET /teams/:number/events/:season  =>  list of TeamEventParticipation"""
    return await _get(f"/teams/{team_number}/events/{season}")


async def get_team_awards(team_number: int, season: int = None) -> Optional[list]:
    """GET /teams/:number/awards?season=Int  =>  list of Award"""
    params = {"season": season} if season else {}
    return await _get(f"/teams/{team_number}/awards", params)


# -- Events ------------------------------------------------------------------

async def get_event(event_code: str, season: int = CURRENT_SEASON) -> Optional[dict]:
    """
    GET /events/:season/:code  =>  Event fields:
    season, code, name, type, city, stateProv, country, start, end, website, address
    """
    return await _get(f"/events/{season}/{event_code.upper()}")


async def get_event_teams(event_code: str, season: int = CURRENT_SEASON) -> Optional[list]:
    """
    GET /events/:season/:code/teams  =>  list of TeamEventParticipation with stats.
    Each item: { team: {number, name, ...}, stats: {rank, wins, losses, ties, tot, opr, ...} }
    Used for rankings.
    """
    return await _get(f"/events/{season}/{event_code.upper()}/teams")


async def get_event_matches(event_code: str, season: int = CURRENT_SEASON) -> Optional[list]:
    """
    GET /events/:season/:code/matches
    Returns list of Match with scores + teams.
    Fields: matchNum, series, description, hasBeenPlayed,
            redScore.totalPoints, blueScore.totalPoints,
            redTeams[].team.number, blueTeams[].team.number
    """
    return await _get(f"/events/{season}/{event_code.upper()}/matches")


async def get_event_awards(event_code: str, season: int = CURRENT_SEASON) -> Optional[list]:
    """GET /events/:season/:code/awards  =>  list of Award"""
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
