from django.contrib import admin
from .models import GeneratedText

# Register your models here.
@admin.register(GeneratedText)
class GeneratedTextAdmin(admin.ModelAdmin):
    list_display = ('topic', 'user', 'created_at')
    list_filter = ('created_at', 'topic')
    search_fields = ('topic', 'content')
    date_hierarchy = 'created_at'
