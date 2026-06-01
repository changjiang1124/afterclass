"""
简化性能测试 (Simplified Performance Tests)

这个测试文件包含简化的性能测试，专注于核心功能的性能验证
(This test file contains simplified performance tests focusing on core functionality performance verification)
"""

import time
import statistics
import threading
from unittest import skipIf
from unittest.mock import patch, Mock
from django.test import TestCase
from django.db import connection
from django.contrib.auth.models import User
from django.core.cache import cache

from speak_practice.models import ChatSession, ChatMessage
from speak_practice.services.text_to_speech import TextToSpeechService
from speak_practice.services.speech_recognition import SpeechRecognitionService
from speak_practice.services.translation import TranslationService
from speak_practice.services.cache import TTSCacheService


class SimplifiedPerformanceTest(TestCase):
    """简化性能测试类 (Simplified Performance Test Class)"""
    
    def setUp(self):
        """测试设置 (Test setup)"""
        self.user = User.objects.create_user(
            username='perfuser',
            email='perf@example.com',
            password='perfpass123'
        )
        
        self.session = ChatSession.objects.create(
            user=self.user,
            scene='性能测试场景 (Performance test scenario)'
        )
        
        cache.clear()
    
    def tearDown(self):
        """测试清理 (Test cleanup)"""
        ChatMessage.objects.filter(session=self.session).delete()
        ChatSession.objects.filter(user=self.user).delete()
        cache.clear()
    
    def test_database_query_performance(self):
        """
        测试数据库查询性能 (Test database query performance)
        """
        print("\n=== 数据库查询性能测试 (Database Query Performance Test) ===")
        
        # 创建测试数据 (Create test data)
        num_messages = 100
        messages_to_create = []
        
        for i in range(num_messages):
            message = ChatMessage(
                session=self.session,
                sender_type='user' if i % 2 == 0 else 'ai',
                message_content={
                    'chinese_text' if i % 2 == 0 else 'chinese': f'测试消息 {i}',
                    'input_method': 'text'
                },
                input_method='text'
            )
            messages_to_create.append(message)
        
        # 测试批量创建性能 (Test bulk creation performance)
        start_time = time.time()
        ChatMessage.objects.bulk_create(messages_to_create)
        creation_time = (time.time() - start_time) * 1000
        
        # 测试查询性能 (Test query performance)
        start_time = time.time()
        messages = list(ChatMessage.objects.filter(session=self.session).order_by('timestamp'))
        query_time = (time.time() - start_time) * 1000
        
        # 测试分页查询性能 (Test paginated query performance)
        start_time = time.time()
        paginated_messages = list(ChatMessage.objects.filter(session=self.session).order_by('timestamp')[:20])
        paginated_query_time = (time.time() - start_time) * 1000
        
        print(f"创建 {num_messages} 条消息耗时: {creation_time:.2f}ms")
        print(f"查询所有消息耗时: {query_time:.2f}ms")
        print(f"分页查询耗时: {paginated_query_time:.2f}ms")
        
        # 性能断言 (Performance assertions)
        self.assertEqual(len(messages), num_messages)
        self.assertEqual(len(paginated_messages), 20)
        self.assertLess(creation_time, 5000, "批量创建应在5秒内完成")
        self.assertLess(query_time, 1000, "查询应在1秒内完成")
        self.assertLess(paginated_query_time, 500, "分页查询应在0.5秒内完成")
    
    @patch('speak_practice.services.text_to_speech.requests.post')
    def test_tts_cache_performance(self, mock_api):
        """
        测试TTS缓存性能 (Test TTS cache performance)
        """
        print("\n=== TTS缓存性能测试 (TTS Cache Performance Test) ===")
        
        # 设置模拟API响应 (Set up mock API response)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'audioContent': 'base64_encoded_audio_content'
        }
        mock_api.return_value = mock_response
        
        tts_service = TextToSpeechService()
        test_text = '这是一个TTS缓存性能测试文本'
        language_code = 'cmn-CN'
        
        # 第一次调用（无缓存）(First call - no cache)
        start_time = time.time()
        result1 = tts_service.generate_speech(test_text, language_code)
        first_call_time = (time.time() - start_time) * 1000
        
        # 第二次调用（有缓存）(Second call - with cache)
        start_time = time.time()
        result2 = tts_service.generate_speech(test_text, language_code)
        second_call_time = (time.time() - start_time) * 1000
        
        print(f"首次TTS调用耗时: {first_call_time:.2f}ms")
        print(f"缓存TTS调用耗时: {second_call_time:.2f}ms")
        print(f"性能提升: {((first_call_time - second_call_time) / first_call_time * 100):.1f}%")
        
        # 验证缓存效果 (Verify cache effectiveness)
        self.assertEqual(result1, result2)
        self.assertLess(second_call_time, first_call_time)
        self.assertEqual(mock_api.call_count, 1, "API应该只被调用一次")
    
    def test_cache_hit_rate_performance(self):
        """
        测试缓存命中率性能 (Test cache hit rate performance)
        """
        print("\n=== 缓存命中率性能测试 (Cache Hit Rate Performance Test) ===")
        
        cache_service = TTSCacheService()
        test_texts = [
            '你好',
            '谢谢',
            '再见',
            '你好',  # 重复
            '谢谢',  # 重复
            '欢迎',
            '你好',  # 重复
            '再见',  # 重复
        ]
        
        hits = 0
        misses = 0
        total_time = 0
        
        for text in test_texts:
            start_time = time.time()
            cache_key = cache_service.get_cache_key(text, 'cmn-CN')
            
            if cache.get(cache_key):
                hits += 1
            else:
                misses += 1
                # 模拟添加到缓存 (Simulate adding to cache)
                cache.set(cache_key, f'audio_data_for_{text}', 3600)
            
            operation_time = (time.time() - start_time) * 1000
            total_time += operation_time
        
        hit_rate = hits / len(test_texts) * 100 if test_texts else 0
        avg_operation_time = total_time / len(test_texts)
        
        print(f"总请求数: {len(test_texts)}")
        print(f"缓存命中: {hits}")
        print(f"缓存未命中: {misses}")
        print(f"命中率: {hit_rate:.1f}%")
        print(f"平均操作时间: {avg_operation_time:.2f}ms")
        
        # 性能断言 (Performance assertions)
        self.assertGreaterEqual(hit_rate, 25, "命中率应大于25%")
        self.assertLess(avg_operation_time, 10, "平均操作时间应小于10ms")
    
    @skipIf(
        connection.vendor == 'sqlite',
        "多线程并发写 SQLite 在内存测试库下天然会锁/失败；本系统是低并发的小规模应用，"
        "该场景不会真实发生。换到 Postgres 等支持并发写的后端后此测试才有意义。"
        "(Threaded concurrent writes are unsupported on SQLite's in-memory test DB; "
        "this is a low-concurrency app — scenario does not occur in practice.)"
    )
    def test_concurrent_database_operations(self):
        """
        测试并发数据库操作性能 (Test concurrent database operations performance)
        """
        print("\n=== 并发数据库操作性能测试 (Concurrent Database Operations Performance Test) ===")
        
        results = []
        errors = []
        num_threads = 5
        operations_per_thread = 10
        
        def database_operation(thread_id):
            """数据库操作函数 (Database operation function)"""
            try:
                start_time = time.time()
                
                # 创建消息 (Create messages)
                for i in range(operations_per_thread):
                    ChatMessage.objects.create(
                        session=self.session,
                        sender_type='user',
                        message_content={
                            'chinese_text': f'线程{thread_id}消息{i}',
                            'input_method': 'text'
                        },
                        input_method='text'
                    )
                
                operation_time = (time.time() - start_time) * 1000
                results.append({
                    'thread_id': thread_id,
                    'time': operation_time,
                    'operations': operations_per_thread
                })
                
            except Exception as e:
                errors.append({
                    'thread_id': thread_id,
                    'error': str(e)
                })
        
        # 创建并启动线程 (Create and start threads)
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=database_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成 (Wait for all threads to complete)
        for thread in threads:
            thread.join()
        
        # 分析结果 (Analyze results)
        if results:
            total_operations = sum(r['operations'] for r in results)
            total_time = sum(r['time'] for r in results)
            avg_time = total_time / len(results)
            
            print(f"并发线程数: {num_threads}")
            print(f"总操作数: {total_operations}")
            print(f"成功线程数: {len(results)}")
            print(f"失败线程数: {len(errors)}")
            print(f"平均执行时间: {avg_time:.2f}ms")
            
            # 验证并发性能 (Verify concurrent performance)
            self.assertEqual(len(errors), 0, "不应该有错误")
            self.assertEqual(len(results), num_threads, "所有线程都应该成功")
            self.assertLess(avg_time, 5000, "平均执行时间应小于5秒")
            
            # 验证数据库中的消息数量 (Verify message count in database)
            message_count = ChatMessage.objects.filter(session=self.session).count()
            expected_count = num_threads * operations_per_thread
            self.assertEqual(message_count, expected_count, f"应该有{expected_count}条消息")
        else:
            self.fail("所有并发操作都失败了")
    
    def test_memory_usage_optimization(self):
        """
        测试内存使用优化 (Test memory usage optimization)
        """
        print("\n=== 内存使用优化测试 (Memory Usage Optimization Test) ===")
        
        import gc
        import sys
        
        # 强制垃圾回收 (Force garbage collection)
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # 创建大量对象 (Create many objects)
        large_data_sets = []
        for i in range(50):
            data_set = {
                'messages': [f'消息 {j}' for j in range(100)],
                'metadata': {'id': i, 'timestamp': time.time()},
                'content': 'x' * 1000  # 1KB数据
            }
            large_data_sets.append(data_set)
        
        # 检查内存使用 (Check memory usage)
        current_objects = len(gc.get_objects())
        object_increase = current_objects - initial_objects
        
        print(f"初始对象数量: {initial_objects}")
        print(f"创建对象后数量: {current_objects}")
        print(f"对象增长: {object_increase}")
        
        # 清理对象 (Clean up objects)
        large_data_sets.clear()
        gc.collect()
        
        final_objects = len(gc.get_objects())
        objects_after_cleanup = final_objects - initial_objects
        
        print(f"清理后对象数量: {final_objects}")
        print(f"清理后净增长: {objects_after_cleanup}")
        
        # 内存使用断言 (Memory usage assertions)
        self.assertLess(object_increase, 10000, "对象增长应该在合理范围内")
        self.assertLess(objects_after_cleanup, 1000, "清理后应该释放大部分内存")
    
    def test_response_time_consistency(self):
        """
        测试响应时间一致性 (Test response time consistency)
        """
        print("\n=== 响应时间一致性测试 (Response Time Consistency Test) ===")
        
        response_times = []
        num_iterations = 20
        
        # 执行多次相同操作 (Execute same operation multiple times)
        for i in range(num_iterations):
            start_time = time.time()
            
            # 模拟典型操作：创建消息并查询 (Simulate typical operation: create message and query)
            message = ChatMessage.objects.create(
                session=self.session,
                sender_type='user',
                message_content={
                    'chinese_text': f'一致性测试消息 {i}',
                    'input_method': 'text'
                },
                input_method='text'
            )
            
            # 查询最近的消息 (Query recent messages)
            recent_messages = list(ChatMessage.objects.filter(
                session=self.session
            ).order_by('-timestamp')[:5])
            
            operation_time = (time.time() - start_time) * 1000
            response_times.append(operation_time)
        
        # 分析响应时间统计 (Analyze response time statistics)
        avg_time = statistics.mean(response_times)
        median_time = statistics.median(response_times)
        std_dev = statistics.stdev(response_times) if len(response_times) > 1 else 0
        min_time = min(response_times)
        max_time = max(response_times)
        
        print(f"测试迭代次数: {num_iterations}")
        print(f"平均响应时间: {avg_time:.2f}ms")
        print(f"中位数响应时间: {median_time:.2f}ms")
        print(f"标准差: {std_dev:.2f}ms")
        print(f"最小响应时间: {min_time:.2f}ms")
        print(f"最大响应时间: {max_time:.2f}ms")
        
        # 一致性断言 (Consistency assertions)
        self.assertLess(avg_time, 1000, "平均响应时间应小于1秒")
        self.assertLess(std_dev, avg_time * 0.5, "标准差应小于平均值的50%")
        self.assertLess(max_time - min_time, avg_time * 2, "响应时间范围应该合理")
    
    def test_scalability_simulation(self):
        """
        测试可扩展性模拟 (Test scalability simulation)
        """
        print("\n=== 可扩展性模拟测试 (Scalability Simulation Test) ===")
        
        # 模拟不同负载级别 (Simulate different load levels)
        load_levels = [10, 50, 100, 200]
        performance_results = {}
        
        for load_level in load_levels:
            print(f"\n测试负载级别: {load_level}")
            
            start_time = time.time()
            
            # 批量创建消息 (Batch create messages)
            messages_to_create = []
            for i in range(load_level):
                message = ChatMessage(
                    session=self.session,
                    sender_type='user' if i % 2 == 0 else 'ai',
                    message_content={
                        'chinese_text' if i % 2 == 0 else 'chinese': f'负载测试消息 {i}',
                        'input_method': 'text'
                    },
                    input_method='text'
                )
                messages_to_create.append(message)
            
            ChatMessage.objects.bulk_create(messages_to_create)
            
            # 执行查询操作 (Execute query operations)
            messages = list(ChatMessage.objects.filter(session=self.session).order_by('-timestamp')[:20])
            
            total_time = (time.time() - start_time) * 1000
            throughput = load_level / (total_time / 1000)  # 每秒处理的消息数
            
            performance_results[load_level] = {
                'time': total_time,
                'throughput': throughput
            }
            
            print(f"处理时间: {total_time:.2f}ms")
            print(f"吞吐量: {throughput:.2f} 消息/秒")
            
            # 清理数据以准备下一轮测试 (Clean up data for next test)
            ChatMessage.objects.filter(session=self.session).delete()
        
        # 分析可扩展性 (Analyze scalability)
        print(f"\n可扩展性分析:")
        for load_level, result in performance_results.items():
            print(f"负载 {load_level}: {result['time']:.2f}ms, {result['throughput']:.2f} 消息/秒")
        
        # 验证可扩展性 (Verify scalability)
        # 检查性能是否随负载合理增长 (Check if performance grows reasonably with load)
        small_load_time = performance_results[10]['time']
        large_load_time = performance_results[200]['time']
        
        # 200倍负载的处理时间不应该超过小负载的100倍 (200x load shouldn't take more than 100x time)
        self.assertLess(large_load_time, small_load_time * 100, "大负载处理时间应该在合理范围内")
        
        # 所有负载级别都应该在合理时间内完成 (All load levels should complete in reasonable time)
        for load_level, result in performance_results.items():
            self.assertLess(result['time'], 30000, f"负载 {load_level} 应该在30秒内完成")


if __name__ == '__main__':
    import unittest
    unittest.main()