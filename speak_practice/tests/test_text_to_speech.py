"""
文本转语音服务单元测试 (Text-to-Speech Service Unit Tests)
"""

import json
import base64
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, override_settings
from django.core.cache import cache
import requests

from ..services.text_to_speech import TextToSpeechService, tts_service, generate_tts_audio, is_tts_available
from ..services.exceptions import (
    TTSError, TTSQuotaExceededError, TTSServiceUnavailableError,
    TextValidationError, APITimeoutError, APIAuthenticationError
)
from ..services.config import VoiceServiceConfig


class TextToSpeechServiceTest(TestCase):
    """文本转语音服务测试类 (Text-to-Speech service test class)"""
    
    def setUp(self):
        """测试设置 (Test setup)"""
        # 清空缓存 (Clear cache)
        cache.clear()
        
        # 模拟有效的API密钥 (Mock valid API key)
        self.mock_api_key = "AIzaSyDsUc6EcwwY1kjINQnlTFG9L7OEriA2R0U"
        
        # 模拟TTS响应数据 (Mock TTS response data)
        self.mock_audio_content = base64.b64encode(b"fake_audio_data").decode('utf-8')
        self.mock_tts_response = {
            'audioContent': self.mock_audio_content
        }
        
        # 测试文本 (Test text)
        self.test_text = "你好，世界！"
        self.test_language = "cmn-CN"
        self.test_voice = "cmn-CN-Standard-A"
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_api_key')
    def test_service_initialization_with_valid_key(self):
        """测试使用有效API密钥初始化服务 (Test service initialization with valid API key)"""
        service = TextToSpeechService()
        
        self.assertEqual(service.api_key, 'test_api_key')
        self.assertIsNotNone(service.api_url)
        self.assertIsNotNone(service.cache_service)
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', None)
    def test_missing_api_key_enforced_at_call_not_construction(self):
        """缺少 API 密钥时：构造不再抛异常（模块级单例需 import-safe），
        而是在调用 generate_speech 时由 @require_valid_config 守卫报错。
        (No key: construction succeeds; the key is enforced at call time, not construction.)"""
        service = TextToSpeechService()
        self.assertIsNone(service.api_key)

        with self.assertRaises(ValueError):
            service.generate_speech(self.test_text, self.test_language)
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    def test_validate_text_length_valid_text(self):
        """测试有效文本长度验证 (Test valid text length validation)"""
        service = TextToSpeechService()
        
        # 测试正常长度文本 (Test normal length text)
        self.assertTrue(service.validate_text_length("你好"))
        self.assertTrue(service.validate_text_length("这是一个测试文本"))
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    def test_validate_text_length_invalid_text(self):
        """测试无效文本长度验证 (Test invalid text length validation)"""
        service = TextToSpeechService()
        
        # 测试空文本 (Test empty text)
        self.assertFalse(service.validate_text_length(""))
        self.assertFalse(service.validate_text_length("   "))
        self.assertFalse(service.validate_text_length(None))
        
        # 测试非字符串类型 (Test non-string type)
        self.assertFalse(service.validate_text_length(123))
        self.assertFalse(service.validate_text_length(["text"]))
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch.object(VoiceServiceConfig, 'TTS_MAX_TEXT_LENGTH', 10)
    def test_validate_text_length_too_long(self):
        """测试过长文本验证 (Test too long text validation)"""
        service = TextToSpeechService()
        
        # 测试超长文本 (Test too long text)
        long_text = "这是一个非常长的文本，超过了最大长度限制"
        self.assertFalse(service.validate_text_length(long_text))
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    def test_validate_input_valid_data(self):
        """测试有效输入数据验证 (Test valid input data validation)"""
        service = TextToSpeechService()
        
        valid_input = {'text': '你好'}
        self.assertTrue(service.validate_input(valid_input))
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    def test_validate_input_invalid_data(self):
        """测试无效输入数据验证 (Test invalid input data validation)"""
        service = TextToSpeechService()
        
        # 测试非字典类型 (Test non-dict type)
        self.assertFalse(service.validate_input("not a dict"))
        
        # 测试空文本 (Test empty text)
        self.assertFalse(service.validate_input({'text': ''}))
        
        # 测试缺少text字段 (Test missing text field)
        self.assertFalse(service.validate_input({'other_field': 'value'}))
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    def test_get_voice_name(self):
        """测试语音名称获取 (Test voice name retrieval)"""
        service = TextToSpeechService()
        
        # 测试中文语音 (Test Chinese voice)
        self.assertEqual(service._get_voice_name('cmn-CN'), 'cmn-CN-Standard-A')
        
        # 测试英文语音 (Test English voice)
        self.assertEqual(service._get_voice_name('en-US'), 'en-US-Standard-C')
        
        # 测试澳洲英语语音 (Test Australian English voice)
        self.assertEqual(service._get_voice_name('en-AU'), 'en-AU-Standard-A')
        
        # 测试未知语言，应返回默认语音 (Test unknown language, should return default voice)
        default_voice = VoiceServiceConfig.TTS_VOICE_NAME
        self.assertEqual(service._get_voice_name('unknown-lang'), default_voice)
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('requests.post')
    def test_call_google_tts_api_success(self, mock_post):
        """测试成功调用Google TTS API (Test successful Google TTS API call)"""
        # 设置模拟响应 (Setup mock response)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_tts_response
        mock_post.return_value = mock_response
        
        service = TextToSpeechService()
        result = service._call_google_tts_api(self.test_text, self.test_language, self.test_voice)
        
        # 验证结果 (Verify result)
        self.assertEqual(result, self.mock_audio_content)
        
        # 验证API调用参数 (Verify API call parameters)
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # 检查请求数据 (Check request data)
        request_data = call_args[1]['json']
        self.assertEqual(request_data['input']['text'], self.test_text)
        self.assertEqual(request_data['voice']['languageCode'], self.test_language)
        self.assertEqual(request_data['voice']['name'], self.test_voice)
        self.assertEqual(request_data['audioConfig']['audioEncoding'], 'MP3')
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('requests.post')
    def test_call_google_tts_api_authentication_error(self, mock_post):
        """测试API认证错误 (Test API authentication error)"""
        # 设置401响应 (Setup 401 response)
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        
        service = TextToSpeechService()
        
        with self.assertRaises(APIAuthenticationError):
            service._call_google_tts_api(self.test_text, self.test_language, self.test_voice)
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('requests.post')
    def test_call_google_tts_api_quota_exceeded(self, mock_post):
        """测试API配额超限 (Test API quota exceeded)"""
        # 设置429响应 (Setup 429 response)
        mock_response = Mock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response
        
        service = TextToSpeechService()
        
        with self.assertRaises(TTSQuotaExceededError):
            service._call_google_tts_api(self.test_text, self.test_language, self.test_voice)
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('requests.post')
    def test_call_google_tts_api_service_unavailable(self, mock_post):
        """测试服务不可用错误 (Test service unavailable error)"""
        # 设置500响应 (Setup 500 response)
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        service = TextToSpeechService()
        
        with self.assertRaises(TTSServiceUnavailableError):
            service._call_google_tts_api(self.test_text, self.test_language, self.test_voice)
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('requests.post')
    def test_call_google_tts_api_timeout(self, mock_post):
        """测试API超时 (Test API timeout)"""
        # 设置超时异常 (Setup timeout exception)
        mock_post.side_effect = requests.exceptions.Timeout()
        
        service = TextToSpeechService()
        
        with self.assertRaises(APITimeoutError):
            service._call_google_tts_api(self.test_text, self.test_language, self.test_voice)
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('requests.post')
    def test_call_google_tts_api_request_exception(self, mock_post):
        """测试请求异常 (Test request exception)"""
        # 设置请求异常 (Setup request exception)
        mock_post.side_effect = requests.exceptions.RequestException("Connection error")
        
        service = TextToSpeechService()
        
        with self.assertRaises(TTSServiceUnavailableError):
            service._call_google_tts_api(self.test_text, self.test_language, self.test_voice)
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('requests.post')
    def test_call_google_tts_api_no_audio_content(self, mock_post):
        """测试API响应中没有音频内容 (Test no audio content in API response)"""
        # 设置没有audioContent的响应 (Setup response without audioContent)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response
        
        service = TextToSpeechService()
        
        with self.assertRaises(TTSError):
            service._call_google_tts_api(self.test_text, self.test_language, self.test_voice)
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('speak_practice.services.text_to_speech.TextToSpeechService._call_google_tts_api')
    def test_generate_speech_success_with_cache_miss(self, mock_api_call):
        """测试缓存未命中时成功生成语音 (Test successful speech generation with cache miss)"""
        # 设置API调用返回 (Setup API call return)
        mock_api_call.return_value = self.mock_audio_content
        
        service = TextToSpeechService()
        result = service.generate_speech(self.test_text, self.test_language)
        
        # 验证结果 (Verify result)
        self.assertEqual(result, self.mock_audio_content)
        
        # 验证API被调用 (Verify API was called)
        mock_api_call.assert_called_once()
        
        # 验证结果被缓存 (Verify result was cached)
        cached_result = service.cache_service.get_cached_audio(
            self.test_text, self.test_language, self.test_voice
        )
        self.assertEqual(cached_result, self.mock_audio_content)
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('speak_practice.services.text_to_speech.TextToSpeechService._call_google_tts_api')
    def test_generate_speech_success_with_cache_hit(self, mock_api_call):
        """测试缓存命中时成功生成语音 (Test successful speech generation with cache hit)"""
        service = TextToSpeechService()
        
        # 预先缓存数据 (Pre-cache data)
        service.cache_service.cache_audio(
            self.test_text, self.test_language, self.mock_audio_content, self.test_voice
        )
        
        result = service.generate_speech(self.test_text, self.test_language)
        
        # 验证结果 (Verify result)
        self.assertEqual(result, self.mock_audio_content)
        
        # 验证API没有被调用 (Verify API was not called)
        mock_api_call.assert_not_called()
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    def test_generate_speech_invalid_text(self):
        """测试无效文本的语音生成 (Test speech generation with invalid text)"""
        service = TextToSpeechService()
        
        # 异常装饰器修复后，TextValidationError 会原样透传（不再被包装成 APIError）
        # (After the decorator fix, TextValidationError propagates as-is instead of being wrapped.)
        with self.assertRaises(TextValidationError):
            service.generate_speech("", self.test_language)

        with self.assertRaises(TextValidationError):
            service.generate_speech("   ", self.test_language)
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('speak_practice.services.text_to_speech.TextToSpeechService._call_google_tts_api')
    def test_process_success(self, mock_api_call):
        """测试成功处理输入数据 (Test successful input data processing)"""
        # 设置API调用返回 (Setup API call return)
        mock_api_call.return_value = self.mock_audio_content
        
        service = TextToSpeechService()
        input_data = {
            'text': self.test_text,
            'language_code': self.test_language
        }
        
        result = service.process(input_data)
        
        # 验证结果结构 (Verify result structure)
        self.assertTrue(result['success'])
        self.assertEqual(result['audio_data'], self.mock_audio_content)
        self.assertEqual(result['text'], self.test_text)
        self.assertEqual(result['language_code'], self.test_language)
        self.assertIn('timestamp', result)
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    def test_process_invalid_input(self):
        """测试处理无效输入数据 (Test processing invalid input data)"""
        service = TextToSpeechService()
        
        with self.assertRaises(TextValidationError):
            service.process({'text': ''})
        
        with self.assertRaises(TextValidationError):
            service.process("not a dict")
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('speak_practice.services.text_to_speech.TextToSpeechService._call_google_tts_api')
    def test_process_api_error(self, mock_api_call):
        """测试处理API错误 (Test processing API error)"""
        # 设置API调用异常 (Setup API call exception)
        mock_api_call.side_effect = TTSError("API error")
        
        service = TextToSpeechService()
        input_data = {'text': self.test_text}
        
        result = service.process(input_data)
        
        # 验证错误结果 (Verify error result)
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('error_code', result)
        self.assertEqual(result['text'], self.test_text)
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    def test_get_supported_languages(self):
        """测试获取支持的语言列表 (Test getting supported languages list)"""
        service = TextToSpeechService()
        languages = service.get_supported_languages()
        
        # 验证返回的语言列表 (Verify returned language list)
        self.assertIsInstance(languages, dict)
        self.assertIn('cmn-CN', languages)
        self.assertIn('en-US', languages)
        self.assertIn('en-AU', languages)
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('speak_practice.services.text_to_speech.TextToSpeechService.generate_speech')
    def test_get_service_status_healthy(self, mock_generate):
        """测试获取健康的服务状态 (Test getting healthy service status)"""
        # 设置成功的语音生成 (Setup successful speech generation)
        mock_generate.return_value = self.mock_audio_content
        
        service = TextToSpeechService()
        status = service.get_service_status()
        
        # 验证状态信息 (Verify status information)
        self.assertEqual(status['api_status'], 'healthy')
        self.assertIn('service_name', status)
        self.assertIn('supported_languages', status)
        self.assertTrue(status['cache_enabled'])
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('speak_practice.services.text_to_speech.TextToSpeechService.generate_speech')
    def test_get_service_status_error(self, mock_generate):
        """测试获取错误的服务状态 (Test getting error service status)"""
        # 设置语音生成异常 (Setup speech generation exception)
        mock_generate.side_effect = TTSError("Service error")
        
        service = TextToSpeechService()
        status = service.get_service_status()
        
        # 验证错误状态 (Verify error status)
        self.assertIn('error:', status['api_status'])


