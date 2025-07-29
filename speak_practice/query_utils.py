"""
数据库查询优化工具 (Database query optimization utilities)

This module provides utilities for optimized database queries
for chat sessions and messages.
"""

from django.db.models import Count, Q, Prefetch
from django.core.paginator import Paginator
from django.core.cache import cache
from .models import ChatSession, ChatMessage


class ChatQueryOptimizer:
    """聊天查询优化器 (Chat query optimizer)"""
    
    @staticmethod
    def get_user_dashboard_data(user, cache_timeout=300):
        """
        获取用户仪表板数据（带缓存）(Get user dashboard data with caching)
        
        Args:
            user: 用户对象 (User object)
            cache_timeout: 缓存超时时间（秒）(Cache timeout in seconds)
            
        Returns:
            Dict containing dashboard data
        """
        cache_key = f"user_dashboard_{user.id}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        # 获取用户统计数据 (Get user statistics)
        session_count = ChatSession.objects.filter(user=user).count()
        message_count = ChatMessage.objects.filter(session__user=user).count()
        voice_message_count = ChatMessage.objects.filter(
            session__user=user,
            input_method='voice'
        ).count()
        
        # 获取最近的会话 (Get recent sessions)
        recent_sessions = ChatSession.objects.get_recent_sessions(user, limit=5)
        
        dashboard_data = {
            'session_count': session_count,
            'message_count': message_count,
            'voice_message_count': voice_message_count,
            'recent_sessions': list(recent_sessions.values(
                'id', 'scene', 'created_at'
            ))
        }
        
        cache.set(cache_key, dashboard_data, cache_timeout)
        return dashboard_data
    
    @staticmethod
    def get_session_with_lazy_messages(session_id, user=None, initial_message_count=20):
        """
        获取会话及懒加载消息 (Get session with lazy-loaded messages)
        
        Args:
            session_id: 会话ID (Session ID)
            user: 用户对象（可选）(User object - optional)
            initial_message_count: 初始消息数量 (Initial message count)
            
        Returns:
            Dict containing session and initial messages
        """
        try:
            # 获取会话信息 (Get session info)
            session_query = ChatSession.objects.select_related('user')
            if user:
                session_query = session_query.filter(user=user)
            
            session = session_query.get(id=session_id)
            
            # 获取初始消息 (Get initial messages)
            initial_messages = ChatMessage.objects.filter(
                session_id=session_id
            ).order_by('-timestamp')[:initial_message_count]
            
            # 反转消息顺序以按时间正序显示 (Reverse message order for chronological display)
            initial_messages = list(reversed(initial_messages))
            
            # 检查是否还有更多消息 (Check if there are more messages)
            total_message_count = ChatMessage.objects.filter(session_id=session_id).count()
            has_more_messages = total_message_count > initial_message_count
            
            return {
                'session': session,
                'messages': initial_messages,
                'has_more_messages': has_more_messages,
                'total_message_count': total_message_count,
                'loaded_message_count': len(initial_messages)
            }
            
        except ChatSession.DoesNotExist:
            return None
    
    @staticmethod
    def get_messages_before_timestamp(session_id, before_timestamp, limit=20):
        """
        获取指定时间戳之前的消息（用于懒加载）(Get messages before timestamp for lazy loading)
        
        Args:
            session_id: 会话ID (Session ID)
            before_timestamp: 时间戳 (Timestamp)
            limit: 限制数量 (Limit count)
            
        Returns:
            List of messages
        """
        messages = ChatMessage.objects.filter(
            session_id=session_id,
            timestamp__lt=before_timestamp
        ).order_by('-timestamp')[:limit]
        
        # 反转消息顺序 (Reverse message order)
        return list(reversed(messages))
    
    @staticmethod
    def get_session_statistics(session_id):
        """
        获取会话统计信息 (Get session statistics)
        
        Args:
            session_id: 会话ID (Session ID)
            
        Returns:
            Dict containing session statistics
        """
        cache_key = f"session_stats_{session_id}"
        cached_stats = cache.get(cache_key)
        
        if cached_stats:
            return cached_stats
        
        # 计算各种统计信息 (Calculate various statistics)
        message_stats = ChatMessage.objects.filter(session_id=session_id).aggregate(
            total_messages=Count('id'),
            user_messages=Count('id', filter=Q(sender_type='user')),
            ai_messages=Count('id', filter=Q(sender_type='ai')),
            voice_messages=Count('id', filter=Q(input_method='voice')),
            text_messages=Count('id', filter=Q(input_method='text')),
            translation_messages=Count('id', filter=Q(input_method='translation'))
        )
        
        # 计算平均音频时长 (Calculate average audio duration)
        voice_messages = ChatMessage.objects.filter(
            session_id=session_id,
            input_method='voice',
            audio_duration__isnull=False
        )
        
        if voice_messages.exists():
            total_duration = sum(msg.audio_duration for msg in voice_messages)
            avg_audio_duration = total_duration / voice_messages.count()
        else:
            avg_audio_duration = 0
        
        stats = {
            **message_stats,
            'avg_audio_duration': avg_audio_duration
        }
        
        cache.set(cache_key, stats, 600)  # 缓存10分钟 (Cache for 10 minutes)
        return stats
    
    @staticmethod
    def search_user_messages(user, query, page=1, per_page=20):
        """
        搜索用户消息 (Search user messages)
        
        Args:
            user: 用户对象 (User object)
            query: 搜索查询 (Search query)
            page: 页码 (Page number)
            per_page: 每页数量 (Items per page)
            
        Returns:
            Paginated search results
        """
        # 构建搜索条件 (Build search conditions)
        search_conditions = Q(message_content__icontains=query)
        
        # 搜索特定字段 (Search specific fields)
        if isinstance(query, str) and query.strip():
            search_conditions |= (
                Q(message_content__chinese_text__icontains=query) |
                Q(message_content__chinese__icontains=query) |
                Q(message_content__english_translation__icontains=query) |
                Q(message_content__original_english__icontains=query)
            )
        
        # 执行搜索 (Execute search)
        messages = ChatMessage.objects.filter(
            session__user=user
        ).filter(search_conditions).select_related(
            'session'
        ).order_by('-timestamp')
        
        return Paginator(messages, per_page).get_page(page)
    
    @staticmethod
    def get_user_activity_summary(user, days=30):
        """
        获取用户活动摘要 (Get user activity summary)
        
        Args:
            user: 用户对象 (User object)
            days: 天数 (Number of days)
            
        Returns:
            Dict containing activity summary
        """
        from datetime import datetime, timedelta
        
        cache_key = f"user_activity_{user.id}_{days}"
        cached_summary = cache.get(cache_key)
        
        if cached_summary:
            return cached_summary
        
        # 计算日期范围 (Calculate date range)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 获取活动统计 (Get activity statistics)
        sessions_in_period = ChatSession.objects.filter(
            user=user,
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        messages_in_period = ChatMessage.objects.filter(
            session__user=user,
            timestamp__gte=start_date,
            timestamp__lte=end_date
        )
        
        activity_summary = {
            'period_days': days,
            'sessions_created': sessions_in_period.count(),
            'messages_sent': messages_in_period.filter(sender_type='user').count(),
            'voice_messages_sent': messages_in_period.filter(
                sender_type='user',
                input_method='voice'
            ).count(),
            'translation_messages_sent': messages_in_period.filter(
                sender_type='user',
                input_method='translation'
            ).count(),
            'ai_responses_received': messages_in_period.filter(sender_type='ai').count()
        }
        
        cache.set(cache_key, activity_summary, 3600)  # 缓存1小时 (Cache for 1 hour)
        return activity_summary


class CacheManager:
    """缓存管理器 (Cache manager)"""
    
    @staticmethod
    def invalidate_user_cache(user_id):
        """
        清除用户相关缓存 (Invalidate user-related cache)
        
        Args:
            user_id: 用户ID (User ID)
        """
        cache_keys = [
            f"user_dashboard_{user_id}",
            f"user_activity_{user_id}_30",
            f"user_activity_{user_id}_7"
        ]
        
        cache.delete_many(cache_keys)
    
    @staticmethod
    def invalidate_session_cache(session_id):
        """
        清除会话相关缓存 (Invalidate session-related cache)
        
        Args:
            session_id: 会话ID (Session ID)
        """
        cache_keys = [
            f"session_stats_{session_id}"
        ]
        
        cache.delete_many(cache_keys)
    
    @staticmethod
    def warm_up_user_cache(user):
        """
        预热用户缓存 (Warm up user cache)
        
        Args:
            user: 用户对象 (User object)
        """
        # 预加载仪表板数据 (Preload dashboard data)
        ChatQueryOptimizer.get_user_dashboard_data(user)
        
        # 预加载活动摘要 (Preload activity summary)
        ChatQueryOptimizer.get_user_activity_summary(user, days=7)
        ChatQueryOptimizer.get_user_activity_summary(user, days=30)