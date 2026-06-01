"""
文本转语音服务实现 (Text-to-Speech Service Implementation)
"""

import base64
import json
import logging
import requests
from typing import Optional, Dict, Any
from django.utils import timezone

from .base import TextToSpeechInterface
from .config import VoiceServiceConfig, require_valid_config
from .cache import tts_cache
from .exceptions import (
    TTSError, TTSQuotaExceededError, TTSServiceUnavailableError,
    TextValidationError, APITimeoutError, APIAuthenticationError,
    MissingAPIKeyError, handle_api_errors
)

logger = logging.getLogger(__name__)


class TextToSpeechService(TextToSpeechInterface):
    """
    Google Cloud Text-to-Speech服务实现 (Google Cloud Text-to-Speech service implementation)
    """
    
    def __init__(self):
        super().__init__()
        self.api_key = VoiceServiceConfig.GOOGLE_API_KEY
        self.api_url = VoiceServiceConfig.get_google_tts_url()
        self.timeout = VoiceServiceConfig.TTS_GENERATION_TIMEOUT
        self.cache_service = tts_cache
        
        if not self.api_key:
            raise MissingAPIKeyError("Google TTS")
    
    def validate_input(self, input_data: Any) -> bool:
        """
        验证输入数据 (Validate input data)
        
        Args:
            input_data: 输入数据，应该是包含text的字典 (Input data, should be dict containing text)
            
        Returns:
            bool: 验证结果 (Validation result)
        """
        if not isinstance(input_data, dict):
            return False
        
        text = input_data.get('text', '')
        return self.validate_text_length(text)
    
    def validate_text_length(self, text: str) -> bool:
        """
        验证文本长度是否适合TTS (Validate text length for TTS)
        
        Args:
            text: 要验证的文本 (Text to validate)
            
        Returns:
            bool: 验证结果 (Validation result)
        """
        if not text or not isinstance(text, str):
            return False
        
        # 检查文本长度 (Check text length)
        if len(text.strip()) == 0:
            return False
        
        if len(text) > VoiceServiceConfig.TTS_MAX_TEXT_LENGTH:
            return False
        
        return True
    
    @require_valid_config('GOOGLE_API_KEY')
    @handle_api_errors("Google TTS")
    def generate_speech(self, text: str, language_code: str = 'cmn-CN') -> str:
        """
        生成语音音频 (Generate speech audio)
        
        Args:
            text: 要转换的文本 (Text to convert)
            language_code: 语言代码 (Language code)
            
        Returns:
            str: Base64编码的音频数据 (Base64 encoded audio data)
        """
        # 验证文本 (Validate text)
        if not self.validate_text_length(text):
            raise TextValidationError(f"Invalid text for TTS: length={len(text)}")
        
        # 检查缓存 (Check cache)
        voice_name = self._get_voice_name(language_code)
        cached_audio = self.cache_service.get_cached_audio(text, language_code, voice_name)
        if cached_audio:
            logger.info(f"TTS cache hit for text length: {len(text)}")
            return cached_audio
        
        # 调用Google TTS API (Call Google TTS API)
        try:
            audio_data = self._call_google_tts_api(text, language_code, voice_name)
            
            # 缓存结果 (Cache result)
            self.cache_service.cache_audio(text, language_code, audio_data, voice_name)
            
            logger.info(f"TTS generated successfully for text length: {len(text)}")
            return audio_data
            
        except Exception as e:
            logger.error(f"TTS generation failed: {str(e)}")
            raise
    
    def _get_voice_name(self, language_code: str) -> str:
        """
        根据语言代码获取语音名称 (Get voice name based on language code)
        
        Args:
            language_code: 语言代码 (Language code)
            
        Returns:
            str: 语音名称 (Voice name)
        """
        voice_mapping = {
            'cmn-CN': 'cmn-CN-Standard-A',  # 中文女声 (Chinese female voice)
            'en-US': 'en-US-Standard-C',    # 英文女声 (English female voice)
            'en-AU': 'en-AU-Standard-A',    # 澳洲英语女声 (Australian English female voice)
        }
        
        return voice_mapping.get(language_code, VoiceServiceConfig.TTS_VOICE_NAME)
    
    def _call_google_tts_api(self, text: str, language_code: str, voice_name: str) -> str:
        """
        调用Google TTS API (Call Google TTS API)
        
        Args:
            text: 要转换的文本 (Text to convert)
            language_code: 语言代码 (Language code)
            voice_name: 语音名称 (Voice name)
            
        Returns:
            str: Base64编码的音频数据 (Base64 encoded audio data)
        """
        # 构建请求数据 (Build request data)
        request_data = {
            'input': {'text': text},
            'voice': {
                'languageCode': language_code,
                'name': voice_name
            },
            'audioConfig': {
                'audioEncoding': 'MP3',
                'speakingRate': 1.0,
                'pitch': 0.0,
                'volumeGainDb': 0.0
            }
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Referer': 'https://afterclass.tongcove.com/',
        }
        
        try:
            # 发送API请求 (Send API request)
            response = requests.post(
                self.api_url,
                headers=headers,
                json=request_data,
                timeout=self.timeout
            )
            
            # 处理响应 (Handle response)
            if response.status_code == 200:
                response_data = response.json()
                audio_content = response_data.get('audioContent')
                
                if not audio_content:
                    raise TTSError("No audio content in API response")
                
                return audio_content
            
            elif response.status_code == 401:
                raise APIAuthenticationError("Google TTS")
            
            elif response.status_code == 429:
                raise TTSQuotaExceededError("Google TTS API quota exceeded")
            
            elif response.status_code >= 500:
                raise TTSServiceUnavailableError(f"Google TTS service error: {response.status_code}")
            
            else:
                error_message = f"Google TTS API error: {response.status_code}"
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_message += f" - {error_data['error'].get('message', '')}"
                except:
                    pass
                
                raise TTSError(error_message)
        
        except requests.exceptions.Timeout:
            raise APITimeoutError("Google TTS")
        
        except requests.exceptions.RequestException as e:
            raise TTSServiceUnavailableError(f"Google TTS request failed: {str(e)}")
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理输入数据 (Process input data)
        
        Args:
            input_data: 输入数据，包含text和可选的language_code (Input data containing text and optional language_code)
            
        Returns:
            Dict[str, Any]: 处理结果 (Processing result)
        """
        if not self.validate_input(input_data):
            raise TextValidationError("Invalid input data for TTS")
        
        text = input_data['text']
        language_code = input_data.get('language_code', VoiceServiceConfig.TTS_DEFAULT_LANGUAGE)
        
        try:
            audio_data = self.generate_speech(text, language_code)
            
            return {
                'success': True,
                'audio_data': audio_data,
                'text': text,
                'language_code': language_code,
                'timestamp': timezone.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"TTS processing failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_code': getattr(e, 'error_code', 'tts_error'),
                'text': text,
                'timestamp': timezone.now().isoformat()
            }
    
    def get_supported_languages(self) -> Dict[str, str]:
        """
        获取支持的语言列表 (Get supported languages list)
        
        Returns:
            Dict[str, str]: 语言代码到语言名称的映射 (Language code to language name mapping)
        """
        return {
            'cmn-CN': '中文 (普通话)',
            'en-US': 'English (US)',
            'en-AU': 'English (Australian)',
            'en-GB': 'English (British)'
        }
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        获取服务状态信息 (Get service status information)
        
        Returns:
            Dict[str, Any]: 服务状态信息 (Service status information)
        """
        try:
            # 测试API连接 (Test API connection)
            test_result = self.generate_speech("测试", "cmn-CN")
            api_status = "healthy"
        except Exception as e:
            api_status = f"error: {str(e)}"
        
        return {
            'service_name': 'Google Text-to-Speech',
            'api_status': api_status,
            'api_url': self.api_url,
            'timeout': self.timeout,
            'cache_enabled': True,
            'cache_timeout': self.cache_service.cache_timeout,
            'supported_languages': list(self.get_supported_languages().keys()),
            'max_text_length': VoiceServiceConfig.TTS_MAX_TEXT_LENGTH
        }


# 全局TTS服务实例 (Global TTS service instance)
tts_service = TextToSpeechService()


def generate_tts_audio(text: str, language_code: str = 'cmn-CN') -> Optional[str]:
    """
    便捷函数：生成TTS音频 (Convenience function: generate TTS audio)
    
    Args:
        text: 要转换的文本 (Text to convert)
        language_code: 语言代码 (Language code)
        
    Returns:
        Optional[str]: Base64编码的音频数据，失败时返回None (Base64 encoded audio data, None on failure)
    """
    try:
        return tts_service.generate_speech(text, language_code)
    except Exception as e:
        logger.error(f"TTS generation failed: {str(e)}")
        return None


def is_tts_available() -> bool:
    """
    检查TTS服务是否可用 (Check if TTS service is available)
    
    Returns:
        bool: TTS服务是否可用 (Whether TTS service is available)
    """
    try:
        status = tts_service.get_service_status()
        return status['api_status'] == 'healthy'
    except Exception:
        return False