class TTSConvenienceFunctionsTest(TestCase):
    """TTS便捷函数测试类 (TTS convenience functions test class)"""
    
    def setUp(self):
        """测试设置 (Test setup)"""
        cache.clear()
        self.test_text = "测试文本"
        self.mock_audio_content = base64.b64encode(b"fake_audio_data").decode('utf-8')
    
    @patch('speak_practice.services.text_to_speech.tts_service.generate_speech')
    def test_generate_tts_audio_success(self, mock_generate):
        """测试成功生成TTS音频的便捷函数 (Test successful TTS audio generation convenience function)"""
        mock_generate.return_value = self.mock_audio_content
        
        result = generate_tts_audio(self.test_text, 'cmn-CN')
        
        self.assertEqual(result, self.mock_audio_content)
        mock_generate.assert_called_once_with(self.test_text, 'cmn-CN')
    
    @patch('speak_practice.services.text_to_speech.tts_service.generate_speech')
    def test_generate_tts_audio_failure(self, mock_generate):
        """测试TTS音频生成失败的便捷函数 (Test TTS audio generation failure convenience function)"""
        mock_generate.side_effect = TTSError("Generation failed")
        
        result = generate_tts_audio(self.test_text, 'cmn-CN')
        
        self.assertIsNone(result)
    
    @patch('speak_practice.services.text_to_speech.tts_service.get_service_status')
    def test_is_tts_available_healthy(self, mock_status):
        """测试TTS服务可用性检查 - 健康状态 (Test TTS service availability check - healthy status)"""
        mock_status.return_value = {'api_status': 'healthy'}
        
        result = is_tts_available()
        
        self.assertTrue(result)
    
    @patch('speak_practice.services.text_to_speech.tts_service.get_service_status')
    def test_is_tts_available_error(self, mock_status):
        """测试TTS服务可用性检查 - 错误状态 (Test TTS service availability check - error status)"""
        mock_status.return_value = {'api_status': 'error: Service down'}
        
        result = is_tts_available()
        
        self.assertFalse(result)
    
    @patch('speak_practice.services.text_to_speech.tts_service.get_service_status')
    def test_is_tts_available_exception(self, mock_status):
        """测试TTS服务可用性检查 - 异常情况 (Test TTS service availability check - exception case)"""
        mock_status.side_effect = Exception("Service error")
        
        result = is_tts_available()
        
        self.assertFalse(result)


