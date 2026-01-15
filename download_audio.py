import os
import requests

# Royalty-free sci-fi sound (Alien Transmission)
url = "https://cdn.pixabay.com/download/audio/2022/03/10/audio_c8c8a73467.mp3?filename=scifi-glitch-interference-10115.mp3"
output_dir = "app/static/audio"
output_file = os.path.join(output_dir, "radiohead.mp3") # Naming it radiohead.mp3 so code works, user can replace

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

print(f"Downloading placeholder to {output_file}...")
try:
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(output_file, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print("Download complete.")
except Exception as e:
    print(f"Error: {e}")
