import os
from pathlib import Path
from app.config import Configuration

conf = Configuration()
IMAGE_FOLDER = Path(Configuration.image_folder_path)

def list_images():

    """Returns the list of available images from the correct folder."""
    supported_formats = (".JPEG", ".jpeg", ".jpg", ".png")
    img_folder = conf.image_folder_path  # Ensure this is correctly set


    if not os.path.exists(img_folder):
        print(f"WARNING: Image folder '{img_folder}' does not exist.")
        return []

    return [f for f in os.listdir(img_folder) if f.endswith(supported_formats)]

#fixed for use more format
