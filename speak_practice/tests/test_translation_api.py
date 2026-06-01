"""
翻译API端点测试 (Translation API Endpoint Tests)
"""

import json
from unittest.mock import patch, Mock
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from speak_practice.services.exceptions import (
    TranslationError,
    TranslationTimeoutError,
    UnsupportedLanguageError,
    TTSError
)


class TranslationAPITest(TestCase):
    """翻译API测试类 (Translation API test class)"""
    
    def setUp(self):
        """测试设置 (Test setup)"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_login(self.user)
        self.url = reverse('speak_practice:translate_text_api')
        
        # 测试数据 (Test data)
        self.test_data = {
            'text': 'Hello, how are you today?'
        }
        self.expected_translation = '你好，你今天怎么样？'
    
    def make_api_request(self, data, method='POST'):
        """创建带有正确头部的API请求 (Create API request with correct headers)"""
        if method == 'POST':
            return self.client.post(
                self.url,
                json.dumps(data) if isinstance(data, dict) else data,
                content_type='application/json',
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
        elif method == 'GET':
            return self.client.get(self.url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    
    def test_translate_api_success(self):
        """测试翻译API成功响应 (Test translation API success response)"""
        with patch('speak_practice.services.translation.TranslationService.process') as mock_process, \
             patch('speak_practice.services.text_to_speech.tts_service.generate_speech') as mock_tts:
            
            # 模拟翻译服务响应 (Mock translation service response)
            mock_process.return_value = {
                'translated_text': self.expected_translation,
                'source_language': 'en',
                'target_language': 'zh',
                'original_text': self.test_data['text'],
                'character_count': len(self.expected_translation)
            }
            
            # 模拟TTS服务响应 (Mock TTS service response)
            mock_tts.return_value = 'base64_audio_data'
            
            response = self.make_api_request(self.test_data)
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            
            self.assertTrue(data['success'])
            self.assertEqual(data['chinese_text'], self.expected_translation)
            self.assertEqual(data['tts_audio'], 'base64_audio_data')
            self.assertTrue(data['tts_available'])
            self.assertIn('translation_info', data)
            self.assertIn('csrf_token', data)
            
            # 验证服务调用 (Verify service calls)
            mock_process.assert_called_once()
            mock_tts.assert_called_once_with(self.expected_translation, 'cmn-CN')
    
    def test_translate_api_success_without_tts(self):
        """测试翻译API成功但TTS失败 (Test translation API success but TTS failure)"""
        with patch('speak_practice.services.translation.TranslationService.process') as mock_process, \
             patch('speak_practice.services.text_to_speech.tts_service.generate_speech') as mock_tts:
            
            mock_process.return_value = {
                'translated_text': self.expected_translation,
                'source_language': 'en',
                'target_language': 'zh',
                'original_text': self.test_data['text'],
                'character_count': len(self.expected_translation)
            }
            
            # 模拟TTS失败 (Mock TTS failure)
            mock_tts.side_effect = TTSError("TTS service unavailable")
            
            response = self.make_api_request(self.test_data)
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            
            self.assertTrue(data['success'])
            self.assertEqual(data['chinese_text'], self.expected_translation)
            self.assertIsNone(data['tts_audio'])
            self.assertFalse(data['tts_available'])


if __name__ == '__main__':
    import unittest
    unittest.main()