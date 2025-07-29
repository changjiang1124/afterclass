"""
消息内容格式化工具 (Message content formatting utilities)

This module provides utilities for serializing and deserializing chat message content
based on different input methods (text, voice, translation).
"""

import json
from typing import Dict, Any, Optional
from django.core.exceptions import ValidationError


class MessageContentFormatter:
    """消息内容格式化器 (Message content formatter)"""
    
    # 支持的输入方法 (Supported input methods)
    SUPPORTED_INPUT_METHODS = ['text', 'voice', 'translation']
    
    # 必需字段映射 (Required fields mapping)
    REQUIRED_FIELDS = {
        'text': ['chinese_text'],
        'voice': ['chinese_text', 'english_translation'],
        'translation': ['chinese_text', 'original_english']
    }
    
    # 可选字段映射 (Optional fields mapping)
    OPTIONAL_FIELDS = {
        'text': ['input_method'],
        'voice': ['input_method', 'audio_duration'],
        'translation': ['input_method']
    }
    
    @classmethod
    def serialize_user_text_message(cls, chinese_text: str) -> Dict[str, Any]:
        """
        序列化用户文本消息 (Serialize user text message)
        
        Args:
            chinese_text: 用户输入的中文文本 (Chinese text input by user)
            
        Returns:
            Dict containing serialized message content
        """
        return {
            "chinese_text": chinese_text,
            "input_method": "text"
        }
    
    @classmethod
    def serialize_user_voice_message(cls, chinese_text: str, english_translation: str, 
                                   audio_duration: Optional[float] = None) -> Dict[str, Any]:
        """
        序列化用户语音消息 (Serialize user voice message)
        
        Args:
            chinese_text: 转录的中文文本 (Transcribed Chinese text)
            english_translation: 英文翻译 (English translation)
            audio_duration: 音频时长（秒）(Audio duration in seconds)
            
        Returns:
            Dict containing serialized message content
        """
        content = {
            "chinese_text": chinese_text,
            "english_translation": english_translation,
            "input_method": "voice"
        }
        
        if audio_duration is not None:
            content["audio_duration"] = audio_duration
            
        return content
    
    @classmethod
    def serialize_user_translation_message(cls, chinese_text: str, 
                                         original_english: str) -> Dict[str, Any]:
        """
        序列化用户翻译消息 (Serialize user translation message)
        
        Args:
            chinese_text: 翻译的中文文本 (Translated Chinese text)
            original_english: 原始英文文本 (Original English text)
            
        Returns:
            Dict containing serialized message content
        """
        return {
            "chinese_text": chinese_text,
            "original_english": original_english,
            "input_method": "translation"
        }
    
    @classmethod
    def serialize_ai_message(cls, chinese: str, pinyin: Optional[str] = None, 
                           tts_generated: bool = False) -> Dict[str, Any]:
        """
        序列化AI回复消息 (Serialize AI reply message)
        
        Args:
            chinese: AI的中文回复 (AI's Chinese reply)
            pinyin: 拼音标注 (Pinyin annotation)
            tts_generated: 是否生成了TTS (Whether TTS was generated)
            
        Returns:
            Dict containing serialized message content
        """
        content = {
            "chinese": chinese,
            "tts_generated": tts_generated
        }
        
        if pinyin:
            content["pinyin"] = pinyin
            
        return content
    
    @classmethod
    def validate_message_content(cls, content: Dict[str, Any], 
                               input_method: str) -> bool:
        """
        验证消息内容格式 (Validate message content format)
        
        Args:
            content: 消息内容字典 (Message content dictionary)
            input_method: 输入方法 (Input method)
            
        Returns:
            bool: True if valid, False otherwise
            
        Raises:
            ValidationError: If content format is invalid
        """
        if input_method not in cls.SUPPORTED_INPUT_METHODS:
            raise ValidationError(f"Unsupported input method: {input_method}")
        
        # 检查必需字段 (Check required fields)
        required_fields = cls.REQUIRED_FIELDS.get(input_method, [])
        for field in required_fields:
            if field not in content:
                raise ValidationError(f"Missing required field '{field}' for input method '{input_method}'")
            
            # 检查字段值不为空 (Check field value is not empty)
            if not content[field] or (isinstance(content[field], str) and not content[field].strip()):
                raise ValidationError(f"Field '{field}' cannot be empty for input method '{input_method}'")
        
        return True
    
    @classmethod
    def get_display_text(cls, content: Dict[str, Any], input_method: str) -> str:
        """
        获取用于显示的文本 (Get text for display)
        
        Args:
            content: 消息内容字典 (Message content dictionary)
            input_method: 输入方法 (Input method)
            
        Returns:
            str: Display text
        """
        if input_method in ['text', 'voice', 'translation']:
            return content.get('chinese_text', '')
        elif 'chinese' in content:  # AI message
            return content.get('chinese', '')
        else:
            return str(content)
    
    @classmethod
    def is_backward_compatible(cls, content: Dict[str, Any]) -> bool:
        """
        检查内容是否向后兼容 (Check if content is backward compatible)
        
        Args:
            content: 消息内容字典 (Message content dictionary)
            
        Returns:
            bool: True if backward compatible
        """
        # 如果内容是简单字符串或包含旧格式，则认为是向后兼容的
        # (If content is simple string or contains old format, consider it backward compatible)
        if isinstance(content, str):
            return True
            
        # 检查是否包含新格式的标识字段 (Check if contains new format identifier fields)
        new_format_indicators = ['input_method', 'chinese_text', 'chinese']
        return any(indicator in content for indicator in new_format_indicators)
    
    @classmethod
    def migrate_legacy_content(cls, content: Any, sender_type: str) -> Dict[str, Any]:
        """
        迁移旧格式内容到新格式 (Migrate legacy content to new format)
        
        Args:
            content: 旧格式内容 (Legacy format content)
            sender_type: 发送者类型 (Sender type: 'user' or 'ai')
            
        Returns:
            Dict containing migrated content
        """
        if isinstance(content, str):
            # 简单字符串格式 (Simple string format)
            if sender_type == 'user':
                return cls.serialize_user_text_message(content)
            else:  # AI message
                return cls.serialize_ai_message(content)
        elif isinstance(content, dict):
            # 如果已经是新格式，直接返回 (If already new format, return directly)
            if cls.is_backward_compatible(content):
                return content
            else:
                # 尝试从旧字典格式迁移 (Try to migrate from old dict format)
                if sender_type == 'user':
                    chinese_text = content.get('text', content.get('message', ''))
                    return cls.serialize_user_text_message(chinese_text)
                else:  # AI message
                    chinese = content.get('text', content.get('message', ''))
                    return cls.serialize_ai_message(chinese)
        else:
            # 其他格式，转换为字符串处理 (Other formats, convert to string)
            content_str = str(content)
            if sender_type == 'user':
                return cls.serialize_user_text_message(content_str)
            else:
                return cls.serialize_ai_message(content_str)


