# 语音处理服务模块 (Voice Processing Services Module)

from .base import (
    BaseVoiceService,
    SpeechRecognitionInterface,
    TextToSpeechInterface,
    TranslationInterface,
    CacheInterface
)

from .exceptions import (
    VoiceServiceError,
    AudioValidationError,
    SpeechRecognitionError,
    TranscriptionTimeoutError,
    AudioFormatError,
    TTSError,
    TTSQuotaExceededError,
    TTSServiceUnavailableError,
    TextValidationError,
    TranslationError,
    TranslationTimeoutError,
    UnsupportedLanguageError,
    CacheError,
    CacheConnectionError,
    APIError,
    APITimeoutError,
    APIQuotaExceededError,
    APIAuthenticationError,
    ConfigurationError,
    MissingAPIKeyError
)

from .config import VoiceServiceConfig, require_valid_config

from .utils import (
    validate_audio_file,
    generate_cache_key,
    encode_audio_to_base64,
    decode_base64_audio,
    validate_text_for_tts,
    sanitize_text_for_processing,
    format_api_error_response,
    get_supported_languages,
    calculate_audio_duration
)

from .cache import (
    TTSCacheService,
    TranslationCacheService,
    tts_cache,
    translation_cache
)

__all__ = [
    # Base interfaces
    'BaseVoiceService',
    'SpeechRecognitionInterface', 
    'TextToSpeechInterface',
    'TranslationInterface',
    'CacheInterface',
    
    # Exceptions
    'VoiceServiceError',
    'AudioValidationError',
    'SpeechRecognitionError',
    'TranscriptionTimeoutError',
    'AudioFormatError',
    'TTSError',
    'TTSQuotaExceededError',
    'TTSServiceUnavailableError',
    'TextValidationError',
    'TranslationError',
    'TranslationTimeoutError',
    'UnsupportedLanguageError',
    'CacheError',
    'CacheConnectionError',
    'APIError',
    'APITimeoutError',
    'APIQuotaExceededError',
    'APIAuthenticationError',
    'ConfigurationError',
    'MissingAPIKeyError',
    
    # Configuration
    'VoiceServiceConfig',
    'require_valid_config',
    
    # Utilities
    'validate_audio_file',
    'generate_cache_key',
    'encode_audio_to_base64',
    'decode_base64_audio',
    'validate_text_for_tts',
    'sanitize_text_for_processing',
    'format_api_error_response',
    'get_supported_languages',
    'calculate_audio_duration',
    
    # Cache services
    'TTSCacheService',
    'TranslationCacheService',
    'tts_cache',
    'translation_cache'
]