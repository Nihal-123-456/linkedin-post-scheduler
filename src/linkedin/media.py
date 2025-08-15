import requests
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_MEDIA_TYPES = {
    '.jpg': 'urn:li:digitalmediaRecipe:feedshare-image',
    '.jpeg': 'urn:li:digitalmediaRecipe:feedshare-image',
    '.png': 'urn:li:digitalmediaRecipe:feedshare-image',
    '.gif': 'urn:li:digitalmediaRecipe:feedshare-image',
    '.mp4': 'urn:li:digitalmediaRecipe:feedshare-video',
    '.mov': 'urn:li:digitalmediaRecipe:feedshare-video'
}

VALID_MEDIA_TYPES = {
    '.jpg': 'IMAGE',
    '.jpeg': 'IMAGE',
    '.png': 'IMAGE',
    '.gif': 'IMAGE',
    '.mp4': 'VIDEO',
    '.mov': 'VIDEO'
}

# a custom exception class for all linkedin errors
class LinkedInPostError(Exception):
    pass

def validate_media_extension(media_name):
    media_extension = Path(media_name).suffix.lower() # we are getting the file extension(anything after (.))
    media_recipe = SUPPORTED_MEDIA_TYPES.get(media_extension)
    if not media_recipe:
        raise LinkedInPostError(f"Unsupported media type: {media_extension}. Supported: {list(SUPPORTED_MEDIA_TYPES.keys())}")
    media_type = VALID_MEDIA_TYPES[media_extension]
    return media_recipe, media_type

def upload_media_to_url(path, upload_url, retries=3, delay=3):
    # we will try a maximum of three times for uploading the media and after each attempt a 3 second delay will be made
    for attempt in range(retries):
        try:
            # opens the file at path in binary read mode for uploading its contents
            with open(path, 'rb') as f:
                headers = {'Content-Type': 'application/octet-stream'}
                response = requests.put(upload_url, data=f, headers=headers, timeout=20) # the timeout defines maximum wait time to connect to the linkedin servers and upload the media
                response.raise_for_status() 
        except requests.RequestException as e:
            if attempt < retries - 1:
                logger.warning(f"Upload failed, retrying in {delay}s. ({attempt+1}/{retries})")
                time.sleep(delay)
            else:
                raise LinkedInPostError(f"Failed to upload media after {retries} attempts: {e}")