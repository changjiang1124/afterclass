"""
语音处理服务工具函数 (Voice Processing Service Utility Functions)
"""

import hashlib
import base64
import mimetypes
from typing import Optional, Dict, Any
from django.core.files.uploadedfile import UploadedFile
from .config import VoiceServiceConfig
from .exceptions import AudioValidationError


def validate_audio_file(audio_file: UploadedFile) -> bool:
    """
    验证音频文件格式和大小 (Validate audio file format and size)
    
    Args:
        audio_file: Django上传文件对象 (Django uploaded file object)
        
    Returns:
        bool: 验证结果 (Validation result)
        
    Raises:
        AudioValidationError: 音频验证失败 (Audio validation failed)
    """
    # 检查文件大小 (Check file size)
    if audio_file.size > VoiceServiceConfig.AUDIO_UPLOAD_MAX_SIZE:
        raise AudioValidationError(
            f"Audio file too large. Maximum size: {VoiceServiceConfig.AUDIO_UPLOAD_MAX_SIZE} bytes"
        )
    
    # 检查文件类型 (Check file type)
    content_type = audio_file.content_type
    if content_type not in VoiceServiceConfig.AUDIO_ALLOWED_FORMATS:
        raise AudioValidationError(
            f"Unsupported audio format: {content_type}. "
            f"Allowed formats: {', '.join(VoiceServiceConfig.AUDIO_ALLOWED_FORMATS)}"
        )
    
    # 检查文件名扩展名 (Check file extension)
    if audio_file.name:
        mime_type, _ = mimetypes.guess_type(audio_file.name)
        if mime_type and mime_type not in VoiceServiceConfig.AUDIO_ALLOWED_FORMATS:
            raise AudioValidationError(f"File extension doesn't match content type")
    
    return True


def generate_cache_key(content: str, service_type: str, **kwargs) -> str:
    """
    生成缓存键 (Generate cache key)
    
    Args:
        content: 内容字符串 (Content string)
        service_type: 服务类型 (Service type)
        **kwargs: 额外参数 (Additional parameters)
        
    Returns:
        str: 缓存键 (Cache key)
    """
    # 创建内容哈希 (Create content hash)
    content_with_params = f"{content}:{':'.join(f'{k}={v}' for k, v in sorted(kwargs.items()))}"
    content_hash = hashlib.md5(content_with_params.encode('utf-8')).hexdigest()
    
    # 返回带前缀的缓存键 (Return cache key with prefix)
    prefix = VoiceServiceConfig.get_cache_key_prefix()
    return f"{prefix}{service_type}:{content_hash}"


def encode_audio_to_base64(audio_data: bytes) -> str:
    """
    将音频数据编码为Base64 (Encode audio data to Base64)
    
    Args:
        audio_data: 音频字节数据 (Audio byte data)
        
    Returns:
        str: Base64编码的音频数据 (Base64 encoded audio data)
    """
    return base64.b64encode(audio_data).decode('utf-8')


def decode_base64_audio(base64_data: str) -> bytes:
    """
    将Base64数据解码为音频字节 (Decode Base64 data to audio bytes)
    
    Args:
        base64_data: Base64编码的音频数据 (Base64 encoded audio data)
        
    Returns:
        bytes: 音频字节数据 (Audio byte data)
    """
    return base64.b64decode(base64_data)


def validate_text_for_tts(text: str) -> bool:
    """
    验证文本是否适合TTS处理 (Validate text for TTS processing)
    
    Args:
        text: 要验证的文本 (Text to validate)
        
    Returns:
        bool: 验证结果 (Validation result)
        
    Raises:
        ValueError: 文本验证失败 (Text validation failed)
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")
    
    if len(text) > VoiceServiceConfig.TTS_MAX_TEXT_LENGTH:
        raise ValueError(
            f"Text too long. Maximum length: {VoiceServiceConfig.TTS_MAX_TEXT_LENGTH} characters"
        )
    
    return True


def sanitize_text_for_processing(text: str) -> str:
    """
    清理文本用于处理 (Sanitize text for processing)
    
    Args:
        text: 原始文本 (Raw text)
        
    Returns:
        str: 清理后的文本 (Sanitized text)
    """
    # 移除多余的空白字符 (Remove excessive whitespace)
    text = ' '.join(text.split())
    
    # 移除潜在的危险字符 (Remove potentially dangerous characters)
    dangerous_chars = ['<', '>', '"', "'", '&']
    for char in dangerous_chars:
        text = text.replace(char, '')
    
    return text.strip()


def format_api_error_response(error: Exception, error_code: str) -> Dict[str, Any]:
    """
    格式化API错误响应 (Format API error response)
    
    Args:
        error: 异常对象 (Exception object)
        error_code: 错误代码 (Error code)
        
    Returns:
        dict: 格式化的错误响应 (Formatted error response)
    """
    return {
        'success': False,
        'error': str(error),
        'error_code': error_code,
        'timestamp': None  # 将在视图中设置 (Will be set in view)
    }


def get_supported_languages() -> Dict[str, str]:
    """
    获取支持的语言列表 (Get supported languages list)
    
    Returns:
        dict: 语言代码到语言名称的映射 (Language code to language name mapping)
    """
    return {
        'en': 'English',
        'zh': '中文',
        'cmn-CN': '中文 (普通话)',
        'en-AU': 'English (Australian)',
        'en-US': 'English (American)'
    }


def calculate_audio_duration(audio_file: UploadedFile) -> Optional[float]:
    """
    计算音频文件时长 (Calculate audio file duration)
    
    Args:
        audio_file: 音频文件 (Audio file)
        
    Returns:
        Optional[float]: 音频时长（秒），如果无法计算则返回None (Audio duration in seconds, None if cannot calculate)
    """
    # 这里可以集成音频处理库来计算实际时长 (Audio processing library can be integrated here for actual duration calculation)
    # 目前返回估算值 (Currently returns estimated value)
    try:
        # 基于文件大小的粗略估算 (Rough estimation based on file size)
        # 假设平均比特率为128kbps (Assuming average bitrate of 128kbps)
        estimated_duration = audio_file.size / (128 * 1024 / 8)  # 转换为秒 (Convert to seconds)
        return min(estimated_duration, VoiceServiceConfig.AUDIO_MAX_DURATION)
    except:
        return None