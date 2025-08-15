from django.db import models
from django.contrib.auth import get_user_model
from linkedin.linkedin import post_on_linkedin
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.files.storage import default_storage
from Inngest.client import inngest_client
import inngest
import logging
# Create your models here.
User = get_user_model()
logger = logging.getLogger(__name__) # instead of crashing the admin save process we trace our errors to the logs

# for defining a set of pre-defined choices for the status model field
class PostStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft' # value('draft'), label('Draft')
    POSTED = 'posted', 'Posted'
    FAILED = 'failed', 'Failed'
    SCHEDULED = 'scheduled', 'Scheduled'

class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(null=True, blank=True)
    share_on_linkedin = models.BooleanField(default=False)

    share_now = models.BooleanField(default=False)
    share_at = models.DateTimeField(auto_now=False, auto_now_add=False, null=True, blank=True)

    share_start_at = models.DateTimeField(auto_now=False, auto_now_add=False, null=True, blank=True)
    share_end_at = models.DateTimeField(auto_now=False, auto_now_add=False, null=True, blank=True)

    shared_at_linkedin = models.DateTimeField(auto_now=False, auto_now_add=False, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=64, choices=PostStatus.choices, default=PostStatus.DRAFT) # programatically accessing the choices
    
    article_url = models.URLField(null=True, blank=True)
    article_title = models.CharField(max_length=64, null=True, blank=True)
    media = models.FileField(null=True, blank=True)
    
    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        if self.media and self.media.size > 52428800:
            raise ValidationError({'media' : 'File size cannot be more than 50 MB'})
        if not any([self.content, self.article_url, self.media]):
            raise ValidationError("Post must have at least text, article, or media.")
        if self.share_on_linkedin and self.shared_at_linkedin:
            raise ValidationError({'share_on_linkedin' : 'This post has already been shared.'})
        if self.share_at and self.share_at <= timezone.now():
            raise ValidationError({'share_at': 'Scheduled time must be in the future.'})

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if self.share_now:
            self.share_at = timezone.now()
        super().save(*args, **kwargs)
        if self.share_on_linkedin and (is_new or not self.shared_at_linkedin):
            # calling the inngest_event to trigger the associated function
            inngest_client.send_sync(
                inngest.Event(
                    name = "posts/post.scheduled",
                    id = f"posts/post.scheduled{self.id}",
                    data={"object_id": self.id},
                )
            ) 
    
    def perform_post_on_linkedin(self):
        try:
            post_on_linkedin(self)
            self.share_on_linkedin = False
            self.shared_at_linkedin = timezone.now()
            self.status = PostStatus.POSTED
            self.save(update_fields = ['share_on_linkedin', 'shared_at_linkedin', 'status'])
        except Exception as e:
            logger.error(f"LinkedIn post failed for Post ID {self.id}: {e}", exc_info=True) # the exc_info enables stack traces in our logs
            self.status = PostStatus.FAILED
    
    # default_storage is used to get the path of our media file for uploading it on linkedin. It is also compatible with cloud backends like AWS
    def get_media_path(self):
        if self.media and default_storage.exists(self.media.name):
            return default_storage.path(self.media.name)
        return None
    
    def get_scheduled_platforms(self):
        scheduled_platforms = []
        if self.share_on_linkedin:
            scheduled_platforms.append('linkedin')
        return scheduled_platforms
