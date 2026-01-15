import urllib.request
import json
import os
from dotenv import load_dotenv

load_dotenv()

INVITE_URL = os.getenv("DISCORD_INVITE_URL")
print(f"Testing Discord Invite API for URL: {INVITE_URL}")

if not INVITE_URL:
    print("Error: DISCORD_INVITE_URL not found in .env")
    exit(1)

# Extract code from URL
invite_code = INVITE_URL.split("/")[-1]
api_url = f"https://discord.com/api/v9/invites/{invite_code}?with_counts=true"

print(f"Fetching API URL: {api_url}")

try:
    req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode())
        print("\n--- Success! ---")
        print(f"Server Name: {data.get('guild', {}).get('name')}")
        print(f"Online: {data.get('approximate_presence_count')}")
        print(f"Total Members: {data.get('approximate_member_count')}")
        print(f"Icon: {data.get('guild', {}).get('icon')}")
except Exception as e:
    print(f"\n--- Error ---")
    print(e)
