"""
数据库查询优化测试 (Database query optimization tests)
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.cache import cache
from datetime import datetime, timedelta

from speak_practice.models import ChatSession, ChatMessage
from speak_practice.query_utils import ChatQueryOptimizer, CacheManager
from speak_practice.message_utils import MessageContentFormatter


class ChatQueryOptimizerTest(TestCase):
    """聊天查询优化器测试 (Chat query optimizer tests)"""
    
    def setUp(self):
        """设置测试数据 (Set up test data)"""
        # 清除缓存 (Clear cache)
        cache.clear()
        
        # 创建测试用户 (Create test user)
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 创建测试会话 (Create test session)
        self.session = ChatSession.objects.create(
            user=self.user,
            scene='测试场景：在餐厅点餐'
        )
        
        # 创建测试消息 (Create test messages)
        self.create_test_messages()
    
    def create_test_messages(self):
        """创建测试消息 (Create test messages)"""
        # 用户文本消息 (User text message)
        ChatMessage.objects.create(
            session=self.session,
            sender_type='user',
            message_content=MessageContentFormatter.serialize_user_text_message("你好"),
            input_method='text'
        )
        
        # AI回复消息 (AI reply message)
        ChatMessage.objects.create(
            session=self.session,
            sender_type='ai',
            message_content=MessageContentFormatter.serialize_ai_message(
                "你好！欢迎来到餐厅。",
                tts_generated=True
            )
        )
        
        # 用户语音消息 (User voice message)
        ChatMessage.objects.create(
            session=self.session,
            sender_type='user',
            message_content=MessageContentFormatter.serialize_user_voice_message(
                "我想要一份宫保鸡丁",
                "I want a Kung Pao Chicken",
                3.5
            ),
            input_method='voice',
            audio_duration=3.5
        )
        
        # 用户翻译消息 (User translation message)
        ChatMessage.objects.create(
            session=self.session,
            sender_type='user',
            message_content=MessageContentFormatter.serialize_user_translation_message(
                "请给我菜单",
                "Please give me the menu"
            ),
            input_method='translation'
        )
    
    def test_get_user_dashboard_data(self):
        """测试获取用户仪表板数据 (Test getting user dashboard data)"""
        dashboard_data = ChatQueryOptimizer.get_user_dashboard_data(self.user)
        
        self.assertIn('session_count', dashboard_data)
        self.assertIn('message_count', dashboard_data)
        self.assertIn('voice_message_count', dashboard_data)
        self.assertIn('recent_sessions', dashboard_data)
        
        self.assertEqual(dashboard_data['session_count'], 1)
        self.assertEqual(dashboard_data['message_count'], 4)
        self.assertEqual(dashboard_data['voice_message_count'], 1)
        self.assertEqual(len(dashboard_data['recent_sessions']), 1)
    
    def test_get_user_dashboard_data_caching(self):
        """测试用户仪表板数据缓存 (Test user dashboard data caching)"""
        # 第一次调用 (First call)
        data1 = ChatQueryOptimizer.get_user_dashboard_data(self.user)
        
        # 第二次调用应该从缓存获取 (Second call should get from cache)
        data2 = ChatQueryOptimizer.get_user_dashboard_data(self.user)
        
        self.assertEqual(data1, data2)
        
        # 验证缓存键存在 (Verify cache key exists)
        cache_key = f"user_dashboard_{self.user.id}"
        cached_data = cache.get(cache_key)
        self.assertIsNotNone(cached_data)
    
    def test_get_session_with_lazy_messages(self):
        """测试获取会话及懒加载消息 (Test getting session with lazy messages)"""
        result = ChatQueryOptimizer.get_session_with_lazy_messages(
            self.session.id, 
            self.user, 
            initial_message_count=2
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result['session'].id, self.session.id)
        self.assertEqual(len(result['messages']), 2)
        self.assertTrue(result['has_more_messages'])
        self.assertEqual(result['total_message_count'], 4)
        self.assertEqual(result['loaded_message_count'], 2)
    
    def test_get_messages_before_timestamp(self):
        """测试获取时间戳之前的消息 (Test getting messages before timestamp)"""
        # 获取最新消息的时间戳 (Get latest message timestamp)
        latest_message = ChatMessage.objects.filter(session=self.session).order_by('-timestamp').first()
        
        # 获取该时间戳之前的消息 (Get messages before that timestamp)
        messages = ChatQueryOptimizer.get_messages_before_timestamp(
            self.session.id,
            latest_message.timestamp,
            limit=2
        )
        
        self.assertEqual(len(messages), 2)
        # 验证消息按时间正序排列 (Verify messages are in chronological order)
        self.assertLess(messages[0].timestamp, messages[1].timestamp)
    
    def test_get_session_statistics(self):
        """测试获取会话统计信息 (Test getting session statistics)"""
        stats = ChatQueryOptimizer.get_session_statistics(self.session.id)
        
        expected_stats = {
            'total_messages': 4,
            'user_messages': 3,
            'ai_messages': 1,
            'voice_messages': 1,
            'text_messages': 2,  # AI message also counts as text (default input_method)
            'translation_messages': 1
        }
        
        for key, expected_value in expected_stats.items():
            self.assertEqual(stats[key], expected_value)
        
        # 验证平均音频时长 (Verify average audio duration)
        self.assertEqual(stats['avg_audio_duration'], 3.5)
    
    def test_search_user_messages(self):
        """测试搜索用户消息 (Test searching user messages)"""
        # 搜索中文内容 (Search Chinese content)
        results = ChatQueryOptimizer.search_user_messages(self.user, "宫保鸡丁")
        self.assertEqual(len(results.object_list), 1)
        
        # 搜索英文内容 (Search English content)
        results = ChatQueryOptimizer.search_user_messages(self.user, "Kung Pao")
        self.assertEqual(len(results.object_list), 1)
        
        # 搜索不存在的内容 (Search non-existent content)
        results = ChatQueryOptimizer.search_user_messages(self.user, "不存在的内容")
        self.assertEqual(len(results.object_list), 0)
    
    def test_get_user_activity_summary(self):
        """测试获取用户活动摘要 (Test getting user activity summary)"""
        summary = ChatQueryOptimizer.get_user_activity_summary(self.user, days=30)
        
        expected_keys = [
            'period_days', 'sessions_created', 'messages_sent',
            'voice_messages_sent', 'translation_messages_sent', 'ai_responses_received'
        ]
        
        for key in expected_keys:
            self.assertIn(key, summary)
        
        self.assertEqual(summary['period_days'], 30)
        self.assertEqual(summary['sessions_created'], 1)
        self.assertEqual(summary['messages_sent'], 3)  # 3 user messages
        self.assertEqual(summary['voice_messages_sent'], 1)
        self.assertEqual(summary['translation_messages_sent'], 1)
        self.assertEqual(summary['ai_responses_received'], 1)


class ChatSessionManagerTest(TestCase):
    """聊天会话管理器测试 (Chat session manager tests)"""
    
    def setUp(self):
        """设置测试数据 (Set up test data)"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 创建多个会话 (Create multiple sessions)
        self.session1 = ChatSession.objects.create(
            user=self.user,
            scene='场景1'
        )
        self.session2 = ChatSession.objects.create(
            user=self.user,
            scene='场景2'
        )
        
        # 为会话添加消息 (Add messages to sessions)
        for i in range(3):
            ChatMessage.objects.create(
                session=self.session1,
                sender_type='user',
                message_content=MessageContentFormatter.serialize_user_text_message(f"消息{i}")
            )
        
        for i in range(2):
            ChatMessage.objects.create(
                session=self.session2,
                sender_type='user',
                message_content=MessageContentFormatter.serialize_user_text_message(f"消息{i}")
            )
    
    def test_get_user_sessions_with_message_count(self):
        """测试获取用户会话及消息数量 (Test getting user sessions with message count)"""
        sessions = ChatSession.objects.get_user_sessions_with_message_count(self.user)
        
        self.assertEqual(sessions.count(), 2)
        
        # 验证消息数量注解 (Verify message count annotation)
        session_with_3_messages = sessions.filter(id=self.session1.id).first()
        session_with_2_messages = sessions.filter(id=self.session2.id).first()
        
        self.assertEqual(session_with_3_messages.message_count, 3)
        self.assertEqual(session_with_2_messages.message_count, 2)
    
    def test_get_recent_sessions(self):
        """测试获取最近会话 (Test getting recent sessions)"""
        recent_sessions = ChatSession.objects.get_recent_sessions(self.user, limit=1)
        
        self.assertEqual(len(recent_sessions), 1)
        # 应该返回最新创建的会话 (Should return the most recently created session)
        self.assertEqual(recent_sessions[0].id, self.session2.id)
    
    def test_get_session_with_messages(self):
        """测试获取会话及消息 (Test getting session with messages)"""
        session = ChatSession.objects.get_session_with_messages(self.session1.id, self.user)
        
        self.assertEqual(session.id, self.session1.id)
        # 验证消息已预取 (Verify messages are prefetched)
        messages = list(session.messages.all())
        self.assertEqual(len(messages), 3)


