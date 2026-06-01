"""
翻译功能集成测试 (Translation functionality integration tests)
"""

import unittest
from django.test import TestCase
from speak_practice.services.translation import TranslationService
from speak_practice.services.config import VoiceServiceConfig


class TranslationIntegrationTest(TestCase):
    """翻译集成测试类 (Translation integration test class)"""
    
    def setUp(self):
        """测试设置 (Test setup)"""
        self.service = TranslationService()
    
    def test_translation_service_basic_functionality(self):
        """测试翻译服务基本功能 (Test translation service basic functionality)"""
        # 测试英文到中文翻译 (Test English to Chinese translation)
        result = self.service.translate_text("Hello", "en", "zh")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        
        # 测试process方法 (Test process method)
        input_data = {
            'text': 'Good morning',
            'source_lang': 'en',
            'target_lang': 'zh'
        }
        
        process_result = self.service.process(input_data)
        self.assertIn('translated_text', process_result)
        self.assertIn('source_language', process_result)
        self.assertIn('target_language', process_result)
        self.assertIn('original_text', process_result)
        self.assertIn('character_count', process_result)
    
    def test_translation_service_validation(self):
        """测试翻译服务验证功能 (Test translation service validation)"""
        # 测试输入验证 (Test input validation)
        self.assertTrue(self.service.validate_input("Valid text"))
        self.assertFalse(self.service.validate_input(""))
        self.assertFalse(self.service.validate_input(None))
        
        # 测试语言支持 (Test language support)
        self.assertTrue(self.service.is_language_supported('zh'))
        self.assertTrue(self.service.is_language_supported('en'))
        self.assertFalse(self.service.is_language_supported('invalid'))
    
    def test_translation_service_status(self):
        """测试翻译服务状态 (Test translation service status)"""
        status = self.service.get_service_status()
        self.assertIn('service_name', status)
        self.assertIn('api_key_configured', status)
        self.assertIn('supported_languages', status)
        self.assertTrue(status['api_key_configured'])


if __name__ == '__main__':
    unittest.main()