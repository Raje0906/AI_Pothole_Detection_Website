import base64
import os

# Create the team images directory if it doesn't exist
os.makedirs('static/images/team', exist_ok=True)

# The image data (this is a placeholder - you'll need to replace it with the actual image data)
image_data = '''
[Your base64 image data will be here]
'''

# Remove any whitespace and newlines from the base64 string
image_data = image_data.strip()

# Save the image
image_path = os.path.join('static/images/team', 'anshu.jpg')
with open(image_path, 'wb') as f:
    f.write(base64.b64decode(image_data))

print(f"✅ Saved image to {image_path}") 