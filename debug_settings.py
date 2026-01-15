from app.core.config import get_settings
import os

def check_settings():
    print("--- Environment Variables ---")
    print(f"MINECRAFT_DISPLAY_NAME env: {os.getenv('MINECRAFT_DISPLAY_NAME')}")
    
    print("\n--- Pydantic Settings ---")
    settings = get_settings()
    print(f"MINECRAFT_DISPLAY_NAME: {settings.MINECRAFT_DISPLAY_NAME}")
    print(f"ZOMBOID_SERVER: {settings.ZOMBOID_SERVER}")
    print(f"ZOMBOID_DISPLAY_NAME: {settings.ZOMBOID_DISPLAY_NAME}")
    print(f"DISCORD_GUILD_ID: {settings.DISCORD_GUILD_ID}")

    print("\n--- Manual Dotenv Check ---")
    from dotenv import load_dotenv, find_dotenv
    print(f"Dotenv found: {find_dotenv()}")
    load_dotenv()
    print(f"MINECRAFT_DISPLAY_NAME after load: {os.getenv('MINECRAFT_DISPLAY_NAME')}")

if __name__ == "__main__":
    check_settings()