class TTSCacheIntegrationTest(TestCase):
    """TTS缓存集成测试类 (TTS cache integration test class)"""
    
    def setUp(self):
        """测试设置 (Test setup)"""
        cache.clear()
        self.test_text = "缓存测试文本"
        self.test_language = "cmn-CN"
        self.test_voice = "cmn-CN-Standard-A"
        self.mock_audio_content = base64.b64encode(b"cached_audio_data").decode('utf-8')
        self.mock_api_key = "test_key"
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('speak_practice.services.text_to_speech.TextToSpeechService._call_google_tts_api')
    def test_cache_integration(self, mock_api_call):
        """测试缓存集成功能 (Test cache integration functionality)"""
        mock_api_call.return_value = self.mock_audio_content
        
        service = TextToSpeechService()
        
        # 第一次调用，应该调用API并缓存结果 (First call should call API and cache result)
        result1 = service.generate_speech(self.test_text, self.test_language)
        self.assertEqual(result1, self.mock_audio_content)
        self.assertEqual(mock_api_call.call_count, 1)
        
        # 第二次调用，应该从缓存获取，不调用API (Second call should get from cache, not call API)
        result2 = service.generate_speech(self.test_text, self.test_language)
        self.assertEqual(result2, self.mock_audio_content)
        self.assertEqual(mock_api_call.call_count, 1)  # API调用次数不应增加 (API call count should not increase)
        
        # 验证两次结果相同 (Verify both results are the same)
        self.assertEqual(result1, result2)
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('speak_practice.services.text_to_speech.TextToSpeechService._call_google_tts_api')
    def test_cache_different_texts(self, mock_api_call):
        """测试不同文本的缓存处理 (Test cache handling for different texts)"""
        mock_api_call.return_value = self.mock_audio_content
        
        service = TextToSpeechService()
        
        # 生成两个不同文本的语音 (Generate speech for two different texts)
        result1 = service.generate_speech("文本一", self.test_language)
        result2 = service.generate_speech("文本二", self.test_language)
        
        # 应该调用API两次 (Should call API twice)
        self.assertEqual(mock_api_call.call_count, 2)
        
        # 再次调用相同文本，应该从缓存获取 (Call same texts again, should get from cache)
        result3 = service.generate_speech("文本一", self.test_language)
        result4 = service.generate_speech("文本二", self.test_language)
        
        # API调用次数不应增加 (API call count should not increase)
        self.assertEqual(mock_api_call.call_count, 2)
        
        # 验证缓存结果正确 (Verify cached results are correct)
        self.assertEqual(result1, result3)
        self.assertEqual(result2, result4)
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('speak_practice.services.text_to_speech.TextToSpeechService._call_google_tts_api')
    def test_cache_different_languages(self, mock_api_call):
        """测试不同语言的缓存处理 (Test cache handling for different languages)"""
        mock_api_call.return_value = self.mock_audio_content
        
        service = TextToSpeechService()
        
        # 同一文本，不同语言 (Same text, different languages)
        result1 = service.generate_speech(self.test_text, "cmn-CN")
        result2 = service.generate_speech(self.test_text, "en-US")
        
        # 应该调用API两次，因为语言不同 (Should call API twice due to different languages)
        self.assertEqual(mock_api_call.call_count, 2)
        
        # 再次调用相同文本和语言，应该从缓存获取 (Call same text and language again, should get from cache)
        result3 = service.generate_speech(self.test_text, "cmn-CN")
        result4 = service.generate_speech(self.test_text, "en-US")
        
        # API调用次数不应增加 (API call count should not increase)
        self.assertEqual(mock_api_call.call_count, 2)
        
        # 验证缓存结果正确 (Verify cached results are correct)
        self.assertEqual(result1, result3)
        self.assertEqual(result2, result4)
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    def test_cache_key_generation(self):
        """测试缓存键生成 (Test cache key generation)"""
        service = TextToSpeechService()
        cache_service = service.cache_service
        
        # 测试基本缓存键生成 (Test basic cache key generation)
        key1 = cache_service.get_cache_key("测试", "cmn-CN", "cmn-CN-Standard-A")
        key2 = cache_service.get_cache_key("测试", "cmn-CN", "cmn-CN-Standard-A")
        self.assertEqual(key1, key2)  # 相同参数应生成相同键 (Same parameters should generate same key)
        
        # 测试不同参数生成不同键 (Test different parameters generate different keys)
        key3 = cache_service.get_cache_key("测试", "en-US", "en-US-Standard-C")
        self.assertNotEqual(key1, key3)
        
        # 测试键格式 (Test key format)
        self.assertTrue(key1.startswith('speak_practice_voice_tts_'))
        self.assertEqual(len(key1), len('speak_practice_voice_tts_') + 32)  # MD5 hash length
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('speak_practice.services.text_to_speech.TextToSpeechService._call_google_tts_api')
    def test_cache_timeout_behavior(self, mock_api_call):
        """测试缓存超时行为 (Test cache timeout behavior)"""
        mock_api_call.return_value = self.mock_audio_content
        
        service = TextToSpeechService()
        
        # 手动设置缓存 (Manually set cache)
        cache_key = service.cache_service.get_cache_key(self.test_text, self.test_language, self.test_voice)
        service.cache_service.set(cache_key, self.mock_audio_content, timeout=1)  # 1秒超时 (1 second timeout)
        
        # 立即获取应该命中缓存 (Immediate retrieval should hit cache)
        result1 = service.generate_speech(self.test_text, self.test_language)
        self.assertEqual(result1, self.mock_audio_content)
        self.assertEqual(mock_api_call.call_count, 0)  # 不应调用API (Should not call API)
        
        # 等待缓存过期后再次调用 (Wait for cache expiration and call again)
        import time
        time.sleep(1.1)  # 等待超过超时时间 (Wait longer than timeout)
        
        result2 = service.generate_speech(self.test_text, self.test_language)
        self.assertEqual(result2, self.mock_audio_content)
        self.assertEqual(mock_api_call.call_count, 1)  # 应该调用API (Should call API)


