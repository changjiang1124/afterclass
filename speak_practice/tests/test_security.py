"""
安全功能测试 (Security Features Tests)
测试速率限制、音频文件验证、输入清理等安全功能
"""

import os
import tempfile
import json
import time
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.core.cache import cache
from django.utils import timezone

from speak_practice.security import (
    RateLimiter, 
    AudioSecurityValidator, 
    InputSanitizer
)
from speak_practice.security_monitor import SecurityEventMonitor, log_security_event
from speak_practice.models import ChatSession, ChatMessage


class RateLimiterTest(TestCase):
    """速率限制器测试 (Rate Limiter Tests)"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.client = Client()
        cache.clear()  # 清理缓存
    
    def test_rate_limit_not_exceeded(self):
        """测试未超出速率限制 (Test rate limit not exceeded)"""
        request = MagicMock()
        request.user = self.user
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        
        is_limited, rate_info = RateLimiter.is_rate_limited(request, 'chat_api')
        
        self.assertFalse(is_limited)
        self.assertEqual(rate_info['limit'], 30)
        self.assertEqual(rate_info['remaining'], 29)
    
    def test_rate_limit_exceeded(self):
        """测试超出速率限制 (Test rate limit exceeded)"""
        request = MagicMock()
        request.user = self.user
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        
        # 模拟超出限制的请求 (Simulate requests exceeding limit)
        for _ in range(31):  # chat_api limit is 30
            RateLimiter.is_rate_limited(request, 'chat_api')
        
        is_limited, rate_info = RateLimiter.is_rate_limited(request, 'chat_api')
        
        self.assertTrue(is_limited)
        self.assertEqual(rate_info['remaining'], 0)
    
    def test_different_endpoints_separate_limits(self):
        """测试不同端点的独立限制 (Test separate limits for different endpoints)"""
        request = MagicMock()
        request.user = self.user
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        
        # 在chat_api上达到限制 (Reach limit on chat_api)
        for _ in range(30):
            RateLimiter.is_rate_limited(request, 'chat_api')
        
        # translate_text应该仍然可用 (translate_text should still be available)
        is_limited, _ = RateLimiter.is_rate_limited(request, 'translate_text')
        self.assertFalse(is_limited)
    
    def test_anonymous_user_rate_limiting(self):
        """测试匿名用户速率限制 (Test anonymous user rate limiting)"""
        request = MagicMock()
        request.user = MagicMock()
        request.user.is_authenticated = False
        request.META = {'REMOTE_ADDR': '192.168.1.100'}
        
        is_limited, rate_info = RateLimiter.is_rate_limited(request, 'chat_api')
        
        self.assertFalse(is_limited)
        self.assertGreater(rate_info['remaining'], 0)


class AudioSecurityValidatorTest(TestCase):
    """音频安全验证器测试 (Audio Security Validator Tests)"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_audio_file(self, content=b'fake audio content', filename='test.wav'):
        """创建测试音频文件 (Create test audio file)"""
        return SimpleUploadedFile(
            filename,
            content,
            content_type='audio/wav'
        )
    
    def test_valid_audio_file(self):
        """测试有效音频文件 (Test valid audio file)"""
        audio_file = self.create_test_audio_file()
        
        result = AudioSecurityValidator.validate_file_basic(audio_file)
        
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(result['file_info']['name'], 'test.wav')
    
    def test_oversized_audio_file(self):
        """测试超大音频文件 (Test oversized audio file)"""
        large_content = b'x' * (11 * 1024 * 1024)  # 11MB, exceeds 10MB limit
        audio_file = self.create_test_audio_file(large_content)
        
        result = AudioSecurityValidator.validate_file_basic(audio_file)
        
        self.assertFalse(result['is_valid'])
        self.assertIn('exceeds maximum allowed size', str(result['errors']))
    
    def test_invalid_file_extension(self):
        """测试无效文件扩展名 (Test invalid file extension)"""
        audio_file = self.create_test_audio_file(filename='test.exe')
        
        result = AudioSecurityValidator.validate_file_basic(audio_file)
        
        self.assertFalse(result['is_valid'])
        self.assertIn('File extension .exe not allowed', str(result['errors']))
    
    def test_malicious_content_detection(self):
        """测试恶意内容检测 (Test malicious content detection)"""
        malicious_content = b'<script>alert("xss")</script>' + b'x' * 1000
        audio_file = self.create_test_audio_file(malicious_content)
        
        result = AudioSecurityValidator.scan_for_malicious_content(audio_file)
        
        self.assertFalse(result['is_valid'])
        self.assertGreater(len(result['threats_detected']), 0)
    
    def test_comprehensive_validation(self):
        """测试综合验证 (Test comprehensive validation)"""
        audio_file = self.create_test_audio_file()
        
        with patch('magic.from_buffer') as mock_magic:
            mock_magic.return_value = 'audio/wav'
            result = AudioSecurityValidator.comprehensive_validate(audio_file)
        
        # 应该通过基础验证但可能在其他验证中有警告 (Should pass basic validation)
        self.assertIn('basic', result['validation_details'])
        self.assertIn('mime_type', result['validation_details'])
        self.assertIn('malicious_content', result['validation_details'])


