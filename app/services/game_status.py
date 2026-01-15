import asyncio
import re
import a2s
from mcstatus import JavaServer
from typing import Dict, Any
import urllib.request
import json

async def get_minecraft_status(server_address: str) -> Dict[str, Any]:
    try:
        # Fix: Manually split host and port to avoid mcstatus parsing errors
        if ":" in server_address:
            host, port = server_address.split(":")
            server = JavaServer(host, int(port))
        else:
            server = await JavaServer.async_lookup(server_address)
            
        status = await server.async_status()
        
        # Parse MOTD: Handle both string and dict formats, then strip color codes
        raw_motd = status.description if isinstance(status.description, str) else status.description.get("text", "")
        clean_motd = re.sub(r'§[0-9a-fk-or]', '', raw_motd)
        
        # Aternos/Cloud servers often return max_players=0 when "offline" or "sleeping"
        if status.players.max == 0:
             return {
                "online": False,
                "game": "Minecraft",
                "motd": "Offline (Sleeping)",
                "players": 0,
                "max_players": 0,
                "version": status.version.name
            }

        return {
            "online": True,
            "game": "Minecraft",
            "players": status.players.online,
            "max_players": status.players.max,
            "latency": round(status.latency, 2),
            "version": status.version.name,
            "motd": clean_motd
        }
    except Exception as e:
        print(f"Minecraft Error: {e}")
        return {
            "online": False,
            "game": "Minecraft",
            "motd": "Offline",
            "players": 0,
            "max_players": 0,
            "version": "Unknown"
        }

async def get_zomboid_status(ip: str, port: int) -> Dict[str, Any]:
    try:
        # Run synchronous a2s call in a separate thread
        # Increased timeout to 8.0s to avoid false negatives
        loop = asyncio.get_running_loop()
        info = await loop.run_in_executor(None, lambda: a2s.info((ip, port), timeout=8.0))
        
        return {
            "online": True,
            "game": "Project Zomboid",
            "server_name": info.server_name,
            "players": info.player_count,
            "max_players": info.max_players,
            "latency": round(info.ping * 1000, 2),
            "map": info.map_name
        }
    except Exception as e:
        print(f"Zomboid Error: {e}")
        return {
            "online": False,
            "game": "Project Zomboid",
            "server_name": "Offline",
            "players": 0,
            "max_players": 0,
            "map": "Unknown"
        }

async def get_discord_status(guild_id: str) -> Dict[str, Any]:
    # Try Widget API first (Best for member list)
    widget_url = f"https://discord.com/api/guilds/{guild_id}/widget.json"
    
    try:
        loop = asyncio.get_running_loop()
        
        def fetch_widget():
            with urllib.request.urlopen(widget_url, timeout=3) as response:
                return json.loads(response.read().decode())
        
        data = await loop.run_in_executor(None, fetch_widget)
        
        return {
            "online": True,
            "game": "Discord",
            "name": data.get("name", "Discord Server"),
            "instant_invite": data.get("instant_invite"),
            "presence_count": data.get("presence_count", 0),
            "members": data.get("members", [])
        }
    except Exception:
        # Fallback: Try Invite API (Good for counts, no member list)
        # We need the invite code. We'll try to fetch it from settings if passed, 
        # but here we only have guild_id. 
        # Ideally we should pass the invite URL to this function too.
        # For now, let's try to get it from the global settings or just fail gracefully.
        # Actually, let's import settings here or change the signature.
        # Changing signature is risky for existing calls.
        # Let's import get_settings inside the function to avoid circular imports if any.
        from app.core.config import get_settings
        settings = get_settings()
        invite_url = settings.DISCORD_INVITE_URL
        
        if not invite_url:
             return {"online": False, "error": "Widget Disabled & No Invite URL"}

        try:
            invite_code = invite_url.split("/")[-1]
            api_url = f"https://discord.com/api/v9/invites/{invite_code}?with_counts=true"
            
            def fetch_invite():
                req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=3) as response:
                    return json.loads(response.read().decode())

            data = await loop.run_in_executor(None, fetch_invite)
            
            guild_info = data.get("guild", {})
            icon_hash = guild_info.get("icon")
            guild_id_resp = guild_info.get("id")
            
            icon_url = None
            if icon_hash and guild_id_resp:
                icon_url = f"https://cdn.discordapp.com/icons/{guild_id_resp}/{icon_hash}.png"

            return {
                "online": True,
                "game": "Discord",
                "name": guild_info.get("name", "Discord Server"),
                "instant_invite": invite_url,
                "presence_count": data.get("approximate_presence_count", 0),
                "icon_url": icon_url,
                "members": [] # Invite API doesn't give member list
            }
        except Exception as e:
            print(f"Discord Error: {e}")
            return {"online": False, "error": "Connection Failed"}
