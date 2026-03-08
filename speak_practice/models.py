from django.db import models
from django.contrib.auth.models import User
from django.db.models import Prefetch, Q
from django.core.paginator import Paginator


SCENE_LEVEL_CHOICES = [
    ('beginner', 'Beginner'),
    ('intermediate', 'Intermediate'),
    ('advanced', 'Advanced'),
]

SCENE_SOURCE_CHOICES = [
    ('custom', 'Custom'),
    ('template', 'Template'),
    ('ai_generated', 'AI Generated'),
    ('fallback', 'Fallback'),
    ('emergency_fallback', 'Emergency Fallback'),
]


class ChatSessionManager(models.Manager):
    """聊天会话管理器 (Chat session manager)"""
    
    def get_user_sessions_with_message_count(self, user):
        """
        获取用户的会话及消息数量 (Get user sessions with message count)
        
        Args:
            user: 用户对象 (User object)
            
        Returns:
            QuerySet with annotated message count
        """
        return self.filter(user=user).annotate(
            message_count=models.Count('messages')
        ).order_by('-created_at')
    
    def get_recent_sessions(self, user, limit=10):
        """
        获取用户最近的会话 (Get user's recent sessions)
        
        Args:
            user: 用户对象 (User object)
            limit: 限制数量 (Limit count)
            
        Returns:
            QuerySet of recent sessions
        """
        return self.filter(user=user).order_by('-created_at')[:limit]
    
    def get_session_with_messages(self, session_id, user=None):
        """
        获取会话及其消息（优化查询）(Get session with messages - optimized query)
        
        Args:
            session_id: 会话ID (Session ID)
            user: 用户对象（可选）(User object - optional)
            
        Returns:
            ChatSession object with prefetched messages
        """
        queryset = self.select_related('user').prefetch_related(
            Prefetch(
                'messages',
                queryset=ChatMessage.objects.order_by('timestamp')
            )
        )
        
        if user:
            queryset = queryset.filter(user=user)
        
        return queryset.get(id=session_id)


class ChatMessageManager(models.Manager):
    """聊天消息管理器 (Chat message manager)"""
    
    def get_session_messages_paginated(self, session_id, page=1, per_page=50):
        """
        分页获取会话消息 (Get session messages with pagination)
        
        Args:
            session_id: 会话ID (Session ID)
            page: 页码 (Page number)
            per_page: 每页数量 (Items per page)
            
        Returns:
            Paginator object
        """
        messages = self.filter(session_id=session_id).select_related('session').order_by('timestamp')
        return Paginator(messages, per_page).get_page(page)
    
    def get_recent_messages(self, session_id, limit=20):
        """
        获取会话最近的消息 (Get recent messages for session)
        
        Args:
            session_id: 会话ID (Session ID)
            limit: 限制数量 (Limit count)
            
        Returns:
            QuerySet of recent messages
        """
        return self.filter(session_id=session_id).order_by('-timestamp')[:limit]
    
    def get_voice_messages(self, session_id=None):
        """
        获取语音消息 (Get voice messages)
        
        Args:
            session_id: 会话ID（可选）(Session ID - optional)
            
        Returns:
            QuerySet of voice messages
        """
        queryset = self.filter(input_method='voice').exclude(audio_duration__isnull=True)
        
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        
        return queryset.order_by('-timestamp')
    
    def get_messages_by_input_method(self, input_method, session_id=None):
        """
        按输入方法获取消息 (Get messages by input method)
        
        Args:
            input_method: 输入方法 (Input method)
            session_id: 会话ID（可选）(Session ID - optional)
            
        Returns:
            QuerySet of messages
        """
        queryset = self.filter(input_method=input_method)
        
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        
        return queryset.order_by('-timestamp')
    
    def search_messages(self, query, session_id=None, sender_type=None):
        """
        搜索消息内容 (Search message content)
        
        Args:
            query: 搜索查询 (Search query)
            session_id: 会话ID（可选）(Session ID - optional)
            sender_type: 发送者类型（可选）(Sender type - optional)
            
        Returns:
            QuerySet of matching messages
        """
        # 使用JSON字段搜索 (Use JSON field search)
        search_conditions = Q(message_content__icontains=query)
        
        # 如果是字符串查询，也搜索可能的文本字段 (If string query, also search possible text fields)
        if isinstance(query, str):
            search_conditions |= (
                Q(message_content__chinese_text__icontains=query) |
                Q(message_content__chinese__icontains=query) |
                Q(message_content__english_translation__icontains=query) |
                Q(message_content__original_english__icontains=query)
            )
        
        queryset = self.filter(search_conditions)
        
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        
        if sender_type:
            queryset = queryset.filter(sender_type=sender_type)
        
        return queryset.order_by('-timestamp')

