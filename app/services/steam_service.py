import httpx
import xml.etree.ElementTree as ET
import json
import os
import aiofiles
from typing import Dict, Any, List, Optional
from app.core.config import get_settings
from cachetools import TTLCache, cached

settings = get_settings()
# Cache for 15 minutes (900 seconds) in memory
profile_cache = TTLCache(maxsize=1, ttl=900)
CACHE_FILE = "steam_cache.json"

async def get_game_achievements(client: httpx.AsyncClient, appid: int) -> Dict[str, Any]:
    """
    Fetches achievement completion for a specific game.
    Returns {total, achieved, percentage}
    """
    try:
        url = f"http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/?appid={appid}&key={settings.STEAM_API_KEY}&steamid={settings.STEAM_ID}"
        resp = await client.get(url, timeout=2.0)
        if resp.status_code != 200:
            return {"total": 0, "achieved": 0, "percentage": 0}
        
        data = resp.json()
        achievements = data.get("playerstats", {}).get("achievements", [])
        
        if not achievements:
            return {"total": 0, "achieved": 0, "percentage": 0}
            
        total = len(achievements)
        achieved = sum(1 for a in achievements if a.get("achieved") == 1)
        percentage = int((achieved / total) * 100) if total > 0 else 0
        
        return {"total": total, "achieved": achieved, "percentage": percentage}
    except Exception:
        return {"total": 0, "achieved": 0, "percentage": 0}

async def get_screenshots() -> List[Dict[str, str]]:
    """
    Fetches the latest 4 screenshots from the user's RSS feed.
    """
    try:
        rss_url = f"https://steamcommunity.com/profiles/{settings.STEAM_ID}/screenshots/rss"
        async with httpx.AsyncClient() as client:
            resp = await client.get(rss_url, timeout=5.0)
            if resp.status_code != 200:
                print(f"Error fetching screenshots: Status {resp.status_code}")
                return []
            
            # Basic sanitization to avoid XML parse errors
            content = resp.content.decode("utf-8", errors="ignore")
            root = ET.fromstring(content)
            screenshots = []
            
            for item in root.findall("./channel/item")[:4]:
                title = item.find("title").text if item.find("title") is not None else "Screenshot"
                link = item.find("link").text if item.find("link") is not None else "#"
                description_elem = item.find("description")
                description = description_elem.text if description_elem is not None else ""
                
                # Extract image URL from description HTML
                img_url = ""
                if 'src="' in description:
                    try:
                        start = description.find('src="') + 5
                        end = description.find('"', start)
                        img_url = description[start:end]
                    except Exception:
                        pass
                
                if img_url:
                    screenshots.append({
                        "title": title,
                        "link": link,
                        "image_url": img_url
                    })
            
            return screenshots
    except Exception as e:
        print(f"Screenshot RSS Error: {e}")
        return []

async def _save_to_cache(data: Dict[str, Any]):
    """Saves valid data to a local JSON file."""
    try:
        async with aiofiles.open(CACHE_FILE, mode='w') as f:
            await f.write(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Failed to write steam cache: {e}")

async def _load_from_cache() -> Optional[Dict[str, Any]]:
    """Loads data from local JSON file if it exists."""
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        async with aiofiles.open(CACHE_FILE, mode='r') as f:
            content = await f.read()
            return json.loads(content)
    except Exception as e:
        print(f"Failed to read steam cache: {e}")
        return None

@cached(cache=profile_cache)
async def get_steam_profile() -> Dict[str, Any]:
    if not settings.STEAM_API_KEY or not settings.STEAM_ID:
        return {"error": "Steam credentials not configured"}

    async with httpx.AsyncClient() as client:
        try:
            # 1. Get Player Summary
            summary_url = f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={settings.STEAM_API_KEY}&steamids={settings.STEAM_ID}"
            summary_resp = await client.get(summary_url, timeout=5.0)
            player_data = summary_resp.json()
            
            if "response" not in player_data or "players" not in player_data["response"] or not player_data["response"]["players"]:
                 raise ValueError("Invalid Steam API response")
            
            player = player_data["response"]["players"][0]

            # 2. Get Steam Level
            level_url = f"http://api.steampowered.com/IPlayerService/GetSteamLevel/v1/?key={settings.STEAM_API_KEY}&steamid={settings.STEAM_ID}"
            level_resp = await client.get(level_url, timeout=5.0)
            level = 0
            if level_resp.status_code == 200:
                level = level_resp.json().get("response", {}).get("player_level", 0)

            # 3. Get Recently Played Games
            recent_url = f"http://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v0001/?key={settings.STEAM_API_KEY}&steamid={settings.STEAM_ID}&count=3"
            recent_resp = await client.get(recent_url, timeout=5.0)
            recent_games_data = recent_resp.json().get("response", {}).get("games", [])

            # Process Games & Fetch Achievements
            processed_games = []
            for game in recent_games_data:
                appid = game.get("appid")
                achievements = await get_game_achievements(client, appid)
                
                playtime_2weeks = round(game.get("playtime_2weeks", 0) / 60, 1)
                playtime_forever = round(game.get("playtime_forever", 0) / 60, 1)
                
                processed_games.append({
                    "name": game.get("name"),
                    "appid": appid,
                    "playtime_2weeks": playtime_2weeks,
                    "playtime_total": playtime_forever,
                    "icon_url": f"http://media.steampowered.com/steamcommunity/public/images/apps/{appid}/{game.get('img_icon_url')}.jpg",
                    "achievements": achievements
                })

            # 4. Get Screenshots
            screenshots = await get_screenshots()

            final_data = {
                "online": True,
                "username": player.get("personaname"),
                "avatar_url": player.get("avatarfull"),
                "profile_url": player.get("profileurl"),
                "level": level,
                "status": player.get("personastate"),
                "recent_games": processed_games,
                "screenshots": screenshots
            }
            
            # SUCCESS: Save to file cache
            await _save_to_cache(final_data)
            
            return final_data

        except Exception as e:
            print(f"Steam API Failed: {e}. Trying fallback cache.")
            cached_data = await _load_from_cache()
            if cached_data:
                # Mark as offline/cached version if you want, or just return as is
                # cached_data["status"] = 0 # Optional: force offline status visual
                return cached_data
            
            return {"online": False, "error": "Steam unreachable and no cache found."}
