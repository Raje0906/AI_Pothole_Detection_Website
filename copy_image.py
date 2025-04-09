import shutil
import os

# Source image path (the image you provided)
source_image = "uploads/anshu.jpg"  # Assuming the image is in the uploads folder

# Destination path
dest_path = os.path.join("static", "images", "team", "anshu.jpg")

# Create directory if it doesn't exist
os.makedirs(os.path.dirname(dest_path), exist_ok=True)

# Copy the image
try:
    shutil.copy2(source_image, dest_path)
    print(f"✅ Successfully copied image to {dest_path}")
except Exception as e:
    print(f"❌ Error copying image: {e}") 