class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户 (User)")
    scene_template = models.ForeignKey(
        'PracticeSceneTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions',
        verbose_name="场景模板 (Scene Template)"
    )
    scene = models.TextField(verbose_name="场景 (Scene)")
    scene_source = models.CharField(
        max_length=20,
        choices=SCENE_SOURCE_CHOICES,
        default='custom',
        verbose_name="场景来源 (Scene Source)"
    )
    scene_signature = models.CharField(
        max_length=40,
        blank=True,
        verbose_name="场景签名 (Scene Signature)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间 (Created At)")

    objects = ChatSessionManager()

    class Meta:
        ordering = ['-created_at']
        verbose_name = "聊天会话 (Chat Session)"
        verbose_name_plural = "聊天会话 (Chat Sessions)"
        indexes = [
            models.Index(fields=['user', '-created_at']),  # 用户会话查询优化 (User session query optimization)
            models.Index(fields=['user', 'scene_signature']),
            models.Index(fields=['-created_at']),  # 时间排序优化 (Time sorting optimization)
        ]

    def __str__(self):
        return f"ChatSession for {self.user.username} - {self.scene[:50]}{'...' if len(self.scene) > 50 else ''} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class ChatMessage(models.Model):
    SENDER_CHOICES = [
        ('user', 'User'),
        ('ai', 'AI'),
    ]
    
    INPUT_METHOD_CHOICES = [
        ('text', 'Text'),
        ('voice', 'Voice'),
        ('translation', 'Translation'),
    ]
    
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    sender_type = models.CharField(max_length=4, choices=SENDER_CHOICES)
    message_content = models.JSONField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # 新增字段用于支持语音消息 (New fields to support voice messages)
    audio_duration = models.FloatField(
        null=True, 
        blank=True, 
        help_text="音频时长（秒）(Audio duration in seconds)"
    )
    input_method = models.CharField(
        max_length=11, 
        choices=INPUT_METHOD_CHOICES,
        default='text',
        help_text="消息输入方式 (Message input method)"
    )

    objects = ChatMessageManager()

    class Meta:
        ordering = ['timestamp']
        verbose_name = "聊天消息 (Chat Message)"
        verbose_name_plural = "聊天消息 (Chat Messages)"
        indexes = [
            models.Index(fields=['session', 'timestamp']),  # 会话消息查询优化 (Session message query optimization)
            models.Index(fields=['sender_type', 'timestamp']),  # 发送者类型查询优化 (Sender type query optimization)
            models.Index(fields=['input_method', 'timestamp']),  # 输入方法查询优化 (Input method query optimization)
            models.Index(fields=['-timestamp']),  # 时间倒序查询优化 (Reverse time query optimization)
        ]

    def __str__(self):
        method_display = f" ({self.get_input_method_display()})" if self.input_method != 'text' else ""
        duration_display = f" [{self.audio_duration}s]" if self.audio_duration else ""
        return f"Message from {self.sender_type}{method_display}{duration_display} in session {self.session.id} at {self.timestamp}"


class PracticeSceneTemplate(models.Model):
    title = models.CharField(max_length=120, verbose_name="标题 (Title)")
    description = models.TextField(verbose_name="描述 (Description)")
    scene_prompt = models.TextField(verbose_name="场景提示词 (Scene Prompt)")
    level = models.CharField(
        max_length=20,
        choices=SCENE_LEVEL_CHOICES,
        default='beginner',
        verbose_name="难度 (Level)"
    )
    icon = models.CharField(
        max_length=50,
        default='fas fa-comments',
        verbose_name="图标 (Icon)"
    )
    category = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="分类 (Category)"
    )
    target_profile = models.TextField(
        blank=True,
        verbose_name="适用背景 (Target Profile)"
    )
    keywords = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="关键词 (Keywords)"
    )
    is_active = models.BooleanField(default=True, verbose_name="启用 (Active)")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="排序 (Sort Order)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间 (Created At)")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间 (Updated At)")

    class Meta:
        ordering = ['sort_order', 'title']
        verbose_name = "口语场景模板 (Practice Scene Template)"
        verbose_name_plural = "口语场景模板 (Practice Scene Templates)"

    def __str__(self):
        return f"{self.title} ({self.get_level_display()})"


class UserSceneExposure(models.Model):
    EXPOSURE_TYPE_CHOICES = [
        ('shown', 'Shown'),
        ('selected', 'Selected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scene_exposures')
    scene_template = models.ForeignKey(
        PracticeSceneTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exposures'
    )
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scene_exposures'
    )
    scene_title = models.CharField(max_length=120, blank=True)
    scene_text = models.TextField()
    scene_signature = models.CharField(max_length=40)
    scene_source = models.CharField(
        max_length=20,
        choices=SCENE_SOURCE_CHOICES,
        default='custom'
    )
    exposure_type = models.CharField(max_length=20, choices=EXPOSURE_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "用户场景记录 (User Scene Exposure)"
        verbose_name_plural = "用户场景记录 (User Scene Exposures)"
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'scene_signature']),
            models.Index(fields=['exposure_type', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} {self.exposure_type} {self.scene_title or self.scene_text[:40]}"