class ChatMessageManagerTest(TestCase):
    """聊天消息管理器测试 (Chat message manager tests)"""
    
    def setUp(self):
        """设置测试数据 (Set up test data)"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.session = ChatSession.objects.create(
            user=self.user,
            scene='测试场景'
        )
        
        # 创建不同类型的消息 (Create different types of messages)
        ChatMessage.objects.create(
            session=self.session,
            sender_type='user',
            message_content=MessageContentFormatter.serialize_user_text_message("文本消息"),
            input_method='text'
        )
        
        ChatMessage.objects.create(
            session=self.session,
            sender_type='user',
            message_content=MessageContentFormatter.serialize_user_voice_message(
                "语音消息", "Voice message", 2.5
            ),
            input_method='voice',
            audio_duration=2.5
        )
        
        ChatMessage.objects.create(
            session=self.session,
            sender_type='user',
            message_content=MessageContentFormatter.serialize_user_translation_message(
                "翻译消息", "Translation message"
            ),
            input_method='translation'
        )
    
    def test_get_session_messages_paginated(self):
        """测试分页获取会话消息 (Test getting session messages with pagination)"""
        page = ChatMessage.objects.get_session_messages_paginated(
            self.session.id, page=1, per_page=2
        )
        
        self.assertEqual(len(page.object_list), 2)
        self.assertTrue(page.has_next())
        self.assertFalse(page.has_previous())
    
    def test_get_recent_messages(self):
        """测试获取最近消息 (Test getting recent messages)"""
        recent_messages = ChatMessage.objects.get_recent_messages(self.session.id, limit=2)
        
        self.assertEqual(len(recent_messages), 2)
        # 验证按时间倒序排列 (Verify reverse chronological order)
        self.assertGreater(recent_messages[0].timestamp, recent_messages[1].timestamp)
    
    def test_get_voice_messages(self):
        """测试获取语音消息 (Test getting voice messages)"""
        voice_messages = ChatMessage.objects.get_voice_messages(self.session.id)
        
        self.assertEqual(voice_messages.count(), 1)
        self.assertEqual(voice_messages.first().input_method, 'voice')
        self.assertIsNotNone(voice_messages.first().audio_duration)
    
    def test_get_messages_by_input_method(self):
        """测试按输入方法获取消息 (Test getting messages by input method)"""
        text_messages = ChatMessage.objects.get_messages_by_input_method('text', self.session.id)
        voice_messages = ChatMessage.objects.get_messages_by_input_method('voice', self.session.id)
        translation_messages = ChatMessage.objects.get_messages_by_input_method('translation', self.session.id)
        
        self.assertEqual(text_messages.count(), 1)
        self.assertEqual(voice_messages.count(), 1)
        self.assertEqual(translation_messages.count(), 1)
    
    def test_search_messages(self):
        """测试搜索消息 (Test searching messages)"""
        # 搜索文本消息 (Search text messages)
        results = ChatMessage.objects.search_messages("文本消息", self.session.id)
        self.assertEqual(results.count(), 1)
        
        # 搜索语音消息的英文翻译 (Search English translation of voice message)
        results = ChatMessage.objects.search_messages("Voice message", self.session.id)
        self.assertEqual(results.count(), 1)
        
        # 搜索翻译消息 (Search translation messages)
        results = ChatMessage.objects.search_messages("Translation message", self.session.id)
        self.assertEqual(results.count(), 1)


class CacheManagerTest(TestCase):
    """缓存管理器测试 (Cache manager tests)"""
    
    def setUp(self):
        """设置测试数据 (Set up test data)"""
        cache.clear()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.session = ChatSession.objects.create(
            user=self.user,
            scene='测试场景'
        )
    
    def test_invalidate_user_cache(self):
        """测试清除用户缓存 (Test invalidating user cache)"""
        # 先设置一些缓存 (First set some cache)
        cache.set(f"user_dashboard_{self.user.id}", {"test": "data"}, 300)
        cache.set(f"user_activity_{self.user.id}_30", {"test": "data"}, 300)
        
        # 验证缓存存在 (Verify cache exists)
        self.assertIsNotNone(cache.get(f"user_dashboard_{self.user.id}"))
        
        # 清除缓存 (Invalidate cache)
        CacheManager.invalidate_user_cache(self.user.id)
        
        # 验证缓存已清除 (Verify cache is cleared)
        self.assertIsNone(cache.get(f"user_dashboard_{self.user.id}"))
        self.assertIsNone(cache.get(f"user_activity_{self.user.id}_30"))
    
    def test_invalidate_session_cache(self):
        """测试清除会话缓存 (Test invalidating session cache)"""
        # 先设置缓存 (First set cache)
        cache.set(f"session_stats_{self.session.id}", {"test": "data"}, 300)
        
        # 验证缓存存在 (Verify cache exists)
        self.assertIsNotNone(cache.get(f"session_stats_{self.session.id}"))
        
        # 清除缓存 (Invalidate cache)
        CacheManager.invalidate_session_cache(self.session.id)
        
        # 验证缓存已清除 (Verify cache is cleared)
        self.assertIsNone(cache.get(f"session_stats_{self.session.id}"))
    
    def test_warm_up_user_cache(self):
        """测试预热用户缓存 (Test warming up user cache)"""
        # 预热缓存 (Warm up cache)
        CacheManager.warm_up_user_cache(self.user)
        
        # 验证缓存已设置 (Verify cache is set)
        self.assertIsNotNone(cache.get(f"user_dashboard_{self.user.id}"))
        self.assertIsNotNone(cache.get(f"user_activity_{self.user.id}_7"))
        self.assertIsNotNone(cache.get(f"user_activity_{self.user.id}_30"))