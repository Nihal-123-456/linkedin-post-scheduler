from django.contrib import admin
from .models import Post

# Register your models here.
class PostAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj):
        if obj and obj.shared_at_linkedin:
            return [field.name for field in obj._meta.fields] # making all the fields read-only when a post has been uploaded to linkedin
        else:
            return ['shared_at_linkedin', 'share_start_at', 'share_end_at', 'status']

admin.site.register(Post, PostAdmin)