class InputSanitizerTest(TestCase):
    """输入清理器测试 (Input Sanitizer Tests)"""
    
    def test_basic_text_sanitization(self):
        """测试基础文本清理 (Test basic text sanitization)"""
        dirty_text = "<script>alert('xss')</script>Hello World"
        clean_text = InputSanitizer.sanitize_text(dirty_text)

        # sanitize_text 通过 HTML 转义中和 XSS：可执行的 <script> 标签被转义成惰性的 &lt;script&gt;，
        # 浏览器不会再执行它，残留的 "alert" 只是纯文本，无法触发脚本。
        # (sanitize_text neutralises XSS by HTML-escaping: the executable <script> becomes inert
        #  &lt;script&gt;; any residual "alert" is plain text and cannot run.)
        self.assertNotIn('<script>', clean_text)
        self.assertIn('&lt;script&gt;', clean_text)
        self.assertIn('Hello World', clean_text)
    
    def test_sql_injection_prevention(self):
        """测试SQL注入防护 (Test SQL injection prevention)"""
        malicious_text = "'; DROP TABLE users; --"
        clean_text = InputSanitizer.sanitize_text(malicious_text)
        
        self.assertNotIn('DROP TABLE', clean_text)
        self.assertNotIn('--', clean_text)
    
    def test_command_injection_prevention(self):
        """测试命令注入防护 (Test command injection prevention)"""
        malicious_text = "test && rm -rf /"
        clean_text = InputSanitizer.sanitize_text(malicious_text)
        
        self.assertNotIn('rm -rf', clean_text)
        self.assertNotIn('&&', clean_text)
    
    def test_length_limitation(self):
        """测试长度限制 (Test length limitation)"""
        long_text = "A" * 2000
        clean_text = InputSanitizer.sanitize_text(long_text, max_length=100)
        
        self.assertEqual(len(clean_text), 100)
    
    def test_validate_text_content_safe(self):
        """测试安全文本内容验证 (Test safe text content validation)"""
        safe_text = "Hello, this is a normal message in Chinese: 你好世界"
        result = InputSanitizer.validate_text_content(safe_text)
        
        self.assertTrue(result['is_safe'])
        self.assertEqual(result['risk_level'], 'low')
        self.assertEqual(len(result['threats_detected']), 0)
    
    def test_validate_text_content_malicious(self):
        """测试恶意文本内容验证 (Test malicious text content validation)"""
        malicious_text = "<script>alert('xss')</script> OR 1=1"
        result = InputSanitizer.validate_text_content(malicious_text)
        
        self.assertFalse(result['is_safe'])
        self.assertIn(result['risk_level'], ['medium', 'high'])
        self.assertGreater(len(result['threats_detected']), 0)
    
    def test_sanitize_json_data(self):
        """测试JSON数据清理 (Test JSON data sanitization)"""
        dirty_data = {
            'message': '<script>alert("xss")</script>Hello',
            'name': 'Normal Name',
            'description': 'A' * 2000
        }
        
        field_configs = {
            'message': {'max_length': 100, 'allow_html': False},
            'name': {'max_length': 50, 'allow_html': False},
            'description': {'max_length': 500, 'allow_html': False}
        }
        
        clean_data = InputSanitizer.sanitize_json_data(dirty_data, field_configs)
        
        self.assertNotIn('<script>', clean_data['message'])
        self.assertEqual(clean_data['name'], 'Normal Name')
        self.assertEqual(len(clean_data['description']), 500)


