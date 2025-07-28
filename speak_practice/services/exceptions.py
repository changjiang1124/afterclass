"""
语音处理服务异常类定义 (Voice Processing Service Exception Classes)
"""


class VoiceServiceError(Exception):
    """语音服务基础异常类 (Base voice service exception class)"""
    
    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or 'voice_service_error'


class AudioValidationError(VoiceServiceError):
    """音频文件验证异常 (Audio file validation exception)"""
    
    def __init__(self, message: str):
        super().__init__(message, 'audio_validation_error')


class SpeechRecognitionError(VoiceServiceError):
    """语音识别异常 (Speech recognition exception)"""
    
    def __init__(self, message: str, error_code: str = 'speech_recognition_error'):
        super().__init__(message, error_code)


class TranscriptionTimeoutError(SpeechRecognitionError):
    """语音识别超时异常 (Speech recognition timeout exception)"""
    
    def __init__(self, message: str = "Speech recognition timeout"):
        super().__init__(message, 'transcription_timeout')


class AudioFormatError(SpeechRecognitionError):
    """音频格式错误异常 (Audio format error exception)"""
    
    def __init__(self, message: str):
        super().__init__(message, 'audio_format_error')


class TTSError(VoiceServiceError):
    """文本转语音异常 (Text-to-speech exception)"""
    
    def __init__(self, message: str, error_code: str = 'tts_error'):
        super().__init__(message, error_code)


class TTSQuotaExceededError(TTSError):
    """TTS配额超限异常 (TTS quota exceeded exception)"""
    
    def __init__(self, message: str = "TTS quota exceeded"):
        super().__init__(message, 'tts_quota_exceeded')


class TTSServiceUnavailableError(TTSError):
    """TTS服务不可用异常 (TTS service unavailable exception)"""
    
    def __init__(self, message: str = "TTS service unavailable"):
        super().__init__(message, 'tts_service_unavailable')


class TextValidationError(TTSError):
    """文本验证异常 (Text validation exception)"""
    
    def __init__(self, message: str):
        super().__init__(message, 'text_validation_error')


class TranslationError(VoiceServiceError):
    """翻译服务异常 (Translation service exception)"""
    
    def __init__(self, message: str, error_code: str = 'translation_error'):
        super().__init__(message, error_code)


class TranslationTimeoutError(TranslationError):
    """翻译超时异常 (Translation timeout exception)"""
    
    def __init__(self, message: str = "Translation timeout"):
        super().__init__(message, 'translation_timeout')


class UnsupportedLanguageError(TranslationError):
    """不支持的语言异常 (Unsupported language exception)"""
    
    def __init__(self, language: str):
        message = f"Unsupported language: {language}"
        super().__init__(message, 'unsupported_language')


class CacheError(VoiceServiceError):
    """缓存服务异常 (Cache service exception)"""
    
    def __init__(self, message: str, error_code: str = 'cache_error'):
        super().__init__(message, error_code)


class CacheConnectionError(CacheError):
    """缓存连接异常 (Cache connection exception)"""
    
    def __init__(self, message: str = "Cache connection failed"):
        super().__init__(message, 'cache_connection_error')


class APIError(VoiceServiceError):
    """API调用异常 (API call exception)"""
    
    def __init__(self, message: str, status_code: int = None, error_code: str = 'api_error'):
        super().__init__(message, error_code)
        self.status_code = status_code


class APITimeoutError(APIError):
    """API超时异常 (API timeout exception)"""
    
    def __init__(self, service_name: str):
        message = f"{service_name} API timeout"
        super().__init__(message, error_code='api_timeout')


class APIQuotaExceededError(APIError):
    """API配额超限异常 (API quota exceeded exception)"""
    
    def __init__(self, service_name: str):
        message = f"{service_name} API quota exceeded"
        super().__init__(message, status_code=429, error_code='api_quota_exceeded')


class APIAuthenticationError(APIError):
    """API认证异常 (API authentication exception)"""
    
    def __init__(self, service_name: str):
        message = f"{service_name} API authentication failed"
        super().__init__(message, status_code=401, error_code='api_authentication_error')


class ConfigurationError(VoiceServiceError):
    """配置错误异常 (Configuration error exception)"""
    
    def __init__(self, message: str):
        super().__init__(message, 'configuration_error')


class MissingAPIKeyError(ConfigurationError):
    """API密钥缺失异常 (Missing API key exception)"""
    
    def __init__(self, service_name: str):
        message = f"Missing API key for {service_name}"
        super().__init__(message)


# 异常处理装饰器 (Exception handling decorators)
def handle_voice_service_errors(func):
    """
    语音服务异常处理装饰器 (Voice service exception handling decorator)
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except VoiceServiceError:
            # 重新抛出已知的语音服务异常 (Re-raise known voice service exceptions)
            raise
        except Exception as e:
            # 将未知异常包装为语音服务异常 (Wrap unknown exceptions as voice service exceptions)
            raise VoiceServiceError(f"Unexpected error: {str(e)}")
    return wrapper


def handle_api_errors(service_name: str):
    """
    API错误处理装饰器工厂 (API error handling decorator factory)
    
    Args:
        service_name: 服务名称 (Service name)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except APIError:
                # 重新抛出已知的API异常 (Re-raise known API exceptions)
                raise
            except Exception as e:
                # 将未知异常包装为API异常 (Wrap unknown exceptions as API exceptions)
                raise APIError(f"{service_name} API error: {str(e)}")
        return wrapper
    return decorator