"""
语音处理服务配置管理 (Voice Processing Services Configuration Management)
"""

import os
from django.conf import settings
from typing import Optional

# 确保环境变量已加载 (Ensure environment variables are loaded)
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass


class VoiceServiceConfig:
    """语音服务配置类 (Voice service configuration class)"""
    
    # OpenAI配置 (OpenAI Configuration)
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') or getattr(settings, 'OPENAI_API_KEY', None)
    OPENAI_WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"
    OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
    
    # Google TTS配置 (Google TTS Configuration)
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY') or getattr(settings, 'GOOGLE_API_KEY', None)
    GOOGLE_TTS_URL = f"https://texttospeech.googleapis.com/v1/text:synthesize"
    
    # 音频文件配置 (Audio File Configuration)
    AUDIO_UPLOAD_MAX_SIZE = int(os.getenv('AUDIO_UPLOAD_MAX_SIZE', '10485760'))  # 10MB
    AUDIO_ALLOWED_FORMATS = ['audio/wav', 'audio/mp3', 'audio/webm', 'audio/ogg', 'audio/m4a']
    AUDIO_MAX_DURATION = int(os.getenv('AUDIO_MAX_DURATION', '300'))  # 5分钟 (5 minutes)
    
    # TTS配置 (TTS Configuration)
    TTS_CACHE_TIMEOUT = int(os.getenv('TTS_CACHE_TIMEOUT', '86400'))  # 24小时 (24 hours)
    TTS_MAX_TEXT_LENGTH = int(os.getenv('TTS_MAX_TEXT_LENGTH', '5000'))  # 最大文本长度 (Max text length)
    TTS_DEFAULT_LANGUAGE = 'cmn-CN'  # 默认中文 (Default Chinese)
    TTS_VOICE_NAME = 'cmn-CN-Standard-A'  # 默认语音 (Default voice)
    
    # API超时配置 (API Timeout Configuration)
    SPEECH_RECOGNITION_TIMEOUT = int(os.getenv('SPEECH_RECOGNITION_TIMEOUT', '30'))
    TTS_GENERATION_TIMEOUT = int(os.getenv('TTS_GENERATION_TIMEOUT', '30'))
    TRANSLATION_TIMEOUT = int(os.getenv('TRANSLATION_TIMEOUT', '15'))
    
    # 速率限制配置 (Rate Limiting Configuration)
    API_RATE_LIMIT_PER_MINUTE = int(os.getenv('API_RATE_LIMIT_PER_MINUTE', '60'))
    API_RATE_LIMIT_PER_HOUR = int(os.getenv('API_RATE_LIMIT_PER_HOUR', '1000'))
    
    @classmethod
    def validate_configuration(cls) -> dict:
        """
        验证配置完整性 (Validate configuration completeness)
        
        Returns:
            dict: 验证结果 (Validation results)
        """
        validation_results = {
            'valid': True,
            'missing_keys': [],
            'warnings': []
        }
        
        # 检查必需的API密钥 (Check required API keys)
        if not cls.OPENAI_API_KEY:
            validation_results['valid'] = False
            validation_results['missing_keys'].append('OPENAI_API_KEY')
        
        if not cls.GOOGLE_API_KEY:
            validation_results['valid'] = False
            validation_results['missing_keys'].append('GOOGLE_API_KEY')
        
        # 检查配置值的合理性 (Check configuration value reasonableness)
        if cls.AUDIO_UPLOAD_MAX_SIZE > 50 * 1024 * 1024:  # 50MB
            validation_results['warnings'].append('AUDIO_UPLOAD_MAX_SIZE is very large (>50MB)')
        
        if cls.TTS_MAX_TEXT_LENGTH > 10000:
            validation_results['warnings'].append('TTS_MAX_TEXT_LENGTH is very large (>10000 chars)')
        
        return validation_results
    
    @classmethod
    def get_openai_headers(cls) -> dict:
        """获取OpenAI API请求头 (Get OpenAI API headers)"""
        return {
            'Authorization': f'Bearer {cls.OPENAI_API_KEY}',
            'Content-Type': 'application/json'
        }
    
    @classmethod
    def get_google_tts_url(cls) -> str:
        """获取Google TTS API URL (Get Google TTS API URL)"""
        return f"{cls.GOOGLE_TTS_URL}?key={cls.GOOGLE_API_KEY}"
    
    @classmethod
    def is_development(cls) -> bool:
        """检查是否为开发环境 (Check if development environment)"""
        return getattr(settings, 'DEBUG', False)
    
    @classmethod
    def get_cache_key_prefix(cls) -> str:
        """获取缓存键前缀 (Get cache key prefix)"""
        return 'speak_practice_voice_'


# 配置验证装饰器 (Configuration validation decorator)
def require_valid_config(func):
    """
    装饰器：确保配置有效才执行函数 (Decorator: ensure valid configuration before function execution)
    """
    def wrapper(*args, **kwargs):
        validation = VoiceServiceConfig.validate_configuration()
        if not validation['valid']:
            raise ValueError(f"Invalid configuration. Missing keys: {validation['missing_keys']}")
        return func(*args, **kwargs)
    return wrapper