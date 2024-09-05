from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Chatbot(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    banner = models.ImageField(upload_to='banners/')
    prompt = models.TextField()

    def __str__(self):
        return self.title

class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    chatbot = models.ForeignKey(Chatbot, on_delete=models.CASCADE)
    message = models.TextField()
    response = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']