class TTSCacheServiceTest(TestCase):
    """TTS缓存服务单独测试类 (TTS cache service standalone test class)"""
    
    def setUp(self):
        """测试设置 (Test setup)"""
        cache.clear()
        from ..services.cache import TTSCacheService
        self.cache_service = TTSCacheService()
        self.test_text = "缓存服务测试"
        self.test_language = "cmn-CN"
        self.test_voice = "cmn-CN-Standard-A"
        self.test_audio = base64.b64encode(b"test_audio_data").decode('utf-8')
    
    def test_cache_audio_and_retrieval(self):
        """测试音频缓存和检索 (Test audio caching and retrieval)"""
        # 缓存音频数据 (Cache audio data)
        success = self.cache_service.cache_audio(
            self.test_text, self.test_language, self.test_audio, self.test_voice
        )
        self.assertTrue(success)
        
        # 检索缓存的音频数据 (Retrieve cached audio data)
        cached_audio = self.cache_service.get_cached_audio(
            self.test_text, self.test_language, self.test_voice
        )
        self.assertEqual(cached_audio, self.test_audio)
    
    def test_cache_miss(self):
        """测试缓存未命中 (Test cache miss)"""
        # 尝试获取不存在的缓存 (Try to get non-existent cache)
        cached_audio = self.cache_service.get_cached_audio(
            "不存在的文本", self.test_language, self.test_voice
        )
        self.assertIsNone(cached_audio)
    
    def test_cache_key_uniqueness(self):
        """测试缓存键的唯一性 (Test cache key uniqueness)"""
        # 不同文本应生成不同键 (Different texts should generate different keys)
        key1 = self.cache_service.get_cache_key("文本1", self.test_language, self.test_voice)
        key2 = self.cache_service.get_cache_key("文本2", self.test_language, self.test_voice)
        self.assertNotEqual(key1, key2)
        
        # 不同语言应生成不同键 (Different languages should generate different keys)
        key3 = self.cache_service.get_cache_key(self.test_text, "en-US", self.test_voice)
        key4 = self.cache_service.get_cache_key(self.test_text, "cmn-CN", self.test_voice)
        self.assertNotEqual(key3, key4)
        
        # 不同语音应生成不同键 (Different voices should generate different keys)
        key5 = self.cache_service.get_cache_key(self.test_text, self.test_language, "voice1")
        key6 = self.cache_service.get_cache_key(self.test_text, self.test_language, "voice2")
        self.assertNotEqual(key5, key6)
    
    def test_cache_stats(self):
        """测试缓存统计信息 (Test cache statistics)"""
        stats = self.cache_service.get_cache_stats()
        
        # 验证统计信息结构 (Verify statistics structure)
        self.assertIn('cache_timeout', stats)
        self.assertIn('key_prefix', stats)
        self.assertIn('backend', stats)
        
        # 验证统计信息值 (Verify statistics values)
        self.assertIsInstance(stats['cache_timeout'], int)
        self.assertTrue(stats['key_prefix'].startswith('speak_practice_voice_tts_'))
    
    @patch('django.core.cache.cache.get')
    def test_cache_connection_error_on_get(self, mock_cache_get):
        """测试获取缓存时的连接错误 (Test connection error when getting cache)"""
        from ..services.exceptions import CacheConnectionError
        
        # 模拟缓存连接错误 (Mock cache connection error)
        mock_cache_get.side_effect = Exception("Cache connection failed")
        
        with self.assertRaises(CacheConnectionError):
            self.cache_service.get("test_key")
    
    @patch('django.core.cache.cache.set')
    def test_cache_connection_error_on_set(self, mock_cache_set):
        """测试设置缓存时的连接错误 (Test connection error when setting cache)"""
        from ..services.exceptions import CacheConnectionError
        
        # 模拟缓存连接错误 (Mock cache connection error)
        mock_cache_set.side_effect = Exception("Cache connection failed")
        
        with self.assertRaises(CacheConnectionError):
            self.cache_service.set("test_key", "test_value")


