"""
翻译服务单元测试 (Translation Service Unit Tests)
"""

import unittest
from unittest.mock import patch, Mock, MagicMock
import json
import requests
from django.test import TestCase

from speak_practice.services.translation import TranslationService
from speak_practice.services.exceptions import (
    TranslationError,
    TranslationTimeoutError,
    UnsupportedLanguageError,
    APIError,
    APIAuthenticationError,
    MissingAPIKeyError
)
from speak_practice.services.config import VoiceServiceConfig


class TranslationServiceTest(TestCase):
    """翻译服务测试类 (Translation service test class)"""
    
    def setUp(self):
        """测试设置 (Test setup)"""
        self.service = TranslationService()
        self.test_text_en = "Hello, how are you today?"
        self.test_text_zh = "你好，你今天怎么样？"
        self.expected_translation_zh = "你好，你今天好吗？"
        self.expected_translation_en = "Hello, how are you today?"
    
    def test_service_initialization(self):
        """测试服务初始化 (Test service initialization)"""
        self.assertIsNotNone(self.service.api_key)
        self.assertEqual(self.service.api_url, VoiceServiceConfig.OPENAI_CHAT_URL)
        self.assertEqual(self.service.timeout, VoiceServiceConfig.TRANSLATION_TIMEOUT)
        self.assertIn('zh', self.service.supported_languages)
        self.assertIn('en', self.service.supported_languages)
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': ''})
    def test_missing_api_key_error(self):
        """测试API密钥缺失错误 (Test missing API key error)"""
        with patch('speak_practice.services.config.VoiceServiceConfig.OPENAI_API_KEY', None):
            with self.assertRaises(MissingAPIKeyError):
                TranslationService()
    
    def test_validate_input_valid_text(self):
        """测试有效文本输入验证 (Test valid text input validation)"""
        self.assertTrue(self.service.validate_input(self.test_text_en))
        self.assertTrue(self.service.validate_input(self.test_text_zh))
        self.assertTrue(self.service.validate_input("Short text"))
    
    def test_validate_input_invalid_text(self):
        """测试无效文本输入验证 (Test invalid text input validation)"""
        self.assertFalse(self.service.validate_input(""))
        self.assertFalse(self.service.validate_input("   "))
        self.assertFalse(self.service.validate_input(None))
        self.assertFalse(self.service.validate_input(123))
        self.assertFalse(self.service.validate_input([]))
        
        # 测试超长文本 (Test overly long text)
        long_text = "a" * (VoiceServiceConfig.TTS_MAX_TEXT_LENGTH + 1)
        self.assertFalse(self.service.validate_input(long_text))
    
    def test_supported_languages(self):
        """测试支持的语言 (Test supported languages)"""
        supported = self.service.get_supported_languages()
        self.assertIn('zh', supported)
        self.assertIn('en', supported)
        self.assertIn('zh-cn', supported)
        self.assertIn('zh-tw', supported)
        self.assertIn('cmn', supported)
        
        self.assertTrue(self.service.is_language_supported('zh'))
        self.assertTrue(self.service.is_language_supported('en'))
        self.assertFalse(self.service.is_language_supported('fr'))
        self.assertFalse(self.service.is_language_supported('invalid'))
    
    def test_get_translation_prompt_en_to_zh(self):
        """测试英文到中文翻译提示词生成 (Test English to Chinese translation prompt generation)"""
        prompt = self.service.get_translation_prompt(self.test_text_en, 'zh')
        self.assertIn('Simplified Chinese', prompt)
        self.assertIn('Chinese language learning', prompt)
        self.assertIn('conversational translations', prompt)
        self.assertIn('simplified Chinese characters', prompt)
    
    def test_get_translation_prompt_zh_to_en(self):
        """测试中文到英文翻译提示词生成 (Test Chinese to English translation prompt generation)"""
        prompt = self.service.get_translation_prompt(self.test_text_zh, 'en')
        self.assertIn('English', prompt)
        self.assertIn('Chinese text', prompt)
        self.assertIn('accurate, natural translations', prompt)
    
    def test_get_translation_prompt_other_languages(self):
        """测试其他语言翻译提示词生成 (Test other language translation prompt generation)"""
        prompt = self.service.get_translation_prompt(self.test_text_en, 'zh-tw')
        self.assertIn('Traditional Chinese', prompt)
        
        prompt = self.service.get_translation_prompt(self.test_text_en, 'cmn')
        self.assertIn('Mandarin Chinese', prompt)
    
    @patch('requests.post')
    def test_translate_text_success_en_to_zh(self, mock_post):
        """测试成功的英文到中文翻译 (Test successful English to Chinese translation)"""
        # 模拟成功的API响应 (Mock successful API response)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': self.expected_translation_zh
                }
            }]
        }
        mock_post.return_value = mock_response
        
        result = self.service.translate_text(self.test_text_en, 'en', 'zh')
        
        self.assertEqual(result, self.expected_translation_zh)
        mock_post.assert_called_once()
        
        # 验证API调用参数 (Verify API call parameters)
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], VoiceServiceConfig.OPENAI_CHAT_URL)
        self.assertIn('Authorization', call_args[1]['headers'])
        self.assertEqual(call_args[1]['json']['model'], 'gpt-4o-mini')
        self.assertEqual(call_args[1]['timeout'], VoiceServiceConfig.TRANSLATION_TIMEOUT)
    
    @patch('requests.post')
    def test_translate_text_success_zh_to_en(self, mock_post):
        """测试成功的中文到英文翻译 (Test successful Chinese to English translation)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': self.expected_translation_en
                }
            }]
        }
        mock_post.return_value = mock_response
        
        result = self.service.translate_text(self.test_text_zh, 'zh', 'en')
        
        self.assertEqual(result, self.expected_translation_en)
        mock_post.assert_called_once()
    
    def test_translate_text_unsupported_source_language(self):
        """测试不支持的源语言 (Test unsupported source language)"""
        with self.assertRaises(UnsupportedLanguageError):
            self.service.translate_text(self.test_text_en, 'fr', 'zh')
    
    def test_translate_text_unsupported_target_language(self):
        """测试不支持的目标语言 (Test unsupported target language)"""
        with self.assertRaises(UnsupportedLanguageError):
            self.service.translate_text(self.test_text_en, 'en', 'fr')
    
    def test_translate_text_empty_text(self):
        """测试空文本翻译 (Test empty text translation)"""
        with self.assertRaises(TranslationError):
            self.service.translate_text("", 'en', 'zh')
        
        with self.assertRaises(TranslationError):
            self.service.translate_text("   ", 'en', 'zh')
    
    def test_translate_text_too_long(self):
        """测试超长文本翻译 (Test overly long text translation)"""
        long_text = "a" * (VoiceServiceConfig.TTS_MAX_TEXT_LENGTH + 1)
        with self.assertRaises(TranslationError):
            self.service.translate_text(long_text, 'en', 'zh')
    
    @patch('requests.post')
    def test_translate_text_api_authentication_error(self, mock_post):
        """测试API认证错误 (Test API authentication error)"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        
        with self.assertRaises(APIAuthenticationError):
            self.service.translate_text(self.test_text_en, 'en', 'zh')
    
    @patch('requests.post')
    def test_translate_text_api_rate_limit(self, mock_post):
        """测试API速率限制 (Test API rate limit)"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response
        
        with self.assertRaises(APIError) as context:
            self.service.translate_text(self.test_text_en, 'en', 'zh')
        
        self.assertEqual(context.exception.error_code, 'api_rate_limit')
    
    @patch('requests.post')
    def test_translate_text_api_server_error(self, mock_post):
        """测试API服务器错误 (Test API server error)"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json.side_effect = ValueError("No JSON object could be decoded")
        mock_post.return_value = mock_response
        
        with self.assertRaises(TranslationError):
            self.service.translate_text(self.test_text_en, 'en', 'zh')
    
    @patch('requests.post')
    def test_translate_text_api_error_with_json(self, mock_post):
        """测试带JSON错误信息的API错误 (Test API error with JSON error message)"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'error': {
                'message': 'Invalid request format'
            }
        }
        mock_post.return_value = mock_response
        
        with self.assertRaises(TranslationError) as context:
            self.service.translate_text(self.test_text_en, 'en', 'zh')
        
        self.assertIn('Invalid request format', str(context.exception))
    
    @patch('requests.post')
    def test_translate_text_timeout_error(self, mock_post):
        """测试翻译超时错误 (Test translation timeout error)"""
        mock_post.side_effect = requests.exceptions.Timeout()
        
        with self.assertRaises(TranslationTimeoutError):
            self.service.translate_text(self.test_text_en, 'en', 'zh')
    
    @patch('requests.post')
    def test_translate_text_connection_error(self, mock_post):
        """测试连接错误 (Test connection error)"""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        with self.assertRaises(TranslationError) as context:
            self.service.translate_text(self.test_text_en, 'en', 'zh')
        
        self.assertIn('Connection error', str(context.exception))
    
    @patch('requests.post')
    def test_translate_text_request_exception(self, mock_post):
        """测试请求异常 (Test request exception)"""
        mock_post.side_effect = requests.exceptions.RequestException("Request failed")
        
        with self.assertRaises(TranslationError) as context:
            self.service.translate_text(self.test_text_en, 'en', 'zh')
        
        self.assertIn('Request error', str(context.exception))
    
    @patch('requests.post')
    def test_translate_text_empty_response(self, mock_post):
        """测试空响应 (Test empty response)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': '   '  # 空白响应 (Empty response)
                }
            }]
        }
        mock_post.return_value = mock_response
        
        with self.assertRaises(TranslationError) as context:
            self.service.translate_text(self.test_text_en, 'en', 'zh')
        
        self.assertIn('Empty translation result', str(context.exception))
    
    def test_process_method_valid_input(self):
        """测试process方法的有效输入 (Test process method with valid input)"""
        with patch.object(self.service, 'translate_text', return_value=self.expected_translation_zh):
            input_data = {
                'text': self.test_text_en,
                'source_lang': 'en',
                'target_lang': 'zh'
            }
            
            result = self.service.process(input_data)
            
            self.assertEqual(result['translated_text'], self.expected_translation_zh)
            self.assertEqual(result['source_language'], 'en')
            self.assertEqual(result['target_language'], 'zh')
            self.assertEqual(result['original_text'], self.test_text_en)
            self.assertEqual(result['character_count'], len(self.expected_translation_zh))
    
    def test_process_method_invalid_input_type(self):
        """测试process方法的无效输入类型 (Test process method with invalid input type)"""
        with self.assertRaises(TranslationError):
            self.service.process("invalid input")
        
        with self.assertRaises(TranslationError):
            self.service.process(123)
        
        with self.assertRaises(TranslationError):
            self.service.process([])
    
    def test_process_method_missing_text(self):
        """测试process方法缺少文本 (Test process method with missing text)"""
        input_data = {
            'source_lang': 'en',
            'target_lang': 'zh'
        }
        
        with self.assertRaises(TranslationError):
            self.service.process(input_data)
    
    def test_process_method_default_languages(self):
        """测试process方法的默认语言 (Test process method with default languages)"""
        with patch.object(self.service, 'translate_text', return_value=self.expected_translation_zh) as mock_translate:
            input_data = {
                'text': self.test_text_en
            }
            
            result = self.service.process(input_data)
            
            mock_translate.assert_called_once_with(self.test_text_en, 'en', 'zh')
            self.assertEqual(result['source_language'], 'en')
            self.assertEqual(result['target_language'], 'zh')
    
    def test_get_service_status(self):
        """测试获取服务状态 (Test get service status)"""
        status = self.service.get_service_status()
        
        self.assertEqual(status['service_name'], 'OpenAI GPT-4 Translation')
        self.assertTrue(status['api_key_configured'])
        self.assertEqual(status['api_url'], VoiceServiceConfig.OPENAI_CHAT_URL)
        self.assertEqual(status['timeout'], VoiceServiceConfig.TRANSLATION_TIMEOUT)
        self.assertIn('supported_languages', status)
        self.assertEqual(status['max_text_length'], VoiceServiceConfig.TTS_MAX_TEXT_LENGTH)


