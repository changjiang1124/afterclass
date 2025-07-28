"""
语音处理服务的基础接口定义 (Base interfaces for voice processing services)
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseVoiceService(ABC):
    """语音处理服务基础接口 (Base interface for voice processing services)"""
    
    def __init__(self):
        self.api_key = None
        self.timeout = 30  # 默认超时时间30秒 (Default timeout 30 seconds)
    
    @abstractmethod
    def validate_input(self, input_data: Any) -> bool:
        """验证输入数据 (Validate input data)"""
        pass
    
    @abstractmethod
    def process(self, input_data: Any) -> Dict[str, Any]:
        """处理输入数据 (Process input data)"""
        pass


class SpeechRecognitionInterface(BaseVoiceService):
    """语音识别服务接口 (Speech recognition service interface)"""
    
    @abstractmethod
    def transcribe_audio(self, audio_file) -> str:
        """
        转录音频文件为文本 (Transcribe audio file to text)
        
        Args:
            audio_file: Django UploadedFile对象 (Django UploadedFile object)
            
        Returns:
            str: 转录的文本 (Transcribed text)
        """
        pass
    
    @abstractmethod
    def validate_audio_file(self, audio_file) -> bool:
        """
        验证音频文件格式和大小 (Validate audio file format and size)
        
        Args:
            audio_file: Django UploadedFile对象 (Django UploadedFile object)
            
        Returns:
            bool: 验证结果 (Validation result)
        """
        pass


class TextToSpeechInterface(BaseVoiceService):
    """文本转语音服务接口 (Text-to-speech service interface)"""
    
    @abstractmethod
    def generate_speech(self, text: str, language_code: str = 'cmn-CN') -> str:
        """
        生成语音音频 (Generate speech audio)
        
        Args:
            text: 要转换的文本 (Text to convert)
            language_code: 语言代码 (Language code)
            
        Returns:
            str: Base64编码的音频数据 (Base64 encoded audio data)
        """
        pass
    
    @abstractmethod
    def validate_text_length(self, text: str) -> bool:
        """
        验证文本长度是否适合TTS (Validate text length for TTS)
        
        Args:
            text: 要验证的文本 (Text to validate)
            
        Returns:
            bool: 验证结果 (Validation result)
        """
        pass


class TranslationInterface(BaseVoiceService):
    """翻译服务接口 (Translation service interface)"""
    
    @abstractmethod
    def translate_text(self, text: str, source_lang: str = 'en', target_lang: str = 'zh') -> str:
        """
        翻译文本 (Translate text)
        
        Args:
            text: 要翻译的文本 (Text to translate)
            source_lang: 源语言代码 (Source language code)
            target_lang: 目标语言代码 (Target language code)
            
        Returns:
            str: 翻译后的文本 (Translated text)
        """
        pass
    
    @abstractmethod
    def get_translation_prompt(self, text: str, target_lang: str) -> str:
        """
        生成翻译提示词 (Generate translation prompt)
        
        Args:
            text: 要翻译的文本 (Text to translate)
            target_lang: 目标语言 (Target language)
            
        Returns:
            str: 翻译提示词 (Translation prompt)
        """
        pass


class CacheInterface(ABC):
    """缓存服务接口 (Cache service interface)"""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据 (Get cached data)"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, timeout: int = 3600) -> bool:
        """设置缓存数据 (Set cached data)"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除缓存数据 (Delete cached data)"""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """清空缓存 (Clear cache)"""
        pass