class TTSAudioDataValidationTest(TestCase):
    """TTS音频数据验证测试类 (TTS audio data validation test class)"""
    
    def setUp(self):
        """测试设置 (Test setup)"""
        self.mock_api_key = "test_key"
        # 创建有效的Base64音频数据 (Create valid Base64 audio data)
        self.valid_audio_data = base64.b64encode(b"valid_audio_content").decode('utf-8')
        # 创建无效的Base64数据 (Create invalid Base64 data)
        self.invalid_audio_data = "invalid_base64_data!"
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('requests.post')
    def test_valid_audio_data_format(self, mock_post):
        """测试有效音频数据格式 (Test valid audio data format)"""
        # 设置有效的API响应 (Setup valid API response)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'audioContent': self.valid_audio_data}
        mock_post.return_value = mock_response
        
        service = TextToSpeechService()
        result = service.generate_speech("测试文本", "cmn-CN")
        
        # 验证返回的音频数据格式 (Verify returned audio data format)
        self.assertEqual(result, self.valid_audio_data)
        
        # 验证Base64数据可以解码 (Verify Base64 data can be decoded)
        try:
            decoded_data = base64.b64decode(result)
            self.assertIsInstance(decoded_data, bytes)
        except Exception as e:
            self.fail(f"Failed to decode Base64 audio data: {e}")
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('requests.post')
    def test_empty_audio_content_handling(self, mock_post):
        """测试空音频内容处理 (Test empty audio content handling)"""
        # 设置空音频内容的API响应 (Setup API response with empty audio content)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'audioContent': ''}
        mock_post.return_value = mock_response
        
        service = TextToSpeechService()
        
        # 由于异常装饰器的存在，会抛出APIError而不是TTSError (Due to exception decorator, APIError will be thrown instead of TTSError)
        with self.assertRaises(Exception) as context:
            service.generate_speech("测试文本", "cmn-CN")
        
        self.assertIn("No audio content", str(context.exception))
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('requests.post')
    def test_missing_audio_content_field(self, mock_post):
        """测试缺少音频内容字段 (Test missing audio content field)"""
        # 设置缺少audioContent字段的API响应 (Setup API response missing audioContent field)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'otherField': 'value'}
        mock_post.return_value = mock_response
        
        service = TextToSpeechService()
        
        # 由于异常装饰器的存在，会抛出APIError而不是TTSError (Due to exception decorator, APIError will be thrown instead of TTSError)
        with self.assertRaises(Exception) as context:
            service.generate_speech("测试文本", "cmn-CN")
        
        self.assertIn("No audio content", str(context.exception))
    
    def test_audio_data_size_validation(self):
        """测试音频数据大小验证 (Test audio data size validation)"""
        # 创建大型音频数据 (Create large audio data)
        large_audio_data = b"x" * (1024 * 1024)  # 1MB
        large_base64_data = base64.b64encode(large_audio_data).decode('utf-8')
        
        # 验证Base64编码的音频数据可以正常处理 (Verify Base64 encoded audio data can be processed normally)
        try:
            decoded_data = base64.b64decode(large_base64_data)
            self.assertEqual(len(decoded_data), 1024 * 1024)
        except Exception as e:
            self.fail(f"Failed to handle large audio data: {e}")
    
    def test_audio_data_encoding_validation(self):
        """测试音频数据编码验证 (Test audio data encoding validation)"""
        # 测试各种有效的Base64数据 (Test various valid Base64 data)
        test_cases = [
            b"short_audio",
            b"medium_length_audio_content_for_testing",
            b"very_long_audio_content_" * 100,
            b"\x00\x01\x02\x03\x04\x05",  # 二进制数据 (Binary data)
        ]
        
        for audio_bytes in test_cases:
            with self.subTest(audio_length=len(audio_bytes)):
                base64_data = base64.b64encode(audio_bytes).decode('utf-8')
                
                # 验证编码和解码过程 (Verify encoding and decoding process)
                try:
                    decoded_data = base64.b64decode(base64_data)
                    self.assertEqual(decoded_data, audio_bytes)
                except Exception as e:
                    self.fail(f"Failed to encode/decode audio data: {e}")


