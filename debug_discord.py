import urllib.request
import json
import os
from dotenv import load_dotenv

load_dotenv()

GUILD_ID = os.getenv("DISCORD_GUILD_ID")
print(f"Testing Discord Widget for Guild ID: {GUILD_ID}")

if not GUILD_ID:
    print("Error: DISCORD_GUILD_ID not found in .env")
    exit(1)

url = f"https://discord.com/api/guilds/{GUILD_ID}/widget.json"
print(f"Fetching URL: {url}")

try:
    with urllib.request.urlopen(url, timeout=10) as response:
        data = json.loads(response.read().decode())
        print("\n--- Success! ---")
        print(f"Server Name: {data.get('name')}")
        print(f"Instant Invite: {data.get('instant_invite')}")
        print(f"Presence Count: {data.get('presence_count')}")
        print(f"Members Online: {len(data.get('members', []))}")
except Exception as e:
    print(f"\n--- Error ---")
    print(e)
    if "HTTP Error 403" in str(e):
        print("Hint: Widget might be disabled in Discord Server Settings.")
    elif "HTTP Error 404" in str(e):
        print("Hint: Guild ID might be incorrect.")
