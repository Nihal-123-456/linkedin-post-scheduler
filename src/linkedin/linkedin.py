from django.contrib.auth import get_user_model
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.utils import timezone
from .payload import *
from .media import validate_media_extension, upload_media_to_url, LinkedInPostError
from django.core.exceptions import ValidationError
import requests
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

def get_user_linkedin(user):
    try:
        user_linkedin = user.socialaccount_set.get(provider='linkedin')
    except SocialAccount.DoesNotExist:
        raise LinkedInPostError("LinkedIn account is not connected.")
    return user_linkedin

def get_request_headers(user_linkedin):
    try:
        user_token = (user_linkedin.socialtoken_set.filter(expires_at__isnull = True) | user_linkedin.socialtoken_set.filter(expires_at__gt = timezone.now())).order_by('-expires_at').first() # we are trying to fetch the latest valid token by filtering tokens with no expiry or tokens which are yet to expire
    except SocialToken.DoesNotExist:
        raise LinkedInPostError("Valid LinkedIn token not found or expired.")
    headers = {
        "X-Restli-Protocol-Version": "2.0.0",
        "Authorization": f"Bearer {user_token.token}"
    }
    return headers

def get_media_upload_content(post, author):
    media_recipe, media_type = validate_media_extension(post.media.name)
    endpoint = "https://api.linkedin.com/v2/assets?action=registerUpload"
    user_linkedin = get_user_linkedin(post.user) 
    headers = get_request_headers(user_linkedin)

    payload = {
        "registerUploadRequest": {
            "recipes": [media_recipe],
            "owner": author,
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }
            ]
        }
    }

    response = requests.post(endpoint, json=payload, headers=headers)

    try:
        response.raise_for_status() # checks the HTTP code of a response and raises exception if there is an error
    except requests.RequestException as e: # highlights network related errors
        logger.error(f"LinkedIn post failed: {e} | Response: {getattr(e.response, 'text', None)}")
        raise LinkedInPostError(f"Failed to upload media on LinkedIn: {e}")
    
    response_data = response.json() # for receiving the json data. If we used only response then we would have gotten only the status code.
    upload_url = response_data.get("value").get("uploadMechanism").get("com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest").get("uploadUrl")
    asset = response_data.get("value").get("asset")

    media_path = post.get_media_path() # we can also get the media path by post.media.path. But using the default_storage is compitable with cloud backends
    if not media_path:
        raise LinkedInPostError(f"Media file not found or not set for post: {post.media.name if post.media else 'None'}")
    
    upload_media_to_url(media_path, upload_url)
    return asset, media_type

def get_post_payload(post, author):
    if post.media:
        asset, media_type = get_media_upload_content(post, author)
        return get_image_payload(post, author, asset, media_type)
    elif post.article_url and not post.media:
        return get_article_payload(post, author)
    else:
        return get_text_payload(post, author) 

def post_on_linkedin(post):
    user_linkedin = get_user_linkedin(post.user)
    author_urn = f"urn:li:person:{user_linkedin.uid}"
    payload = get_post_payload(post, author_urn)
    headers = get_request_headers(user_linkedin)
    endpoint = "https://api.linkedin.com/v2/ugcPosts"

    logger.info(f"Posting to LinkedIn for {post.user} with payload: {payload}")
    try:
        response = requests.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        logger.info(f"Post successful for {post.user}")
        return response
    except requests.RequestException as e:
        logger.error(f"LinkedIn post failed: {e} | Response: {getattr(e.response, 'text', None)}")
        raise LinkedInPostError(f"Failed to post on LinkedIn: {e}")