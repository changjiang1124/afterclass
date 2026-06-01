"""
消息内容格式化工具测试 (Message content formatting utilities tests)
"""

import unittest
from django.test import TestCase
from django.core.exceptions import ValidationError

from speak_practice.message_utils import MessageContentFormatter, MessageContentValidator


class MessageContentFormatterTest(TestCase):
    """消息内容格式化器测试 (Message content formatter tests)"""
    
    def test_serialize_user_text_message(self):
        """测试用户文本消息序列化 (Test user text message serialization)"""
        chinese_text = "你好，我想学习中文。"
        result = MessageContentFormatter.serialize_user_text_message(chinese_text)
        
        expected = {
            "chinese_text": chinese_text,
            "input_method": "text"
        }
        
        self.assertEqual(result, expected)
    
    def test_serialize_user_voice_message(self):
        """测试用户语音消息序列化 (Test user voice message serialization)"""
        chinese_text = "你好，我想学习中文。"
        english_translation = "Hello, I want to learn Chinese."
        audio_duration = 3.5
        
        result = MessageContentFormatter.serialize_user_voice_message(
            chinese_text, english_translation, audio_duration
        )
        
        expected = {
            "chinese_text": chinese_text,
            "english_translation": english_translation,
            "input_method": "voice",
            "audio_duration": audio_duration
        }
        
        self.assertEqual(result, expected)
    
    def test_serialize_user_voice_message_without_duration(self):
        """测试不带时长的用户语音消息序列化 (Test user voice message serialization without duration)"""
        chinese_text = "你好"
        english_translation = "Hello"
        
        result = MessageContentFormatter.serialize_user_voice_message(
            chinese_text, english_translation
        )
        
        expected = {
            "chinese_text": chinese_text,
            "english_translation": english_translation,
            "input_method": "voice"
        }
        
        self.assertEqual(result, expected)
        self.assertNotIn("audio_duration", result)
    
    def test_serialize_user_translation_message(self):
        """测试用户翻译消息序列化 (Test user translation message serialization)"""
        chinese_text = "你好，我想学习中文。"
        original_english = "Hello, I want to learn Chinese."
        
        result = MessageContentFormatter.serialize_user_translation_message(
            chinese_text, original_english
        )
        
        expected = {
            "chinese_text": chinese_text,
            "original_english": original_english,
            "input_method": "translation"
        }
        
        self.assertEqual(result, expected)
    
    def test_serialize_ai_message(self):
        """测试AI消息序列化 (Test AI message serialization)"""
        chinese = "你好！我很高兴帮助你学习中文。"
        pinyin = "nǐ hǎo! wǒ hěn gāo xìng bāng zhù nǐ xué xí zhōng wén."
        
        result = MessageContentFormatter.serialize_ai_message(
            chinese, pinyin, tts_generated=True
        )
        
        expected = {
            "chinese": chinese,
            "pinyin": pinyin,
            "tts_generated": True
        }
        
        self.assertEqual(result, expected)
    
    def test_serialize_ai_message_minimal(self):
        """测试最小AI消息序列化 (Test minimal AI message serialization)"""
        chinese = "好的。"
        
        result = MessageContentFormatter.serialize_ai_message(chinese)
        
        expected = {
            "chinese": chinese,
            "tts_generated": False
        }
        
        self.assertEqual(result, expected)
        self.assertNotIn("pinyin", result)
    
    def test_validate_message_content_text(self):
        """测试文本消息内容验证 (Test text message content validation)"""
        content = {
            "chinese_text": "你好",
            "input_method": "text"
        }
        
        result = MessageContentFormatter.validate_message_content(content, "text")
        self.assertTrue(result)
    
    def test_validate_message_content_voice(self):
        """测试语音消息内容验证 (Test voice message content validation)"""
        content = {
            "chinese_text": "你好",
            "english_translation": "Hello",
            "input_method": "voice"
        }
        
        result = MessageContentFormatter.validate_message_content(content, "voice")
        self.assertTrue(result)
    
    def test_validate_message_content_translation(self):
        """测试翻译消息内容验证 (Test translation message content validation)"""
        content = {
            "chinese_text": "你好",
            "original_english": "Hello",
            "input_method": "translation"
        }
        
        result = MessageContentFormatter.validate_message_content(content, "translation")
        self.assertTrue(result)
    
    def test_validate_message_content_missing_field(self):
        """测试缺少必需字段的消息内容验证 (Test message content validation with missing required field)"""
        content = {
            "input_method": "voice"
            # Missing chinese_text and english_translation
        }
        
        with self.assertRaises(ValidationError) as context:
            MessageContentFormatter.validate_message_content(content, "voice")
        
        self.assertIn("Missing required field", str(context.exception))
    
    def test_validate_message_content_empty_field(self):
        """测试空字段的消息内容验证 (Test message content validation with empty field)"""
        content = {
            "chinese_text": "",  # Empty field
            "english_translation": "Hello",
            "input_method": "voice"
        }
        
        with self.assertRaises(ValidationError) as context:
            MessageContentFormatter.validate_message_content(content, "voice")
        
        self.assertIn("cannot be empty", str(context.exception))
    
    def test_validate_message_content_unsupported_method(self):
        """测试不支持的输入方法验证 (Test validation with unsupported input method)"""
        content = {"chinese_text": "你好"}
        
        with self.assertRaises(ValidationError) as context:
            MessageContentFormatter.validate_message_content(content, "unsupported")
        
        self.assertIn("Unsupported input method", str(context.exception))
    
    def test_get_display_text_user_message(self):
        """测试获取用户消息显示文本 (Test getting display text for user message)"""
        content = {
            "chinese_text": "你好，世界！",
            "input_method": "text"
        }
        
        result = MessageContentFormatter.get_display_text(content, "text")
        self.assertEqual(result, "你好，世界！")
    
    def test_get_display_text_ai_message(self):
        """测试获取AI消息显示文本 (Test getting display text for AI message)"""
        content = {
            "chinese": "你好！我很高兴帮助你。",
            "tts_generated": True
        }
        
        result = MessageContentFormatter.get_display_text(content, "ai")
        self.assertEqual(result, "你好！我很高兴帮助你。")
    
    def test_is_backward_compatible_string(self):
        """测试字符串内容的向后兼容性 (Test backward compatibility for string content)"""
        content = "这是一个简单的字符串消息"
        result = MessageContentFormatter.is_backward_compatible(content)
        self.assertTrue(result)
    
    def test_is_backward_compatible_new_format(self):
        """测试新格式内容的向后兼容性 (Test backward compatibility for new format content)"""
        content = {
            "chinese_text": "你好",
            "input_method": "text"
        }
        result = MessageContentFormatter.is_backward_compatible(content)
        self.assertTrue(result)
    
    def test_migrate_legacy_content_string_user(self):
        """测试迁移用户字符串格式内容 (Test migrating legacy string content for user)"""
        legacy_content = "你好，我想学习中文。"
        result = MessageContentFormatter.migrate_legacy_content(legacy_content, "user")
        
        expected = {
            "chinese_text": "你好，我想学习中文。",
            "input_method": "text"
        }
        
        self.assertEqual(result, expected)
    
    def test_migrate_legacy_content_string_ai(self):
        """测试迁移AI字符串格式内容 (Test migrating legacy string content for AI)"""
        legacy_content = "你好！我很高兴帮助你学习中文。"
        result = MessageContentFormatter.migrate_legacy_content(legacy_content, "ai")
        
        expected = {
            "chinese": "你好！我很高兴帮助你学习中文。",
            "tts_generated": False
        }
        
        self.assertEqual(result, expected)
    
    def test_migrate_legacy_content_dict_user(self):
        """测试迁移用户字典格式内容 (Test migrating legacy dict content for user)"""
        legacy_content = {"text": "你好，世界！"}
        result = MessageContentFormatter.migrate_legacy_content(legacy_content, "user")
        
        expected = {
            "chinese_text": "你好，世界！",
            "input_method": "text"
        }
        
        self.assertEqual(result, expected)


