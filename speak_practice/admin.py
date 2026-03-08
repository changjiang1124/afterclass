from django.contrib import admin
from django.utils.html import format_html
from .models import ChatSession, ChatMessage, PracticeSceneTemplate, UserSceneExposure


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'scene_preview', 'scene_source', 'scene_template', 'created_at', 'message_count')
    list_filter = ('created_at', 'user', 'scene_source')
    search_fields = ('user__username', 'scene', 'scene_signature', 'scene_template__title')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    def scene_preview(self, obj):
        """显示场景的预览 (Display scene preview)"""
        return obj.scene[:100] + '...' if len(obj.scene) > 100 else obj.scene
    scene_preview.short_description = '场景预览 (Scene Preview)'
    
    def message_count(self, obj):
        """显示消息数量 (Display message count)"""
        return obj.messages.count()
    message_count.short_description = '消息数量 (Message Count)'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session_id', 'sender_type', 'input_method', 'audio_duration_display', 'content_preview', 'timestamp')
    list_filter = ('sender_type', 'input_method', 'timestamp')
    search_fields = ('session__user__username', 'message_content')
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)
    
    fieldsets = (
        ('基本信息 (Basic Information)', {
            'fields': ('session', 'sender_type', 'input_method')
        }),
        ('消息内容 (Message Content)', {
            'fields': ('message_content',)
        }),
        ('语音信息 (Voice Information)', {
            'fields': ('audio_duration',),
            'classes': ('collapse',)
        }),
        ('时间信息 (Time Information)', {
            'fields': ('timestamp',)
        }),
    )
    
    def content_preview(self, obj):
        """显示消息内容预览 (Display message content preview)"""
        content = str(obj.message_content)
        return content[:100] + '...' if len(content) > 100 else content
    content_preview.short_description = '内容预览 (Content Preview)'
    
    def audio_duration_display(self, obj):
        """显示音频时长 (Display audio duration)"""
        if obj.audio_duration:
            return f"{obj.audio_duration:.1f}s"
        return "-"
    audio_duration_display.short_description = '音频时长 (Audio Duration)'
    
    def session_id(self, obj):
        """显示会话ID (Display session ID)"""
        return obj.session.id
    session_id.short_description = '会话ID (Session ID)'


@admin.register(PracticeSceneTemplate)
class PracticeSceneTemplateAdmin(admin.ModelAdmin):
    list_display = ('title', 'level', 'category', 'is_active', 'sort_order', 'updated_at')
    list_filter = ('level', 'is_active', 'category')
    search_fields = ('title', 'description', 'scene_prompt', 'target_profile', 'keywords')
    list_editable = ('is_active', 'sort_order')
    ordering = ('sort_order', 'title')


@admin.register(UserSceneExposure)
class UserSceneExposureAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'scene_title', 'scene_source', 'exposure_type', 'scene_template', 'created_at')
    list_filter = ('scene_source', 'exposure_type', 'created_at')
    search_fields = ('user__username', 'scene_title', 'scene_text', 'scene_signature')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
