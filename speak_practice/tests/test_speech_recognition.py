"""
语音识别服务单元测试 (Speech Recognition Service Unit Tests)
"""

import os
import io
import json
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile, InMemoryUploadedFile
from django.conf import settings

from ..services.speech_recognition import SpeechRecognitionService
from ..services.exceptions import (
    AudioValidationError,
    SpeechRecognitionError,
    TranscriptionTimeoutError,
    AudioFormatError,
    APIAuthenticationError,
    MissingAPIKeyError,
    APIError
)


class SpeechRecognitionServiceTest(TestCase):
    """语音识别服务测试类 (Speech Recognition Service Test Class)"""
    
    def setUp(self):
        """测试设置 (Test setup)"""
        # 模拟API密钥 (Mock API key)
        self.mock_api_key = "sk-test123456789"
        
        # 创建测试音频文件 (Create test audio files)
        self.valid_audio_content = b"fake_audio_content_for_testing"
        self.valid_audio_file = SimpleUploadedFile(
            "test_audio.wav",
            self.valid_audio_content,
            content_type="audio/wav"
        )
        
        # 创建大文件用于测试 (Create large file for testing)
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        self.large_audio_file = SimpleUploadedFile(
            "large_audio.wav",
            large_content,
            content_type="audio/wav"
        )
        
        # 创建无效格式文件 (Create invalid format file)
        self.invalid_format_file = SimpleUploadedFile(
            "test_file.txt",
            b"not an audio file",
            content_type="text/plain"
        )
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    def test_service_initialization_success(self, mock_api_key):
        """测试服务初始化成功 (Test successful service initialization)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        
        service = SpeechRecognitionService()
        
        self.assertEqual(service.api_key, self.mock_api_key)
        self.assertIsNotNone(service.whisper_url)
        self.assertGreater(service.timeout, 0)
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    def test_service_initialization_missing_api_key(self, mock_api_key):
        """测试缺少API密钥时的初始化失败 (Test initialization failure with missing API key)"""
        mock_api_key.__get__ = Mock(return_value=None)
        
        with self.assertRaises(MissingAPIKeyError):
            SpeechRecognitionService()
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    def test_validate_audio_file_success(self, mock_api_key):
        """测试有效音频文件验证成功 (Test successful validation of valid audio file)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        service = SpeechRecognitionService()
        
        result = service.validate_audio_file(self.valid_audio_file)
        
        self.assertTrue(result)
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    def test_validate_audio_file_no_file(self, mock_api_key):
        """测试无文件时的验证失败 (Test validation failure with no file)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        service = SpeechRecognitionService()
        
        with self.assertRaises(AudioValidationError) as context:
            service.validate_audio_file(None)
        
        self.assertIn("No audio file provided", str(context.exception))
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.AUDIO_UPLOAD_MAX_SIZE')
    def test_validate_audio_file_too_large(self, mock_max_size, mock_api_key):
        """测试文件过大时的验证失败 (Test validation failure with oversized file)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        mock_max_size.__get__ = Mock(return_value=10 * 1024 * 1024)  # 10MB
        service = SpeechRecognitionService()
        
        with self.assertRaises(AudioValidationError) as context:
            service.validate_audio_file(self.large_audio_file)
        
        self.assertIn("Audio file too large", str(context.exception))
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    def test_validate_audio_file_invalid_format(self, mock_api_key):
        """测试无效格式时的验证失败 (Test validation failure with invalid format)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        service = SpeechRecognitionService()
        
        with self.assertRaises(AudioFormatError) as context:
            service.validate_audio_file(self.invalid_format_file)
        
        self.assertIn("Unsupported audio format", str(context.exception))
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    def test_validate_input_success(self, mock_api_key):
        """测试输入验证成功 (Test successful input validation)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        service = SpeechRecognitionService()
        
        result = service.validate_input(self.valid_audio_file)
        
        self.assertTrue(result)
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    def test_validate_input_invalid_type(self, mock_api_key):
        """测试无效输入类型的验证失败 (Test validation failure with invalid input type)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        service = SpeechRecognitionService()
        
        result = service.validate_input("not_a_file")
        
        self.assertFalse(result)
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    @patch('speak_practice.services.speech_recognition.requests.post')
    def test_transcribe_audio_success(self, mock_post, mock_api_key):
        """测试音频转录成功 (Test successful audio transcription)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        
        # 模拟成功的API响应 (Mock successful API response)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "这是转录的中文文本"
        mock_post.return_value = mock_response
        
        service = SpeechRecognitionService()
        result = service.transcribe_audio(self.valid_audio_file)
        
        self.assertEqual(result, "这是转录的中文文本")
        
        # 验证API调用参数 (Verify API call parameters)
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertIn('headers', call_args.kwargs)
        self.assertIn('files', call_args.kwargs)
        self.assertIn('data', call_args.kwargs)
        self.assertIn('timeout', call_args.kwargs)
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    @patch('speak_practice.services.speech_recognition.requests.post')
    def test_transcribe_audio_empty_result(self, mock_post, mock_api_key):
        """测试空转录结果的处理 (Test handling of empty transcription result)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        
        # 模拟空响应 (Mock empty response)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_post.return_value = mock_response
        
        service = SpeechRecognitionService()
        
        with self.assertRaises(SpeechRecognitionError) as context:
            service.transcribe_audio(self.valid_audio_file)
        
        self.assertIn("Empty transcription result", str(context.exception))
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    @patch('speak_practice.services.speech_recognition.requests.post')
    def test_transcribe_audio_authentication_error(self, mock_post, mock_api_key):
        """测试API认证错误处理 (Test API authentication error handling)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        
        # 模拟认证失败响应 (Mock authentication failure response)
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        
        service = SpeechRecognitionService()
        
        with self.assertRaises(APIAuthenticationError):
            service.transcribe_audio(self.valid_audio_file)
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    @patch('speak_practice.services.speech_recognition.requests.post')
    def test_transcribe_audio_rate_limit_error(self, mock_post, mock_api_key):
        """测试API速率限制错误处理 (Test API rate limit error handling)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        
        # 模拟速率限制响应 (Mock rate limit response)
        mock_response = Mock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response
        
        service = SpeechRecognitionService()
        
        with self.assertRaises(APIError):  # 修正：429应该抛出APIError
            service.transcribe_audio(self.valid_audio_file)
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    @patch('speak_practice.services.speech_recognition.requests.post')
    def test_transcribe_audio_timeout_error(self, mock_post, mock_api_key):
        """测试API超时错误处理 (Test API timeout error handling)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        
        # 模拟超时异常 (Mock timeout exception)
        import requests
        mock_post.side_effect = requests.exceptions.Timeout()
        
        service = SpeechRecognitionService()
        
        with self.assertRaises(TranscriptionTimeoutError):
            service.transcribe_audio(self.valid_audio_file)
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    @patch('speak_practice.services.speech_recognition.requests.post')
    def test_transcribe_audio_connection_error(self, mock_post, mock_api_key):
        """测试连接错误处理 (Test connection error handling)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        
        # 模拟连接异常 (Mock connection exception)
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        service = SpeechRecognitionService()
        
        with self.assertRaises(SpeechRecognitionError) as context:
            service.transcribe_audio(self.valid_audio_file)
        
        self.assertIn("Connection error", str(context.exception))
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    @patch('speak_practice.services.speech_recognition.requests.post')
    def test_process_method_success(self, mock_post, mock_api_key):
        """测试process方法成功执行 (Test successful execution of process method)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        
        # 模拟成功的API响应 (Mock successful API response)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "测试转录文本"
        mock_post.return_value = mock_response
        
        service = SpeechRecognitionService()
        result = service.process(self.valid_audio_file)
        
        self.assertIsInstance(result, dict)
        self.assertIn('transcribed_text', result)
        self.assertIn('audio_duration', result)
        self.assertIn('audio_size', result)
        self.assertIn('audio_format', result)
        self.assertEqual(result['transcribed_text'], "测试转录文本")
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    def test_estimate_audio_duration(self, mock_api_key):
        """测试音频时长估算 (Test audio duration estimation)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        service = SpeechRecognitionService()
        
        duration = service._estimate_audio_duration(self.valid_audio_file)
        
        self.assertIsInstance(duration, float)
        self.assertGreater(duration, 0)
        self.assertLessEqual(duration, 300)  # 不应超过最大时长 (Should not exceed max duration)
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    def test_get_supported_formats(self, mock_api_key):
        """测试获取支持的格式列表 (Test getting supported formats list)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        service = SpeechRecognitionService()
        
        formats = service.get_supported_formats()
        
        self.assertIsInstance(formats, list)
        self.assertIn('audio/wav', formats)
        self.assertIn('audio/mp3', formats)
        self.assertIn('audio/webm', formats)
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    def test_get_max_file_size(self, mock_api_key):
        """测试获取最大文件大小 (Test getting maximum file size)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        service = SpeechRecognitionService()
        
        max_size = service.get_max_file_size()
        
        self.assertIsInstance(max_size, int)
        self.assertGreater(max_size, 0)
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    def test_get_service_status(self, mock_api_key):
        """测试获取服务状态 (Test getting service status)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        service = SpeechRecognitionService()
        
        status = service.get_service_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn('service_name', status)
        self.assertIn('api_key_configured', status)
        self.assertIn('api_url', status)
        self.assertIn('timeout', status)
        self.assertIn('max_file_size', status)
        self.assertIn('supported_formats', status)
        self.assertTrue(status['api_key_configured'])


