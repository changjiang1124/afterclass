from django.contrib import admin
from .models import NameGenerationRequest

@admin.register(NameGenerationRequest)
class NameGenerationRequestAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'surname', 'gender', 'generated_chinese_name', 'personality_trait', 'preferred_style', 'created_at']
    list_filter = ['gender', 'personality_trait', 'preferred_style', 'created_at']
    search_fields = ['first_name', 'surname', 'generated_chinese_name']
    readonly_fields = ['created_at', 'ip_address']
    
    fieldsets = (
        ('User Information', {
            'fields': ('first_name', 'surname', 'gender', 'date_of_birth', 'personality_trait', 'preferred_style')
        }),
        ('Generated Name', {
            'fields': ('generated_chinese_name', 'name_pinyin', 'name_meaning')
        }),
        ('Metadata', {
            'fields': ('created_at', 'ip_address'),
            'classes': ('collapse',)
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
