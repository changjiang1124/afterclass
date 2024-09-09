from django.db import models

# Create your models here.

class Feature(models.Model):
    label = models.CharField(max_length=2)
    title = models.CharField(max_length=100)
    description = models.TextField()
    link = models.CharField(max_length=200)
    color = models.CharField(max_length=7, default='null')
    order = models.IntegerField(default=0)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['order']
