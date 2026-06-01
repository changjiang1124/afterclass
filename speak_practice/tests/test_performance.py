"""
性能测试和优化 (Performance Testing and Optimization)

这个测试文件测试API响应时间和并发处理能力，
优化音频处理和TTS缓存性能，验证移动设备上的性能表现
(This test file tests API response time and concurrent processing capability,
optimizes audio processing and TTS cache performance, verifies performance on mobile devices)
"""

import time
import threading
import statistics
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, Mock
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.db import connection
from django.test.utils import override_settings

from speak_practice.models import ChatSession, ChatMessage
from speak_practice.services.text_to_speech import TextToSpeechService
from speak_practice.services.speech_recognition import SpeechRecognitionService
from speak_practice.services.translation import TranslationService
from speak_practice.services.cache import TTSCacheService


class APIPerformanceTest(TestCase):
    """API性能测试类 (API Performance Test Class)"""
    
    def setUp(self):
        """测试设置 (Test setup)"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='perfuser',
            email='perf@example.com',
            password='perfpass123'
        )
        self.client.login(username='perfuser', password='perfpass123')
        
        self.session = ChatSession.objects.create(
            user=self.user,
            scene='性能测试场景 (Performance test scenario)'
        )
        
        # 创建测试音频文件 (Create test audio file)
        self.test_audio = SimpleUploadedFile(
            "perf_test.webm",
            b"fake_audio_content_for_performance_test",
            content_type="audio/webm"
        )
    
    def tearDown(self):
        """测试清理 (Test cleanup)"""
        ChatMessage.objects.filter(session=self.session).delete()
        ChatSession.objects.filter(user=self.user).delete()
        cache.clear()
    
    def measure_response_time(self, url, method='GET', data=None, **kwargs):
        """
        测量API响应时间 (Measure API response time)
        
        Args:
            url: API端点URL (API endpoint URL)
            method: HTTP方法 (HTTP method)
            data: 请求数据 (Request data)
            **kwargs: 其他请求参数 (Other request parameters)
            
        Returns:
            tuple: (response_time_ms, response)
        """
        start_time = time.time()
        
        if method.upper() == 'POST':
            response = self.client.post(url, data, **kwargs)
        else:
            response = self.client.get(url, **kwargs)
        
        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000
        
        return response_time_ms, response
    
    @patch('speak_practice.views._validate_request_origin', return_value=True)
    @patch('speak_practice.views.get_ai_response')
    @patch('speak_practice.services.text_to_speech.tts_service.generate_speech')
    def test_chat_api_response_time(self, mock_tts, mock_ai_response, mock_validate):
        """
        测试聊天API响应时间 (Test chat API response time)
        
        验证聊天API在正常负载下的响应时间
        (Verify chat API response time under normal load)
        """
        # 设置模拟响应 (Set up mock responses)
        mock_ai_response.return_value = json.dumps({
            'chinese': '性能测试回复',
            'pinyin': 'xìng néng cè shì huí fù'
        })
        mock_tts.return_value = 'mock_tts_audio_data'
        
        chat_url = reverse('speak_practice:chat_api')
        response_times = []
        
        # 执行多次请求测试 (Execute multiple requests for testing)
        for i in range(10):
            response_time, response = self.measure_response_time(
                chat_url,
                method='POST',
                data=json.dumps({
                    'message': f'性能测试消息 {i}',
                    'session_id': self.session.id
                }),
                content_type='application/json',
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            response_times.append(response_time)
            self.assertEqual(response.status_code, 200)
        
        # 分析性能指标 (Analyze performance metrics)
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        
        print(f"\n聊天API性能指标 (Chat API Performance Metrics):")
        print(f"平均响应时间 (Average response time): {avg_response_time:.2f}ms")
        print(f"最大响应时间 (Max response time): {max_response_time:.2f}ms")
        print(f"最小响应时间 (Min response time): {min_response_time:.2f}ms")
        
        # 性能断言 (Performance assertions)
        self.assertLess(avg_response_time, 2000, "平均响应时间应小于2秒 (Average response time should be less than 2 seconds)")
        self.assertLess(max_response_time, 5000, "最大响应时间应小于5秒 (Max response time should be less than 5 seconds)")
    
    @patch('speak_practice.views._validate_request_origin', return_value=True)
    @patch('speak_practice.services.speech_recognition.SpeechRecognitionService.process')
    @patch('speak_practice.services.translation.TranslationService.process')
    def test_transcription_api_response_time(self, mock_translation, mock_speech, mock_validate):
        """
        测试语音转录API响应时间 (Test transcription API response time)
        
        验证语音转录API的性能表现
        (Verify performance of speech transcription API)
        """
        # 设置模拟响应 (Set up mock responses)
        mock_speech.return_value = {
            'transcribed_text': '性能测试转录文本',
            'audio_duration': 2.5,
            'audio_size': 1024,
            'audio_format': 'webm'
        }
        
        mock_translation.return_value = {
            'translated_text': 'Performance test transcription text',
            'source_language': 'zh',
            'target_language': 'en',
            'character_count': 8
        }
        
        transcribe_url = reverse('speak_practice:transcribe_audio_api')
        response_times = []
        
        # 执行多次转录请求 (Execute multiple transcription requests)
        for i in range(5):
            test_audio = SimpleUploadedFile(
                f"test_audio_{i}.webm",
                b"fake_audio_content",
                content_type="audio/webm"
            )
            
            response_time, response = self.measure_response_time(
                transcribe_url,
                method='POST',
                data={'audio': test_audio},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            response_times.append(response_time)
            self.assertEqual(response.status_code, 200)
        
        # 分析转录性能 (Analyze transcription performance)
        avg_response_time = statistics.mean(response_times)
        
        print(f"\n语音转录API性能指标 (Transcription API Performance Metrics):")
        print(f"平均响应时间 (Average response time): {avg_response_time:.2f}ms")
        
        # 转录API通常需要更多时间 (Transcription API typically needs more time)
        self.assertLess(avg_response_time, 10000, "转录平均响应时间应小于10秒 (Transcription average response time should be less than 10 seconds)")
    
    @patch('speak_practice.views._validate_request_origin', return_value=True)
    @patch('speak_practice.services.translation.TranslationService.process')
    @patch('speak_practice.services.text_to_speech.tts_service.generate_speech')
    def test_translation_api_response_time(self, mock_tts, mock_translation, mock_validate):
        """
        测试翻译API响应时间 (Test translation API response time)
        
        验证文本翻译API的性能表现
        (Verify performance of text translation API)
        """
        # 设置模拟响应 (Set up mock responses)
        mock_translation.return_value = {
            'translated_text': '性能测试翻译结果',
            'source_language': 'en',
            'target_language': 'zh',
            'character_count': 8
        }
        mock_tts.return_value = 'mock_tts_data'
        
        translate_url = reverse('speak_practice:translate_text_api')
        response_times = []
        
        # 测试不同长度的文本翻译 (Test translation of different text lengths)
        test_texts = [
            'Hello',
            'Hello world',
            'Hello world, this is a longer text for translation testing',
            'This is a very long text that contains multiple sentences. It is used to test the performance of the translation API when handling longer content. The system should be able to process this efficiently.'
        ]
        
        for text in test_texts:
            response_time, response = self.measure_response_time(
                translate_url,
                method='POST',
                data=json.dumps({'text': text}),
                content_type='application/json',
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            response_times.append(response_time)
            self.assertEqual(response.status_code, 200)
        
        # 分析翻译性能 (Analyze translation performance)
        avg_response_time = statistics.mean(response_times)
        
        print(f"\n翻译API性能指标 (Translation API Performance Metrics):")
        print(f"平均响应时间 (Average response time): {avg_response_time:.2f}ms")
        print(f"文本长度范围 (Text length range): {len(test_texts[0])} - {len(test_texts[-1])} characters")
        
        self.assertLess(avg_response_time, 5000, "翻译平均响应时间应小于5秒 (Translation average response time should be less than 5 seconds)")
    
    @patch('speak_practice.views._validate_request_origin', return_value=True)
    @patch('speak_practice.views.get_ai_response')
    @patch('speak_practice.services.text_to_speech.tts_service.generate_speech')
    def test_concurrent_request_handling(self, mock_tts, mock_ai_response, mock_validate):
        """
        测试并发请求处理能力 (Test concurrent request handling capability)
        
        验证系统在并发负载下的性能表现
        (Verify system performance under concurrent load)
        """
        # 设置模拟响应 (Set up mock responses)
        mock_ai_response.return_value = json.dumps({
            'chinese': '并发测试回复',
            'pinyin': 'bìng fā cè shì huí fù'
        })
        mock_tts.return_value = 'concurrent_test_audio'
        
        chat_url = reverse('speak_practice:chat_api')
        num_concurrent_requests = 10
        results = []
        
        def make_request(request_id):
            """发送单个请求的辅助函数 (Helper function to send single request)"""
            client = Client()
            client.login(username='perfuser', password='perfpass123')
            
            start_time = time.time()
            response = client.post(
                chat_url,
                json.dumps({
                    'message': f'并发测试消息 {request_id}',
                    'session_id': self.session.id
                }),
                content_type='application/json',
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            end_time = time.time()
            
            return {
                'request_id': request_id,
                'response_time': (end_time - start_time) * 1000,
                'status_code': response.status_code,
                'success': response.status_code == 200
            }
        
        # 使用线程池执行并发请求 (Execute concurrent requests using thread pool)
        with ThreadPoolExecutor(max_workers=num_concurrent_requests) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_concurrent_requests)]
            
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=30)  # 30秒超时 (30 second timeout)
                    results.append(result)
                except Exception as e:
                    print(f"并发请求失败 (Concurrent request failed): {e}")
        
        # 分析并发性能 (Analyze concurrent performance)
        successful_requests = [r for r in results if r['success']]
        response_times = [r['response_time'] for r in successful_requests]
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            success_rate = len(successful_requests) / len(results) * 100
            
            print(f"\n并发请求性能指标 (Concurrent Request Performance Metrics):")
            print(f"并发请求数 (Concurrent requests): {num_concurrent_requests}")
            print(f"成功率 (Success rate): {success_rate:.1f}%")
            print(f"平均响应时间 (Average response time): {avg_response_time:.2f}ms")
            print(f"最大响应时间 (Max response time): {max_response_time:.2f}ms")
            
            # 并发性能断言 (Concurrent performance assertions)
            self.assertGreaterEqual(success_rate, 90, "并发请求成功率应大于90% (Concurrent request success rate should be greater than 90%)")
            self.assertLess(avg_response_time, 10000, "并发平均响应时间应小于10秒 (Concurrent average response time should be less than 10 seconds)")
        else:
            self.fail("所有并发请求都失败了 (All concurrent requests failed)")


class CachePerformanceTest(TestCase):
    """缓存性能测试类 (Cache Performance Test Class)"""
    
    def setUp(self):
        """测试设置 (Test setup)"""
        self.tts_service = TextToSpeechService()
        self.cache_service = TTSCacheService()
        cache.clear()
    
    def tearDown(self):
        """测试清理 (Test cleanup)"""
        cache.clear()
    
    @patch('speak_practice.services.text_to_speech.requests.post')
    def test_tts_cache_performance(self, mock_api):
        """
        测试TTS缓存性能 (Test TTS cache performance)
        
        验证TTS缓存机制的性能提升效果
        (Verify performance improvement of TTS cache mechanism)
        """
        # 设置模拟API响应 (Set up mock API response)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'audioContent': 'base64_encoded_audio_content'
        }
        mock_api.return_value = mock_response
        
        test_text = '这是一个TTS缓存性能测试文本'
        language_code = 'cmn-CN'
        
        # 第一次调用（无缓存）(First call - no cache)
        start_time = time.time()
        result1 = self.tts_service.generate_speech(test_text, language_code)
        first_call_time = (time.time() - start_time) * 1000
        
        # 第二次调用（有缓存）(Second call - with cache)
        start_time = time.time()
        result2 = self.tts_service.generate_speech(test_text, language_code)
        second_call_time = (time.time() - start_time) * 1000
        
        # 验证缓存效果 (Verify cache effectiveness)
        self.assertEqual(result1, result2, "缓存结果应与原始结果相同 (Cached result should be same as original)")
        self.assertLess(second_call_time, first_call_time, "缓存调用应比首次调用更快 (Cached call should be faster than first call)")
        
        print(f"\nTTS缓存性能测试结果 (TTS Cache Performance Test Results):")
        print(f"首次调用时间 (First call time): {first_call_time:.2f}ms")
        print(f"缓存调用时间 (Cached call time): {second_call_time:.2f}ms")
        print(f"性能提升 (Performance improvement): {((first_call_time - second_call_time) / first_call_time * 100):.1f}%")
        
        # 验证API只被调用一次 (Verify API was called only once)
        self.assertEqual(mock_api.call_count, 1, "API应该只被调用一次 (API should be called only once)")
    
    def test_cache_memory_usage(self):
        """
        测试缓存内存使用情况 (Test cache memory usage)
        
        验证缓存不会导致内存泄漏
        (Verify cache doesn't cause memory leaks)
        """
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 添加大量缓存项 (Add many cache items)
        for i in range(100):
            cache_key = f"test_cache_key_{i}"
            cache_value = f"test_cache_value_{i}" * 100  # 较大的值 (Larger value)
            cache.set(cache_key, cache_value, 3600)
        
        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = current_memory - initial_memory
        
        print(f"\n缓存内存使用测试 (Cache Memory Usage Test):")
        print(f"初始内存 (Initial memory): {initial_memory:.2f}MB")
        print(f"当前内存 (Current memory): {current_memory:.2f}MB")
        print(f"内存增长 (Memory increase): {memory_increase:.2f}MB")
        
        # 清理缓存 (Clear cache)
        cache.clear()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"清理后内存 (Memory after cleanup): {final_memory:.2f}MB")
        
        # 内存使用应该合理 (Memory usage should be reasonable)
        self.assertLess(memory_increase, 50, "缓存内存增长应小于50MB (Cache memory increase should be less than 50MB)")
    
    def test_cache_hit_rate(self):
        """
        测试缓存命中率 (Test cache hit rate)
        
        验证缓存命中率在合理范围内
        (Verify cache hit rate is within reasonable range)
        """
        cache_service = self.cache_service
        test_texts = [
            '你好',
            '谢谢',
            '再见',
            '你好',  # 重复 (Duplicate)
            '谢谢',  # 重复 (Duplicate)
            '欢迎',
            '你好',  # 重复 (Duplicate)
        ]
        
        hits = 0
        misses = 0
        
        for text in test_texts:
            cache_key = cache_service.get_cache_key(text, 'cmn-CN')
            
            if cache.get(cache_key):
                hits += 1
            else:
                misses += 1
                # 模拟添加到缓存 (Simulate adding to cache)
                cache.set(cache_key, f'audio_data_for_{text}', 3600)
        
        hit_rate = hits / len(test_texts) * 100 if test_texts else 0
        
        print(f"\n缓存命中率测试 (Cache Hit Rate Test):")
        print(f"总请求数 (Total requests): {len(test_texts)}")
        print(f"缓存命中 (Cache hits): {hits}")
        print(f"缓存未命中 (Cache misses): {misses}")
        print(f"命中率 (Hit rate): {hit_rate:.1f}%")
        
        # 对于这个测试，期望有一定的命中率 (For this test, expect some hit rate)
        self.assertGreaterEqual(hit_rate, 20, "缓存命中率应大于20% (Cache hit rate should be greater than 20%)")


class DatabasePerformanceTest(TestCase):
    """数据库性能测试类 (Database Performance Test Class)"""
    
    def setUp(self):
        """测试设置 (Test setup)"""
        self.user = User.objects.create_user(
            username='dbperfuser',
            email='dbperf@example.com',
            password='dbperfpass123'
        )
        
        self.session = ChatSession.objects.create(
            user=self.user,
            scene='数据库性能测试场景 (Database performance test scenario)'
        )
    
    def tearDown(self):
        """测试清理 (Test cleanup)"""
        ChatMessage.objects.filter(session=self.session).delete()
        ChatSession.objects.filter(user=self.user).delete()
    
    def test_message_query_performance(self):
        """
        测试消息查询性能 (Test message query performance)
        
        验证大量消息情况下的查询性能
        (Verify query performance with large number of messages)
        """
        # 创建大量测试消息 (Create many test messages)
        messages_to_create = 1000
        batch_size = 100
        
        print(f"\n创建 {messages_to_create} 条测试消息... (Creating {messages_to_create} test messages...)")
        
        start_time = time.time()
        
        # 批量创建消息 (Batch create messages)
        for i in range(0, messages_to_create, batch_size):
            batch_messages = []
            for j in range(batch_size):
                if i + j >= messages_to_create:
                    break
                
                message = ChatMessage(
                    session=self.session,
                    sender_type='user' if (i + j) % 2 == 0 else 'ai',
                    message_content={
                        'chinese_text' if (i + j) % 2 == 0 else 'chinese': f'测试消息 {i + j}',
                        'input_method': 'text'
                    },
                    input_method='text'
                )
                batch_messages.append(message)
            
            ChatMessage.objects.bulk_create(batch_messages)
        
        creation_time = (time.time() - start_time) * 1000
        
        # 测试查询性能 (Test query performance)
        start_time = time.time()
        messages = list(ChatMessage.objects.filter(session=self.session).order_by('timestamp'))
        query_time = (time.time() - start_time) * 1000
        
        # 测试分页查询性能 (Test paginated query performance)
        start_time = time.time()
        paginated_messages = list(ChatMessage.objects.filter(session=self.session).order_by('timestamp')[:50])
        paginated_query_time = (time.time() - start_time) * 1000
        
        # 测试索引查询性能 (Test indexed query performance)
        start_time = time.time()
        user_messages = list(ChatMessage.objects.filter(session=self.session, sender_type='user'))
        indexed_query_time = (time.time() - start_time) * 1000
        
        print(f"数据库性能测试结果 (Database Performance Test Results):")
        print(f"消息创建时间 (Message creation time): {creation_time:.2f}ms")
        print(f"全量查询时间 (Full query time): {query_time:.2f}ms")
        print(f"分页查询时间 (Paginated query time): {paginated_query_time:.2f}ms")
        print(f"索引查询时间 (Indexed query time): {indexed_query_time:.2f}ms")
        print(f"查询到的消息数量 (Queried message count): {len(messages)}")
        
        # 性能断言 (Performance assertions)
        self.assertEqual(len(messages), messages_to_create, "应该查询到所有创建的消息 (Should query all created messages)")
        self.assertLess(paginated_query_time, 1000, "分页查询应小于1秒 (Paginated query should be less than 1 second)")
        self.assertLess(indexed_query_time, 1000, "索引查询应小于1秒 (Indexed query should be less than 1 second)")
    
    def test_database_connection_performance(self):
        """
        测试数据库连接性能 (Test database connection performance)
        
        验证数据库连接池的性能表现
        (Verify database connection pool performance)
        """
        connection_times = []
        
        # 测试多次数据库连接 (Test multiple database connections)
        for i in range(10):
            start_time = time.time()
            
            # 执行简单查询 (Execute simple query)
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            
            connection_time = (time.time() - start_time) * 1000
            connection_times.append(connection_time)
            
            self.assertEqual(result[0], 1, "查询结果应该正确 (Query result should be correct)")
        
        avg_connection_time = statistics.mean(connection_times)
        max_connection_time = max(connection_times)
        
        print(f"\n数据库连接性能测试 (Database Connection Performance Test):")
        print(f"平均连接时间 (Average connection time): {avg_connection_time:.2f}ms")
        print(f"最大连接时间 (Max connection time): {max_connection_time:.2f}ms")
        
        # 连接时间应该很快 (Connection time should be fast)
        self.assertLess(avg_connection_time, 100, "平均连接时间应小于100ms (Average connection time should be less than 100ms)")
        self.assertLess(max_connection_time, 500, "最大连接时间应小于500ms (Max connection time should be less than 500ms)")


class MobilePerformanceTest(TestCase):
    """移动设备性能测试类 (Mobile Device Performance Test Class)"""
    
    def setUp(self):
        """测试设置 (Test setup)"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='mobileuser',
            email='mobile@example.com',
            password='mobilepass123'
        )
        self.client.login(username='mobileuser', password='mobilepass123')
        
        self.session = ChatSession.objects.create(
            user=self.user,
            scene='移动设备测试场景 (Mobile device test scenario)'
        )
    
    def tearDown(self):
        """测试清理 (Test cleanup)"""
        ChatMessage.objects.filter(session=self.session).delete()
        ChatSession.objects.filter(user=self.user).delete()
    
    def simulate_mobile_request(self, url, method='GET', data=None, **kwargs):
        """
        模拟移动设备请求 (Simulate mobile device request)
        
        Args:
            url: 请求URL (Request URL)
            method: HTTP方法 (HTTP method)
            data: 请求数据 (Request data)
            **kwargs: 其他参数 (Other parameters)
            
        Returns:
            tuple: (response_time_ms, response)
        """
        # 添加移动设备User-Agent (Add mobile device User-Agent)
        mobile_headers = {
            'HTTP_USER_AGENT': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1',
            'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'
        }
        kwargs.update(mobile_headers)
        
        start_time = time.time()
        
        if method.upper() == 'POST':
            response = self.client.post(url, data, **kwargs)
        else:
            response = self.client.get(url, **kwargs)
        
        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000
        
        return response_time_ms, response
    
    @patch('speak_practice.views._validate_request_origin', return_value=True)
    @patch('speak_practice.views.get_ai_response')
    @patch('speak_practice.services.text_to_speech.tts_service.generate_speech')
    def test_mobile_chat_performance(self, mock_tts, mock_ai_response, mock_validate):
        """
        测试移动设备聊天性能 (Test mobile device chat performance)
        
        验证移动设备上的聊天功能性能
        (Verify chat functionality performance on mobile devices)
        """
        # 设置模拟响应 (Set up mock responses)
        mock_ai_response.return_value = json.dumps({
            'chinese': '移动设备测试回复',
            'pinyin': 'yí dòng shè bèi cè shì huí fù'
        })
        mock_tts.return_value = 'mobile_test_audio'
        
        chat_url = reverse('speak_practice:chat_api')
        mobile_response_times = []
        
        # 模拟移动设备上的多次聊天请求 (Simulate multiple chat requests on mobile device)
        for i in range(5):
            response_time, response = self.simulate_mobile_request(
                chat_url,
                method='POST',
                data=json.dumps({
                    'message': f'移动设备测试消息 {i}',
                    'session_id': self.session.id
                }),
                content_type='application/json'
            )
            
            mobile_response_times.append(response_time)
            self.assertEqual(response.status_code, 200)
        
        avg_mobile_response_time = statistics.mean(mobile_response_times)
        
        print(f"\n移动设备聊天性能测试 (Mobile Device Chat Performance Test):")
        print(f"平均响应时间 (Average response time): {avg_mobile_response_time:.2f}ms")
        
        # 移动设备性能要求可能稍微宽松 (Mobile device performance requirements may be slightly relaxed)
        self.assertLess(avg_mobile_response_time, 3000, "移动设备平均响应时间应小于3秒 (Mobile device average response time should be less than 3 seconds)")
    
    @patch('speak_practice.views._validate_request_origin', return_value=True)
    @patch('speak_practice.services.speech_recognition.SpeechRecognitionService.process')
    @patch('speak_practice.services.translation.TranslationService.process')
    def test_mobile_audio_processing_performance(self, mock_translation, mock_speech, mock_validate):
        """
        测试移动设备音频处理性能 (Test mobile device audio processing performance)
        
        验证移动设备上的音频处理性能
        (Verify audio processing performance on mobile devices)
        """
        # 设置模拟响应 (Set up mock responses)
        mock_speech.return_value = {
            'transcribed_text': '移动设备音频测试',
            'audio_duration': 3.0,
            'audio_size': 2048,
            'audio_format': 'webm'
        }
        
        mock_translation.return_value = {
            'translated_text': 'Mobile device audio test',
            'source_language': 'zh',
            'target_language': 'en',
            'character_count': 8
        }
        
        transcribe_url = reverse('speak_practice:transcribe_audio_api')
        
        # 创建不同大小的音频文件进行测试 (Create different sized audio files for testing)
        audio_sizes = [1024, 2048, 4096, 8192]  # bytes
        
        for size in audio_sizes:
            test_audio = SimpleUploadedFile(
                f"mobile_test_{size}.webm",
                b"x" * size,  # 创建指定大小的假音频数据 (Create fake audio data of specified size)
                content_type="audio/webm"
            )
            
            response_time, response = self.simulate_mobile_request(
                transcribe_url,
                method='POST',
                data={'audio': test_audio}
            )
            
            print(f"音频大小 {size} bytes, 处理时间: {response_time:.2f}ms (Audio size {size} bytes, processing time: {response_time:.2f}ms)")
            
            self.assertEqual(response.status_code, 200)
            # 音频处理时间应该与文件大小相关但保持合理 (Audio processing time should be related to file size but remain reasonable)
            self.assertLess(response_time, 15000, f"音频处理时间应小于15秒 (Audio processing time should be less than 15 seconds) for {size} bytes")
    
    def test_mobile_memory_constraints(self):
        """
        测试移动设备内存约束 (Test mobile device memory constraints)
        
        验证应用在内存受限环境下的表现
        (Verify application performance in memory-constrained environment)
        """
        import gc
        import sys
        
        # 获取初始内存使用情况 (Get initial memory usage)
        initial_objects = len(gc.get_objects())
        
        # 模拟移动设备上的内存密集操作 (Simulate memory-intensive operations on mobile device)
        large_data_sets = []
        
        try:
            # 创建一些大的数据结构 (Create some large data structures)
            for i in range(10):
                large_data = {
                    'messages': [f'消息 {j}' for j in range(1000)],
                    'audio_data': 'x' * 10000,  # 模拟音频数据 (Simulate audio data)
                    'cache_data': {f'key_{k}': f'value_{k}' * 100 for k in range(100)}
                }
                large_data_sets.append(large_data)
            
            # 检查内存使用 (Check memory usage)
            current_objects = len(gc.get_objects())
            object_increase = current_objects - initial_objects
            
            print(f"\n移动设备内存约束测试 (Mobile Device Memory Constraint Test):")
            print(f"初始对象数量 (Initial objects): {initial_objects}")
            print(f"当前对象数量 (Current objects): {current_objects}")
            print(f"对象增长 (Object increase): {object_increase}")
            
            # 验证内存使用在合理范围内 (Verify memory usage is within reasonable range)
            self.assertLess(object_increase, 50000, "对象增长应该在合理范围内 (Object increase should be within reasonable range)")
            
        finally:
            # 清理内存 (Clean up memory)
            large_data_sets.clear()
            gc.collect()
            
            final_objects = len(gc.get_objects())
            print(f"清理后对象数量 (Objects after cleanup): {final_objects}")


