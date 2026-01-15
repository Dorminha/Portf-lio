import asyncio
import a2s
import os
from dotenv import load_dotenv

load_dotenv()

def test_zomboid():
    address = os.getenv("ZOMBOID_SERVER")
    print(f"Testing Zomboid Connection to: {address}")
    
    if not address:
        print("Error: ZOMBOID_SERVER not set in .env")
        return

    ip, port = address.split(":")
    port = int(port)
    
    try:
        print(f"Querying {ip}:{port}...")
        info = a2s.info((ip, port), timeout=5.0)
        print("\n--- Success! ---")
        print(f"Server Name: {info.server_name}")
        print(f"Players: {info.player_count}/{info.max_players}")
        print(f"Map: {info.map_name}")
    except Exception as e:
        print(f"\n--- Error ---")
        print(e)

if __name__ == "__main__":
    test_zomboid()