class MessageContentValidatorTest(TestCase):
    """消息内容验证器测试 (Message content validator tests)"""
    
    def test_validate_chinese_text_valid(self):
        """测试有效中文文本验证 (Test valid Chinese text validation)"""
        valid_texts = [
            "你好",
            "我想学习中文。",
            "这是一个很长的句子，包含了很多中文字符和标点符号！",
            "Hello 你好 mixed text"
        ]
        
        for text in valid_texts:
            with self.subTest(text=text):
                result = MessageContentValidator.validate_chinese_text(text)
                self.assertTrue(result)
    
    def test_validate_chinese_text_invalid(self):
        """测试无效中文文本验证 (Test invalid Chinese text validation)"""
        invalid_texts = [
            "",
            "   ",  # Only whitespace
            None,
            123,  # Not a string
            "x" * 5001  # Too long
        ]
        
        for text in invalid_texts:
            with self.subTest(text=text):
                result = MessageContentValidator.validate_chinese_text(text)
                self.assertFalse(result)
    
    def test_validate_audio_duration_valid(self):
        """测试有效音频时长验证 (Test valid audio duration validation)"""
        valid_durations = [0.1, 1.0, 30.5, 120, 300]
        
        for duration in valid_durations:
            with self.subTest(duration=duration):
                result = MessageContentValidator.validate_audio_duration(duration)
                self.assertTrue(result)
    
    def test_validate_audio_duration_invalid(self):
        """测试无效音频时长验证 (Test invalid audio duration validation)"""
        invalid_durations = [
            0,      # Too short
            0.05,   # Too short
            301,    # Too long
            -1,     # Negative
            "5.0",  # String
            None    # None
        ]
        
        for duration in invalid_durations:
            with self.subTest(duration=duration):
                result = MessageContentValidator.validate_audio_duration(duration)
                self.assertFalse(result)
    
    def test_sanitize_text_content(self):
        """测试文本内容清理 (Test text content sanitization)"""
        test_cases = [
            ("  你好   世界  ", "你好 世界"),
            ("你好<script>alert('xss')</script>", "你好scriptalert(xss)/script"),
            ('包含"引号"的文本', "包含引号的文本"),
            ("包含&特殊&字符", "包含特殊字符"),
            ("正常的中文文本", "正常的中文文本"),
            (123, "123")  # Non-string input
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = MessageContentValidator.sanitize_text_content(input_text)
                self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()