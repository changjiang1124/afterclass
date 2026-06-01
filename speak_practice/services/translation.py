"""
翻译服务实现 (Translation Service Implementation)
"""

import requests
import logging
from typing import Dict, Any

from .base import TranslationInterface
from .config import VoiceServiceConfig, require_valid_config
from .exceptions import (
    TranslationError,
    TranslationTimeoutError,
    UnsupportedLanguageError,
    APIError,
    APITimeoutError,
    APIAuthenticationError,
    MissingAPIKeyError,
    handle_voice_service_errors
)

# 配置日志记录 (Configure logging)
logger = logging.getLogger('speak_practice.translation')


class TranslationService(TranslationInterface):
    """
    翻译服务类，使用OpenAI GPT-4进行翻译
    (Translation service class using OpenAI GPT-4 for translation)
    """
    
    def __init__(self):
        super().__init__()
        self.api_key = VoiceServiceConfig.OPENAI_API_KEY
        self.api_url = VoiceServiceConfig.OPENAI_CHAT_URL
        self.timeout = VoiceServiceConfig.TRANSLATION_TIMEOUT
        
        # 验证API密钥 (Validate API key)
        if not self.api_key:
            raise MissingAPIKeyError("OpenAI")
        
        # 支持的语言映射 (Supported language mapping)
        self.supported_languages = {
            'zh': 'Chinese (Simplified)',
            'en': 'English',
            'zh-cn': 'Chinese (Simplified)',
            'zh-tw': 'Chinese (Traditional)',
            'cmn': 'Chinese (Mandarin)'
        }
    
    @require_valid_config('OPENAI_API_KEY')
    @handle_voice_service_errors
    def validate_input(self, input_data: Any) -> bool:
        """
        验证输入数据 (Validate input data)
        
        Args:
            input_data: 要翻译的文本 (Text to translate)
            
        Returns:
            bool: 验证结果 (Validation result)
        """
        if not isinstance(input_data, str):
            return False
        
        # 检查文本长度 (Check text length)
        if len(input_data.strip()) == 0:
            return False
        
        if len(input_data) > VoiceServiceConfig.TTS_MAX_TEXT_LENGTH:
            return False
        
        return True
    
    @require_valid_config('OPENAI_API_KEY')
    @handle_voice_service_errors
    def process(self, input_data: Any) -> Dict[str, Any]:
        """
        处理输入数据 (Process input data)
        
        Args:
            input_data: 包含翻译参数的字典 (Dictionary containing translation parameters)
            
        Returns:
            Dict[str, Any]: 处理结果 (Processing result)
        """
        if not isinstance(input_data, dict):
            raise TranslationError("Input data must be a dictionary")
        
        text = input_data.get('text', '')
        source_lang = input_data.get('source_lang', 'en')
        target_lang = input_data.get('target_lang', 'zh')
        
        if not self.validate_input(text):
            raise TranslationError("Invalid input text")
        
        translated_text = self.translate_text(text, source_lang, target_lang)
        
        return {
            'translated_text': translated_text,
            'source_language': source_lang,
            'target_language': target_lang,
            'original_text': text,
            'character_count': len(translated_text)
        }
    
    @handle_voice_service_errors
    def translate_text(self, text: str, source_lang: str = 'en', target_lang: str = 'zh') -> str:
        """
        使用OpenAI GPT-4翻译文本
        (Translate text using OpenAI GPT-4)
        
        Args:
            text: 要翻译的文本 (Text to translate)
            source_lang: 源语言代码 (Source language code)
            target_lang: 目标语言代码 (Target language code)
            
        Returns:
            str: 翻译后的文本 (Translated text)
            
        Raises:
            TranslationError: 翻译失败 (Translation failed)
            TranslationTimeoutError: 翻译超时 (Translation timeout)
            UnsupportedLanguageError: 不支持的语言 (Unsupported language)
        """
        # 验证语言支持 (Validate language support)
        if source_lang not in self.supported_languages:
            raise UnsupportedLanguageError(source_lang)
        
        if target_lang not in self.supported_languages:
            raise UnsupportedLanguageError(target_lang)
        
        # 验证文本 (Validate text)
        if not text or not text.strip():
            raise TranslationError("Empty text provided")
        
        if len(text) > VoiceServiceConfig.TTS_MAX_TEXT_LENGTH:
            raise TranslationError(f"Text too long. Maximum length: {VoiceServiceConfig.TTS_MAX_TEXT_LENGTH}")
        
        # 生成翻译提示词 (Generate translation prompt)
        translation_prompt = self.get_translation_prompt(text, target_lang)
        
        # 准备API请求 (Prepare API request)
        headers = VoiceServiceConfig.get_openai_headers()
        
        messages = [
            {"role": "system", "content": translation_prompt},
            {"role": "user", "content": text}
        ]
        
        payload = {
            "model": "gpt-4o-mini",  # 使用4o-mini优化成本 (Use 4o-mini for cost optimization)
            "messages": messages,
            "temperature": 0.3,  # 较低的温度以获得更一致的翻译 (Lower temperature for consistent translation)
            "max_tokens": 1000
        }
        
        try:
            logger.info(f"Starting translation: {source_lang} -> {target_lang}, length: {len(text)}")
            
            # 发送API请求 (Send API request)
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            # 处理API响应 (Handle API response)
            if response.status_code == 200:
                response_data = response.json()
                translated_text = response_data['choices'][0]['message']['content'].strip()
                
                if not translated_text:
                    raise TranslationError("Empty translation result")
                
                logger.info(f"Translation successful: {len(translated_text)} characters")
                return translated_text
                
            elif response.status_code == 401:
                logger.error("OpenAI API authentication failed")
                raise APIAuthenticationError("OpenAI")
                
            elif response.status_code == 429:
                logger.error("OpenAI API rate limit exceeded")
                raise APIError("Rate limit exceeded", status_code=429, error_code='api_rate_limit')
                
            else:
                error_message = f"API request failed with status {response.status_code}"
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_message += f": {error_data['error'].get('message', 'Unknown error')}"
                except:
                    error_message += f": {response.text}"
                
                logger.error(f"Translation API error: {error_message}")
                raise TranslationError(error_message)
                
        except requests.exceptions.Timeout:
            logger.error(f"Translation timeout after {self.timeout} seconds")
            raise TranslationTimeoutError()
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error during translation: {e}")
            raise TranslationError(f"Connection error: {str(e)}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error during translation: {e}")
            raise TranslationError(f"Request error: {str(e)}")
    
    def get_translation_prompt(self, text: str, target_lang: str) -> str:
        """
        生成翻译提示词 (Generate translation prompt)
        
        Args:
            text: 要翻译的文本 (Text to translate)
            target_lang: 目标语言 (Target language)
            
        Returns:
            str: 翻译提示词 (Translation prompt)
        """
        language_names = {
            'zh': 'Simplified Chinese',
            'en': 'English',
            'zh-cn': 'Simplified Chinese',
            'zh-tw': 'Traditional Chinese',
            'cmn': 'Mandarin Chinese'
        }
        
        target_language_name = language_names.get(target_lang, target_lang)
        
        if target_lang in ['zh', 'zh-cn', 'cmn']:
            return f"""You are a professional translator specializing in Chinese language learning materials.

Translate the following text to {target_language_name}. Follow these guidelines:

1. Provide natural, conversational translations appropriate for Chinese language learners
2. Use simplified Chinese characters
3. Maintain the original tone and context
4. For casual conversations, use appropriate colloquial expressions
5. For formal content, maintain appropriate formality level
6. Only return the translated text, no explanations or additional content

The text to translate is:"""
        
        else:
            return f"""You are a professional translator.

Translate the following Chinese text to {target_language_name}. Follow these guidelines:

1. Provide accurate, natural translations
2. Maintain the original meaning and context
3. Use appropriate formality level
4. Only return the translated text, no explanations or additional content

The Chinese text to translate is:"""
    
    def get_supported_languages(self) -> Dict[str, str]:
        """
        获取支持的语言列表 (Get list of supported languages)
        
        Returns:
            Dict[str, str]: 支持的语言映射 (Supported language mapping)
        """
        return self.supported_languages.copy()
    
    def is_language_supported(self, language_code: str) -> bool:
        """
        检查语言是否支持 (Check if language is supported)
        
        Args:
            language_code: 语言代码 (Language code)
            
        Returns:
            bool: 是否支持 (Whether supported)
        """
        return language_code.lower() in self.supported_languages
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        获取服务状态信息 (Get service status information)
        
        Returns:
            Dict[str, Any]: 服务状态 (Service status)
        """
        return {
            'service_name': 'OpenAI GPT-4 Translation',
            'api_key_configured': bool(self.api_key),
            'api_url': self.api_url,
            'timeout': self.timeout,
            'supported_languages': self.get_supported_languages(),
            'max_text_length': VoiceServiceConfig.TTS_MAX_TEXT_LENGTH
        }