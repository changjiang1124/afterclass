from django.db import models

# Create your models here.

class Feature(models.Model):
    CATEGORY_CHOICES = (
        ('typing', '汉字输入'),
        ('reading', '阅读理解'),
        ('listening', '听力练习'),
        ('speaking', '口语练习'),
        ('other', '其他工具'),
    )
    
    label = models.CharField(max_length=2)
    title = models.CharField(max_length=100)
    description = models.TextField()
    link = models.CharField(max_length=200)
    color = models.CharField(max_length=7, default='null')
    order = models.IntegerField(default=0)
    icon = models.CharField(max_length=50, default='fas fa-star', help_text='Font Awesome 图标类名')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['category', 'order']