class TTSErrorHandlingTest(TestCase):
    """TTS错误处理测试类 (TTS error handling test class)"""
    
    def setUp(self):
        """测试设置 (Test setup)"""
        self.mock_api_key = "test_key"
        self.test_text = "错误处理测试"
        self.test_language = "cmn-CN"
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('requests.post')
    def test_api_error_with_json_response(self, mock_post):
        """测试带JSON响应的API错误 (Test API error with JSON response)"""
        # 设置带错误信息的API响应 (Setup API response with error information)
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'error': {
                'message': 'Invalid request parameters',
                'code': 'INVALID_ARGUMENT'
            }
        }
        mock_post.return_value = mock_response
        
        service = TextToSpeechService()
        
        # 由于异常装饰器的存在，会抛出APIError (Due to exception decorator, APIError will be thrown)
        with self.assertRaises(Exception) as context:
            service.generate_speech(self.test_text, self.test_language)
        
        error_message = str(context.exception)
        self.assertIn("Invalid request parameters", error_message)
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('requests.post')
    def test_api_error_without_json_response(self, mock_post):
        """测试没有JSON响应的API错误 (Test API error without JSON response)"""
        # 设置无法解析JSON的API响应 (Setup API response that cannot parse JSON)
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response
        
        service = TextToSpeechService()
        
        # 由于异常装饰器的存在，会抛出APIError (Due to exception decorator, APIError will be thrown)
        with self.assertRaises(Exception) as context:
            service.generate_speech(self.test_text, self.test_language)
        
        error_message = str(context.exception)
        self.assertIn("400", error_message)
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('speak_practice.services.text_to_speech.TextToSpeechService._call_google_tts_api')
    def test_error_handling_in_process_method(self, mock_api_call):
        """测试process方法中的错误处理 (Test error handling in process method)"""
        # 设置API调用异常 (Setup API call exception)
        test_error = TTSQuotaExceededError("Quota exceeded")
        mock_api_call.side_effect = test_error
        
        service = TextToSpeechService()
        input_data = {'text': self.test_text}
        
        result = service.process(input_data)
        
        # 验证错误结果结构 (Verify error result structure)
        self.assertFalse(result['success'])
        # 由于异常装饰器，错误消息会被包装 (Due to exception decorator, error message will be wrapped)
        self.assertIn('error', result)
        self.assertIn('error_code', result)
        self.assertEqual(result['text'], self.test_text)
        self.assertIn('timestamp', result)
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    @patch('speak_practice.services.text_to_speech.TextToSpeechService._call_google_tts_api')
    def test_generic_exception_handling(self, mock_api_call):
        """测试通用异常处理 (Test generic exception handling)"""
        # 设置通用异常 (Setup generic exception)
        mock_api_call.side_effect = Exception("Unexpected error")
        
        service = TextToSpeechService()
        input_data = {'text': self.test_text}
        
        result = service.process(input_data)
        
        # 验证错误结果 (Verify error result)
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        # 由于异常装饰器，错误代码会是api_error (Due to exception decorator, error code will be api_error)
        self.assertIn('error_code', result)
    
    @patch.object(VoiceServiceConfig, 'GOOGLE_API_KEY', 'test_key')
    def test_text_validation_error_handling(self):
        """测试文本验证错误处理 (Test text validation error handling)"""
        service = TextToSpeechService()
        
        # 测试空文本错误 (Test empty text error)
        # 由于异常装饰器的存在，会抛出APIError而不是TextValidationError (Due to exception decorator, APIError will be thrown instead of TextValidationError)
        with self.assertRaises(Exception) as context:
            service.generate_speech("", self.test_language)
        
        self.assertIn("Invalid text for TTS", str(context.exception))
        
        # 测试process方法中的文本验证错误 (Test text validation error in process method)
        # process方法会直接抛出异常而不是返回错误结果 (process method will throw exception directly instead of returning error result)
        with self.assertRaises(TextValidationError):
            service.process({'text': ''})