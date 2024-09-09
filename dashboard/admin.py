from django.contrib import admin
from .models import Feature

@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ('title', 'label', 'order')
    list_editable = ('order',)

# Register your models here.
