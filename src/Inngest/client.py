import logging
import inngest

# Create an Inngest client
inngest_client = inngest.Inngest(
    app_id="post_scheduler",
    logger=logging.getLogger("gunicorn"),
)

