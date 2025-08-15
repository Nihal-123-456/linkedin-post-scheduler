import inngest
from datetime import datetime, timedelta
from .client import inngest_client
from django.utils import timezone
from posts.models import PostStatus, Post

# Create an Inngest function
@inngest_client.create_function(
    fn_id="my_function",
    # Event that triggers this function
    trigger=inngest.TriggerEvent(event="posts/post.scheduled"),
)
def my_function(ctx: inngest.Context) -> str:
    instance_id = ctx.event.data.get('object_id')
    qs = Post.objects.filter(id=instance_id)
    instance = qs.first()
    if 'linkedin' in instance.get_scheduled_platforms():
        start_time = ctx.step.run('start_time', get_time) # executing the workflow in a step by step way. Returns the current time in a float number format
        start_time = datetime.fromtimestamp(start_time, tz=timezone.get_current_timezone()) # converting the time back to a datetime object
        qs.update(share_start_at = start_time, status = PostStatus.SCHEDULED)

        ctx.step.sleep_until("sleeping_time", instance.share_at + timedelta(seconds=10))
        instance.perform_post_on_linkedin()

    end_time = ctx.step.run('end_time', get_time)
    end_time = datetime.fromtimestamp(end_time, tz=timezone.get_current_timezone())
    qs.update(share_end_at = end_time)
    ctx.logger.info(ctx.event)
    return "done"

def get_time():
    return timezone.now().timestamp() # timezone.now() returns a datetime objects. So we convert it to a floating value