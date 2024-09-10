from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

# Create your models here.

class Story(models.Model):
    title = models.CharField(max_length=200)
    excerpt = models.TextField()
    content = CKEditor5Field()
    banner = models.ImageField(upload_to='story_banners/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "Stories"