class TranslationServiceIntegrationTest(TestCase):
    """翻译服务集成测试类 (Translation service integration test class)"""
    
    def setUp(self):
        """测试设置 (Test setup)"""
        self.service = TranslationService()
    
    @unittest.skipUnless(
        hasattr(VoiceServiceConfig, 'OPENAI_API_KEY') and VoiceServiceConfig.OPENAI_API_KEY,
        "OpenAI API key not configured"
    )
    def test_real_translation_en_to_zh(self):
        """测试真实的英文到中文翻译 (Test real English to Chinese translation)"""
        text = "Hello, how are you?"
        result = self.service.translate_text(text, 'en', 'zh')
        
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        # 检查是否包含中文字符 (Check if contains Chinese characters)
        self.assertTrue(any('\u4e00' <= char <= '\u9fff' for char in result))
    
    @unittest.skipUnless(
        hasattr(VoiceServiceConfig, 'OPENAI_API_KEY') and VoiceServiceConfig.OPENAI_API_KEY,
        "OpenAI API key not configured"
    )
    def test_real_translation_zh_to_en(self):
        """测试真实的中文到英文翻译 (Test real Chinese to English translation)"""
        text = "你好，你好吗？"
        result = self.service.translate_text(text, 'zh', 'en')
        
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        # 检查是否包含英文字符 (Check if contains English characters)
        self.assertTrue(any(char.isalpha() and ord(char) < 128 for char in result))
    
    @unittest.skipUnless(
        hasattr(VoiceServiceConfig, 'OPENAI_API_KEY') and VoiceServiceConfig.OPENAI_API_KEY,
        "OpenAI API key not configured"
    )
    def test_real_process_method(self):
        """测试真实的process方法 (Test real process method)"""
        input_data = {
            'text': 'Good morning!',
            'source_lang': 'en',
            'target_lang': 'zh'
        }
        
        result = self.service.process(input_data)
        
        self.assertIn('translated_text', result)
        self.assertIn('source_language', result)
        self.assertIn('target_language', result)
        self.assertIn('original_text', result)
        self.assertIn('character_count', result)
        
        self.assertEqual(result['source_language'], 'en')
        self.assertEqual(result['target_language'], 'zh')
        self.assertEqual(result['original_text'], 'Good morning!')
        self.assertGreater(len(result['translated_text']), 0)


if __name__ == '__main__':
    unittest.main()