class MockAudioFileTest(TestCase):
    """模拟音频文件测试类 (Mock Audio File Test Class)"""
    
    def setUp(self):
        """创建各种测试用的模拟音频文件 (Create various mock audio files for testing)"""
        self.mock_api_key = "sk-test123456789"
    
    def create_mock_audio_file(self, filename, content_type, size_mb=1):
        """
        创建模拟音频文件 (Create mock audio file)
        
        Args:
            filename: 文件名 (Filename)
            content_type: MIME类型 (MIME type)
            size_mb: 文件大小(MB) (File size in MB)
        """
        content = b"x" * (size_mb * 1024 * 1024)
        return SimpleUploadedFile(filename, content, content_type=content_type)
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    def test_various_audio_formats(self, mock_api_key):
        """测试各种音频格式 (Test various audio formats)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        service = SpeechRecognitionService()
        
        # 测试支持的格式 (Test supported formats)
        supported_formats = [
            ('test.wav', 'audio/wav'),
            ('test.mp3', 'audio/mp3'),
            ('test.webm', 'audio/webm'),
            ('test.ogg', 'audio/ogg'),
            ('test.m4a', 'audio/m4a')
        ]
        
        for filename, content_type in supported_formats:
            with self.subTest(format=content_type):
                audio_file = self.create_mock_audio_file(filename, content_type)
                result = service.validate_audio_file(audio_file)
                self.assertTrue(result, f"Format {content_type} should be supported")
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    def test_unsupported_audio_formats(self, mock_api_key):
        """测试不支持的音频格式 (Test unsupported audio formats)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        service = SpeechRecognitionService()
        
        # 测试不支持的格式 (Test unsupported formats)
        unsupported_formats = [
            ('test.txt', 'text/plain'),
            ('test.pdf', 'application/pdf'),
            ('test.jpg', 'image/jpeg'),
            ('test.mp4', 'video/mp4')
        ]
        
        for filename, content_type in unsupported_formats:
            with self.subTest(format=content_type):
                audio_file = self.create_mock_audio_file(filename, content_type)
                with self.assertRaises(AudioFormatError):
                    service.validate_audio_file(audio_file)
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.AUDIO_UPLOAD_MAX_SIZE')
    def test_file_size_limits(self, mock_max_size, mock_api_key):
        """测试文件大小限制 (Test file size limits)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        mock_max_size.__get__ = Mock(return_value=5 * 1024 * 1024)  # 5MB limit
        service = SpeechRecognitionService()
        
        # 测试小于限制的文件 (Test file smaller than limit)
        small_file = self.create_mock_audio_file('small.wav', 'audio/wav', 1)  # 1MB
        result = service.validate_audio_file(small_file)
        self.assertTrue(result)
        
        # 测试等于限制的文件 (Test file equal to limit)
        exact_file = self.create_mock_audio_file('exact.wav', 'audio/wav', 5)  # 5MB
        result = service.validate_audio_file(exact_file)
        self.assertTrue(result)
        
        # 测试超过限制的文件 (Test file larger than limit)
        large_file = self.create_mock_audio_file('large.wav', 'audio/wav', 10)  # 10MB
        with self.assertRaises(AudioValidationError):
            service.validate_audio_file(large_file)


class ErrorHandlingTest(TestCase):
    """错误处理测试类 (Error Handling Test Class)"""
    
    def setUp(self):
        """测试设置 (Test setup)"""
        self.mock_api_key = "sk-test123456789"
        self.valid_audio_file = SimpleUploadedFile(
            "test.wav",
            b"fake_audio_content",
            content_type="audio/wav"
        )
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    @patch('speak_practice.services.speech_recognition.requests.post')
    def test_api_error_responses(self, mock_post, mock_api_key):
        """测试各种API错误响应 (Test various API error responses)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        service = SpeechRecognitionService()
        
        # 测试不同的HTTP状态码 (Test different HTTP status codes)
        error_cases = [
            (400, SpeechRecognitionError),
            (401, APIAuthenticationError),
            (429, APIError),  # 修正：429应该抛出APIError
            (500, SpeechRecognitionError),
            (503, SpeechRecognitionError)
        ]
        
        for status_code, expected_exception in error_cases:
            with self.subTest(status_code=status_code):
                mock_response = Mock()
                mock_response.status_code = status_code
                mock_response.json.return_value = {
                    'error': {'message': f'Test error {status_code}'}
                }
                mock_response.text = f'Error {status_code}'
                mock_post.return_value = mock_response
                
                with self.assertRaises(expected_exception):
                    service.transcribe_audio(self.valid_audio_file)
    
    @patch('speak_practice.services.speech_recognition.VoiceServiceConfig.OPENAI_API_KEY')
    @patch('speak_practice.services.speech_recognition.requests.post')
    def test_network_errors(self, mock_post, mock_api_key):
        """测试网络错误 (Test network errors)"""
        mock_api_key.__get__ = Mock(return_value=self.mock_api_key)
        service = SpeechRecognitionService()
        
        import requests
        
        # 测试不同的网络异常 (Test different network exceptions)
        network_errors = [
            (requests.exceptions.Timeout(), TranscriptionTimeoutError),
            (requests.exceptions.ConnectionError(), SpeechRecognitionError),
            (requests.exceptions.RequestException(), SpeechRecognitionError)
        ]
        
        for exception, expected_exception in network_errors:
            with self.subTest(exception=type(exception).__name__):
                mock_post.side_effect = exception
                
                with self.assertRaises(expected_exception):
                    service.transcribe_audio(self.valid_audio_file)
                
                # 重置mock (Reset mock)
                mock_post.side_effect = None