class SecurityMonitorTest(TestCase):
    """安全监控测试 (Security Monitor Tests)"""
    
    def setUp(self):
        self.monitor = SecurityEventMonitor()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
    
    def test_record_security_event(self):
        """测试记录安全事件 (Test recording security event)"""
        self.monitor.record_event(
            'rate_limit_violation',
            self.user.id,
            '127.0.0.1',
            {'endpoint': 'chat_api', 'attempts': 31}
        )
        
        metrics = self.monitor.get_security_metrics(1)
        self.assertEqual(metrics['total_events'], 1)
        self.assertIn('rate_limit_violation', metrics['events_by_type'])
    
    def test_alert_threshold_triggering(self):
        """测试告警阈值触发 (Test alert threshold triggering)"""
        # 记录多个高严重性事件 (Record multiple high severity events)
        for i in range(3):
            self.monitor.record_event(
                'malicious_input_detected',
                self.user.id,
                '127.0.0.1',
                {'threat_type': 'xss', 'attempt': i}
            )
        
        metrics = self.monitor.get_security_metrics(1)
        self.assertEqual(metrics['events_by_type']['malicious_input_detected'], 3)
    
    def test_get_security_metrics(self):
        """测试获取安全指标 (Test getting security metrics)"""
        # 记录不同类型的事件 (Record different types of events)
        events = [
            ('rate_limit_violation', 'medium'),
            ('malicious_input_detected', 'high'),
            ('authentication_failure', 'medium')
        ]
        
        for event_type, severity in events:
            self.monitor.record_event(
                event_type,
                self.user.id,
                '127.0.0.1',
                {'severity': severity}
            )
        
        metrics = self.monitor.get_security_metrics(1)
        
        self.assertEqual(metrics['total_events'], 3)
        self.assertEqual(len(metrics['events_by_type']), 3)
        self.assertIn('medium', metrics['events_by_severity'])
        self.assertIn('high', metrics['events_by_severity'])


