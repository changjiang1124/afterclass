from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class GeneratedText(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField()
    topic = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.topic} - {self.created_at.strftime('%d/%m/%Y')}"
