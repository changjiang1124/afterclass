from django.contrib import admin
from .models import NameGenerationRequest, PageVisitStatistics, DailyStatistics

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

@admin.register(PageVisitStatistics)
class PageVisitStatisticsAdmin(admin.ModelAdmin):
    list_display = ['activity_type', 'ip_address', 'country', 'city', 'generated_name', 'share_platform', 'created_at']
    list_filter = ['activity_type', 'country', 'city', 'share_platform', 'created_at']
    search_fields = ['ip_address', 'generated_name', 'user_agent']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('活动信息', {
            'fields': ('activity_type', 'page_url', 'generated_name', 'request_id')
        }),
        ('位置信息', {
            'fields': ('ip_address', 'country', 'city', 'session_key')
        }),
        ('分享信息', {
            'fields': ('share_platform',)
        }),
        ('技术信息', {
            'fields': ('user_agent', 'response_time', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return False  # 只允许系统自动创建
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(DailyStatistics)
class DailyStatisticsAdmin(admin.ModelAdmin):
    list_display = ['date', 'page_visits', 'unique_visitors', 'unique_ips', 'name_generations', 'share_clicks', 'updated_at']
    list_filter = ['date']
    readonly_fields = ['updated_at']
    
    fieldsets = (
        ('日期', {
            'fields': ('date',)
        }),
        ('访问统计', {
            'fields': ('page_visits', 'unique_visitors', 'unique_ips')
        }),
        ('功能使用', {
            'fields': ('name_generations', 'name_card_generations', 'tts_requests', 'share_clicks')
        }),
        ('地理分布', {
            'fields': ('country_stats', 'city_stats'),
            'classes': ('collapse',)
        }),
        ('更新信息', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return False  # 只允许系统自动创建
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