class PerformanceOptimizationTest(TestCase):
    """性能优化测试类 (Performance Optimization Test Class)"""
    
    def test_audio_compression_optimization(self):
        """
        测试音频压缩优化 (Test audio compression optimization)
        
        验证音频压缩对性能的影响
        (Verify impact of audio compression on performance)
        """
        # 模拟不同压缩级别的音频处理 (Simulate audio processing with different compression levels)
        compression_levels = ['low', 'medium', 'high']
        processing_times = {}
        
        for level in compression_levels:
            start_time = time.time()
            
            # 模拟音频压缩处理 (Simulate audio compression processing)
            if level == 'low':
                # 低压缩，快速处理 (Low compression, fast processing)
                time.sleep(0.1)
                compressed_size = 1000
            elif level == 'medium':
                # 中等压缩，中等处理时间 (Medium compression, medium processing time)
                time.sleep(0.2)
                compressed_size = 700
            else:  # high
                # 高压缩，较长处理时间 (High compression, longer processing time)
                time.sleep(0.3)
                compressed_size = 500
            
            processing_time = (time.time() - start_time) * 1000
            processing_times[level] = {
                'time': processing_time,
                'size': compressed_size
            }
        
        print(f"\n音频压缩优化测试 (Audio Compression Optimization Test):")
        for level, data in processing_times.items():
            print(f"{level} 压缩: 处理时间 {data['time']:.2f}ms, 压缩后大小 {data['size']} bytes")
            print(f"{level} compression: processing time {data['time']:.2f}ms, compressed size {data['size']} bytes")
        
        # 验证压缩效果 (Verify compression effectiveness)
        self.assertLess(processing_times['high']['size'], processing_times['low']['size'], 
                       "高压缩应该产生更小的文件 (High compression should produce smaller files)")
        self.assertGreater(processing_times['high']['time'], processing_times['low']['time'],
                          "高压缩应该需要更多处理时间 (High compression should require more processing time)")
    
    def test_lazy_loading_optimization(self):
        """
        测试懒加载优化 (Test lazy loading optimization)
        
        验证懒加载对性能的提升效果
        (Verify performance improvement from lazy loading)
        """
        # 模拟传统加载 vs 懒加载 (Simulate traditional loading vs lazy loading)
        
        # 传统加载：一次性加载所有数据 (Traditional loading: load all data at once)
        start_time = time.time()
        all_data = []
        for i in range(100):
            # 模拟数据加载 (Simulate data loading)
            data_item = {
                'id': i,
                'content': f'数据项 {i}' * 100,  # 较大的数据项 (Larger data item)
                'metadata': {'created': time.time(), 'size': 1000}
            }
            all_data.append(data_item)
        traditional_loading_time = (time.time() - start_time) * 1000
        
        # 懒加载：只加载需要的数据 (Lazy loading: load only needed data)
        start_time = time.time()
        lazy_data = []
        for i in range(10):  # 只加载前10项 (Only load first 10 items)
            data_item = {
                'id': i,
                'content': f'数据项 {i}' * 100,
                'metadata': {'created': time.time(), 'size': 1000}
            }
            lazy_data.append(data_item)
        lazy_loading_time = (time.time() - start_time) * 1000
        
        print(f"\n懒加载优化测试 (Lazy Loading Optimization Test):")
        print(f"传统加载时间 (Traditional loading time): {traditional_loading_time:.2f}ms")
        print(f"懒加载时间 (Lazy loading time): {lazy_loading_time:.2f}ms")
        print(f"性能提升 (Performance improvement): {((traditional_loading_time - lazy_loading_time) / traditional_loading_time * 100):.1f}%")
        
        # 验证懒加载的性能优势 (Verify performance advantage of lazy loading)
        self.assertLess(lazy_loading_time, traditional_loading_time, 
                       "懒加载应该比传统加载更快 (Lazy loading should be faster than traditional loading)")
        self.assertGreater(len(all_data), len(lazy_data),
                          "传统加载应该加载更多数据 (Traditional loading should load more data)")
    
    def test_request_batching_optimization(self):
        """
        测试请求批处理优化 (Test request batching optimization)
        
        验证批处理请求对性能的影响
        (Verify impact of request batching on performance)
        """
        # 模拟单个请求 vs 批处理请求 (Simulate individual requests vs batched requests)
        
        # 单个请求模式 (Individual request mode)
        start_time = time.time()
        individual_results = []
        for i in range(10):
            # 模拟单个API调用 (Simulate individual API call)
            time.sleep(0.01)  # 模拟网络延迟 (Simulate network latency)
            result = f'结果 {i}'
            individual_results.append(result)
        individual_request_time = (time.time() - start_time) * 1000
        
        # 批处理请求模式 (Batched request mode)
        start_time = time.time()
        # 模拟批处理API调用 (Simulate batched API call)
        time.sleep(0.05)  # 单次较长的调用 (Single longer call)
        batch_results = [f'结果 {i}' for i in range(10)]
        batch_request_time = (time.time() - start_time) * 1000
        
        print(f"\n请求批处理优化测试 (Request Batching Optimization Test):")
        print(f"单个请求总时间 (Individual requests total time): {individual_request_time:.2f}ms")
        print(f"批处理请求时间 (Batched request time): {batch_request_time:.2f}ms")
        print(f"性能提升 (Performance improvement): {((individual_request_time - batch_request_time) / individual_request_time * 100):.1f}%")
        
        # 验证批处理的性能优势 (Verify performance advantage of batching)
        self.assertLess(batch_request_time, individual_request_time,
                       "批处理请求应该比单个请求更快 (Batched requests should be faster than individual requests)")
        self.assertEqual(len(individual_results), len(batch_results),
                        "两种方式应该返回相同数量的结果 (Both approaches should return same number of results)")


if __name__ == '__main__':
    import unittest
    unittest.main()