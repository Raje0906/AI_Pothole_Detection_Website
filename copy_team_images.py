import shutil
import os

def copy_image(source_name, dest_name):
    """Copy an image from uploads to the team images directory."""
    source_path = os.path.join("uploads", source_name)
    dest_path = os.path.join("static", "images", "team", dest_name)
    
    try:
        shutil.copy2(source_path, dest_path)
        print(f"✅ Successfully copied {source_name} to {dest_path}")
    except Exception as e:
        print(f"❌ Error copying {source_name}: {e}")

# Create directory if it doesn't exist
os.makedirs(os.path.join("static", "images", "team"), exist_ok=True)

# Copy team member images
copy_image("aditya.jpg", "aditya.jpg")
copy_image("anshu.jpg", "anshu.jpg") 