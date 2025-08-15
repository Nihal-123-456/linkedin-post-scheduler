import os
import sys
import pathlib
import django
from django.contrib.auth import get_user_model


PROJECT_ROOT = pathlib.Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_scheduler.settings')

django.setup()

User = get_user_model()
from posts.models import Post
post = Post.objects.get(id=22)
print(post.media.size)
# user = User.objects.get(username = 'kazi')
# user_linkedin = user.socialaccount_set.get(provider='linkedin')
# print(user_linkedin.uid)
# print(user_linkedin.socialtoken_set.first().token)