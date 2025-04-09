import requests
import os

def download_image(url, filename):
    """Download an image from URL and save it to the specified path."""
    response = requests.get(url)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"✅ Downloaded {filename}")
    else:
        print(f"❌ Failed to download {filename}")

# Create images directory if it doesn't exist
os.makedirs('static/images', exist_ok=True)

# Logo URL (using a modern road/pothole detection themed icon)
logo_url = "https://raw.githubusercontent.com/FortAwesome/Font-Awesome/master/svgs/solid/road.svg"
logo_path = os.path.join('static/images', 'logo.svg')

# Download the logo
if not os.path.exists(logo_path):
    download_image(logo_url, logo_path) 