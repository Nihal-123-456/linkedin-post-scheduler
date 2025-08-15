import inngest
import inngest.django
from .client import inngest_client
from .function import my_function

# Serve the Inngest endpoint
inngest_endpoint = inngest.django.serve(inngest_client, [my_function])