class SecurityIntegrationTest(TestCase):
    """安全集成测试 (Security Integration Tests)"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        # 测试运行器强制 DEBUG=False，此时 _validate_request_origin 要求合法 Referer，否则先返回 403。
        # 真实浏览器会带 Referer，因此用 Client 默认头模拟，才能测到来源校验之后的真正逻辑。
        # (Test runner forces DEBUG=False; _validate_request_origin then needs a valid Referer or it
        #  returns 403 first. Real browsers send one, so set it as a Client default to reach the real logic.)
        self.client = Client(HTTP_REFERER='http://testserver/')
        self.client.login(username='testuser', password='password')

        # 创建测试会话 (Create test session)
        self.session = ChatSession.objects.create(user=self.user, scene='测试场景')
        cache.clear()
    
    @patch('speak_practice.views.get_ai_response')
    @patch('speak_practice.services.text_to_speech.tts_service.generate_speech')
    def test_chat_api_with_malicious_input(self, mock_tts, mock_ai):
        """测试聊天API恶意输入处理 (Test chat API malicious input handling)

        chat_api 采用"先清洗后放行"策略：恶意输入经 sanitize_text 做 HTML 转义后已被中和，
        请求正常成功(200)，但持久化的用户消息绝不能含有可执行的 <script> 标签。
        (chat_api sanitises-then-allows: malicious input is neutralised via HTML escaping, so the
         request succeeds while the persisted user message must never contain an executable <script>.)
        """
        mock_ai.return_value = '{"chinese": "你好", "pinyin": "nǐ hǎo"}'
        mock_tts.return_value = 'fake_audio_data'

        malicious_data = {
            'message': '<script>alert("xss")</script>',
            'session_id': self.session.id
        }

        response = self.client.post(
            reverse('speak_practice:chat_api'),
            data=json.dumps(malicious_data),
            content_type='application/json'
        )

        # 输入被清洗中和后请求成功 (request succeeds once the input is neutralised)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])

        # 持久化的用户消息必须是转义后的安全文本，不含可执行脚本
        # (the stored user message must be escaped, safe text — no executable script)
        user_msg = ChatMessage.objects.filter(
            session=self.session, sender_type='user'
        ).latest('timestamp')
        stored_text = user_msg.message_content.get('chinese_text', '')
        self.assertNotIn('<script>', stored_text)
        self.assertIn('&lt;script&gt;', stored_text)
    
    def test_transcribe_audio_api_with_invalid_file(self):
        """测试音频转录API无效文件处理 (Test transcribe audio API invalid file handling)"""
        # 创建恶意文件 (Create malicious file)
        malicious_file = SimpleUploadedFile(
            'malicious.exe',
            b'MZ\x90\x00' + b'fake executable content',  # PE header
            content_type='audio/wav'
        )
        
        response = self.client.post(
            reverse('speak_practice:transcribe_audio_api'),
            {'audio': malicious_file}
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error_code'], 'audio_security_violation')
    
    @patch('speak_practice.views.get_ai_response')
    @patch('speak_practice.services.text_to_speech.tts_service.generate_speech')
    def test_rate_limiting_integration(self, mock_tts, mock_ai):
        """测试速率限制集成 (Test rate limiting integration)"""
        # mock 掉外部 AI/TTS：限流前的请求会真正进入视图，不 mock 就会发起真实网络调用拖慢测试
        # (mock external AI/TTS — pre-limit requests reach the view; without mocks they hit real
        #  network services and slow the test dramatically)
        mock_ai.return_value = '{"chinese": "你好", "pinyin": "nǐ hǎo"}'
        mock_tts.return_value = 'fake_audio_data'

        # 快速发送多个请求 (Send multiple requests quickly)
        for i in range(32):  # Exceed chat_api limit of 30
            response = self.client.post(
                reverse('speak_practice:chat_api'),
                data=json.dumps({
                    'message': f'Test message {i}',
                    'session_id': self.session.id
                }),
                content_type='application/json'
            )
            
            if i >= 30:  # Should be rate limited after 30 requests
                self.assertEqual(response.status_code, 429)
                response_data = json.loads(response.content)
                self.assertEqual(response_data['error_code'], 'rate_limit_exceeded')
                break
    
    @patch('speak_practice.services.text_to_speech.tts_service.generate_speech')
    @patch('speak_practice.services.translation.TranslationService.process')
    def test_translate_text_api_security(self, mock_translate, mock_tts):
        """测试翻译API安全性 (Test translate text API security)

        translate_text_api 同样"先清洗后放行"：SQL 注入片段(DROP / --)在调用翻译服务前已被剥离，
        请求成功(200)，但传给下游服务的文本必须不含注入关键字。
        (translate_text_api sanitises-then-allows: SQL-injection fragments (DROP / --) are stripped
         before the translation service is called; the text reaching the service must be clean.)
        """
        mock_translate.return_value = {'translated_text': '你好世界'}
        # mock 掉 TTS，避免测试发起真实的 Google TTS 网络请求(否则会因 referer 被拒并重试,拖慢测试)
        # (mock TTS so the test makes no real Google TTS network call — otherwise it retries and stalls)
        mock_tts.return_value = 'fake_audio_data'

        # 测试SQL注入尝试 (Test SQL injection attempt)
        malicious_data = {
            'text': "Hello'; DROP TABLE users; --"
        }

        response = self.client.post(
            reverse('speak_practice:translate_text_api'),
            data=json.dumps(malicious_data),
            content_type='application/json'
        )

        # 注入内容被中和后请求成功 (request succeeds once the injection is neutralised)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mock_translate.called)

        # 传给翻译服务的文本已剔除 SQL 注入片段 (text passed downstream has injection fragments stripped)
        passed_text = mock_translate.call_args[0][0]['text']
        self.assertNotIn('DROP', passed_text.upper())
        self.assertNotIn('--', passed_text)


class SecurityConfigTest(TestCase):
    """安全配置测试 (Security Configuration Tests)"""
    
    def test_production_security_validation(self):
        """测试生产环境安全验证 (Test production security validation)"""
        from speak_practice.security_config import validate_production_security
        
        result = validate_production_security()
        
        self.assertIn('passed', result)
        self.assertIn('total', result)
        self.assertIn('percentage', result)
        self.assertIn('is_secure', result)
        self.assertIn('failed_checks', result)
        self.assertIsInstance(result['failed_checks'], list)
    
    def test_security_headers_generation(self):
        """测试安全头部生成 (Test security headers generation)"""
        from speak_practice.security_config import get_security_headers
        
        headers = get_security_headers()
        
        self.assertIn('X-Content-Type-Options', headers)
        self.assertIn('X-Frame-Options', headers)
        self.assertIn('Content-Security-Policy', headers)
        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(headers['X-Frame-Options'], 'DENY')


if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'speak_practice',
            ],
            SECRET_KEY='test-secret-key',
        )
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['speak_practice.tests.test_security'])