class MessageContentValidator:
    """消息内容验证器 (Message content validator)"""
    
    @staticmethod
    def validate_chinese_text(text: str) -> bool:
        """
        验证中文文本 (Validate Chinese text)
        
        Args:
            text: 要验证的文本 (Text to validate)
            
        Returns:
            bool: True if valid
        """
        if not text or not isinstance(text, str):
            return False
        
        # 检查文本长度 (Check text length)
        if len(text.strip()) == 0:
            return False
        
        # 检查文本长度不超过限制 (Check text length doesn't exceed limit)
        if len(text) > 5000:  # 5000字符限制 (5000 character limit)
            return False
        
        return True
    
    @staticmethod
    def validate_audio_duration(duration: float) -> bool:
        """
        验证音频时长 (Validate audio duration)
        
        Args:
            duration: 音频时长（秒）(Audio duration in seconds)
            
        Returns:
            bool: True if valid
        """
        if not isinstance(duration, (int, float)):
            return False
        
        # 音频时长应该在合理范围内 (Audio duration should be within reasonable range)
        return 0.1 <= duration <= 300  # 0.1秒到5分钟 (0.1 seconds to 5 minutes)
    
    @staticmethod
    def sanitize_text_content(text: str) -> str:
        """
        清理文本内容 (Sanitize text content)
        
        Args:
            text: 原始文本 (Raw text)
            
        Returns:
            str: Sanitized text
        """
        if not isinstance(text, str):
            text = str(text)
        
        # 移除多余的空白字符 (Remove excessive whitespace)
        text = ' '.join(text.split())
        
        # 移除潜在的危险字符 (Remove potentially dangerous characters)
        dangerous_chars = ['<', '>', '"', "'", '&']
        for char in dangerous_chars:
            text = text.replace(char, '')
        
        return text.strip()