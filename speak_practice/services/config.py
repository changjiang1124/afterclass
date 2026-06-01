"""
语音处理服务配置管理 (Voice Processing Services Configuration Management)
"""

import os
from functools import wraps
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
    def validate_configuration(cls, required_keys=None) -> dict:
        """
        验证配置完整性 (Validate configuration completeness)

        Args:
            required_keys: 需要校验的 API key 名称列表（如 ['OPENAI_API_KEY']）。
                           None 表示校验全部 key（向后兼容）。各服务应只传入自己真正需要的 key，
                           避免缺少不相关的 key（如纯 OpenAI 服务被缺失的 GOOGLE_API_KEY 拖垮）。
                           (List of key names to require; None = all, for back-compat.)

        Returns:
            dict: 验证结果 (Validation results)
        """
        if required_keys is None:
            required_keys = ['OPENAI_API_KEY', 'GOOGLE_API_KEY']

        validation_results = {
            'valid': True,
            'missing_keys': [],
            'warnings': []
        }

        # 仅检查本次调用真正需要的 API 密钥 (Check only the keys actually required)
        for key_name in required_keys:
            if not getattr(cls, key_name, None):
                validation_results['valid'] = False
                validation_results['missing_keys'].append(key_name)

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
def require_valid_config(*required_keys):
    """
    装饰器：确保所需 API key 已配置才执行函数。
    (Decorator: ensure the required API keys are configured before running.)

    用法 (Usage):
        @require_valid_config('OPENAI_API_KEY')   # 只需要 OpenAI（翻译 / 语音识别）
        @require_valid_config('GOOGLE_API_KEY')   # 只需要 Google（TTS）
        @require_valid_config                      # 不带参数 → 校验全部 key（向后兼容）
    """
    # 裸用法 @require_valid_config：此时唯一的位置参数就是被装饰的函数
    # (Bare usage: the single positional arg is the decorated function.)
    if len(required_keys) == 1 and callable(required_keys[0]):
        return _make_config_guard(required_keys[0], None)

    keys = list(required_keys) or None

    def decorator(func):
        return _make_config_guard(func, keys)
    return decorator


def _make_config_guard(func, required_keys):
    @wraps(func)
    def wrapper(*args, **kwargs):
        validation = VoiceServiceConfig.validate_configuration(required_keys)
        if not validation['valid']:
            raise ValueError(f"Invalid configuration. Missing keys: {validation['missing_keys']}")
        return func(*args, **kwargs)
    return wrapper