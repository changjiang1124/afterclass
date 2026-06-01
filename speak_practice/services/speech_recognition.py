"""
语音识别服务实现 (Speech Recognition Service Implementation)
"""

import os
import requests
import logging
from typing import Dict, Any
from django.core.files.uploadedfile import UploadedFile

from .base import SpeechRecognitionInterface
from .config import VoiceServiceConfig, require_valid_config
from .exceptions import (
    SpeechRecognitionError,
    AudioValidationError,
    TranscriptionTimeoutError,
    AudioFormatError,
    APIError,
    APITimeoutError,
    APIAuthenticationError,
    MissingAPIKeyError,
    handle_voice_service_errors
)

# 配置日志记录 (Configure logging)
logger = logging.getLogger('speak_practice.speech_recognition')


class SpeechRecognitionService(SpeechRecognitionInterface):
    """
    语音识别服务类，集成OpenAI Whisper API
    (Speech recognition service class integrating OpenAI Whisper API)
    """
    
    def __init__(self):
        super().__init__()
        self.api_key = VoiceServiceConfig.OPENAI_API_KEY
        self.whisper_url = VoiceServiceConfig.OPENAI_WHISPER_URL
        self.timeout = VoiceServiceConfig.SPEECH_RECOGNITION_TIMEOUT
        
        # 验证API密钥 (Validate API key)
        if not self.api_key:
            raise MissingAPIKeyError("OpenAI")
    
    @require_valid_config('OPENAI_API_KEY')
    @handle_voice_service_errors
    def validate_input(self, input_data: Any) -> bool:
        """
        验证输入数据 (Validate input data)
        
        Args:
            input_data: Django UploadedFile对象 (Django UploadedFile object)
            
        Returns:
            bool: 验证结果 (Validation result)
        """
        if not isinstance(input_data, UploadedFile):
            return False
        
        return self.validate_audio_file(input_data)
    
    @handle_voice_service_errors
    def validate_audio_file(self, audio_file: UploadedFile) -> bool:
        """
        验证音频文件格式和大小 (Validate audio file format and size)
        
        Args:
            audio_file: Django UploadedFile对象 (Django UploadedFile object)
            
        Returns:
            bool: 验证结果 (Validation result)
            
        Raises:
            AudioValidationError: 音频文件验证失败 (Audio file validation failed)
        """
        # 检查文件是否存在 (Check if file exists)
        if not audio_file:
            raise AudioValidationError("No audio file provided")
        
        # 检查文件大小 (Check file size)
        if audio_file.size > VoiceServiceConfig.AUDIO_UPLOAD_MAX_SIZE:
            max_size_mb = VoiceServiceConfig.AUDIO_UPLOAD_MAX_SIZE / (1024 * 1024)
            raise AudioValidationError(
                f"Audio file too large. Maximum size: {max_size_mb:.1f}MB"
            )
        
        # 检查文件格式 (Check file format)
        content_type = audio_file.content_type
        if content_type not in VoiceServiceConfig.AUDIO_ALLOWED_FORMATS:
            allowed_formats = ', '.join(VoiceServiceConfig.AUDIO_ALLOWED_FORMATS)
            raise AudioFormatError(
                f"Unsupported audio format: {content_type}. "
                f"Allowed formats: {allowed_formats}"
            )
        
        # 检查文件名扩展名 (Check file extension)
        if hasattr(audio_file, 'name') and audio_file.name:
            allowed_extensions = ['.wav', '.mp3', '.webm', '.ogg', '.m4a']
            file_extension = os.path.splitext(audio_file.name)[1].lower()
            if file_extension not in allowed_extensions:
                raise AudioFormatError(
                    f"Unsupported file extension: {file_extension}. "
                    f"Allowed extensions: {', '.join(allowed_extensions)}"
                )
        
        logger.info(f"Audio file validation passed: {audio_file.name}, "
                   f"size: {audio_file.size} bytes, type: {content_type}")
        
        return True
    
    @require_valid_config('OPENAI_API_KEY')
    @handle_voice_service_errors
    def process(self, input_data: Any) -> Dict[str, Any]:
        """
        处理输入数据 (Process input data)
        
        Args:
            input_data: Django UploadedFile对象 (Django UploadedFile object)
            
        Returns:
            Dict[str, Any]: 处理结果 (Processing result)
        """
        if not self.validate_input(input_data):
            raise AudioValidationError("Invalid input data")
        
        transcribed_text = self.transcribe_audio(input_data)
        
        return {
            'transcribed_text': transcribed_text,
            'audio_duration': self._estimate_audio_duration(input_data),
            'audio_size': input_data.size,
            'audio_format': input_data.content_type
        }
    
    @handle_voice_service_errors
    def transcribe_audio(self, audio_file: UploadedFile) -> str:
        """
        使用OpenAI Whisper API转录音频文件
        (Transcribe audio file using OpenAI Whisper API)
        
        Args:
            audio_file: Django UploadedFile对象 (Django UploadedFile object)
            
        Returns:
            str: 转录的中文文本 (Transcribed Chinese text)
            
        Raises:
            SpeechRecognitionError: 语音识别失败 (Speech recognition failed)
            TranscriptionTimeoutError: 转录超时 (Transcription timeout)
            APIAuthenticationError: API认证失败 (API authentication failed)
        """
        # 验证音频文件 (Validate audio file)
        self.validate_audio_file(audio_file)
        
        # 准备API请求 (Prepare API request)
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }
        
        # 准备文件数据 (Prepare file data)
        files = {
            'file': (audio_file.name or 'audio.webm', audio_file.read(), audio_file.content_type)
        }
        
        # 准备请求数据 (Prepare request data)
        data = {
            'model': 'whisper-1',
            'language': 'zh',  # 指定中文 (Specify Chinese)
            'response_format': 'text'
        }
        
        try:
            logger.info(f"Starting speech recognition for file: {audio_file.name}")
            
            # 发送API请求 (Send API request)
            response = requests.post(
                self.whisper_url,
                headers=headers,
                files=files,
                data=data,
                timeout=self.timeout
            )
            
            # 处理API响应 (Handle API response)
            if response.status_code == 200:
                transcribed_text = response.text.strip()
                
                if not transcribed_text:
                    raise SpeechRecognitionError("Empty transcription result")
                
                logger.info(f"Speech recognition successful: {len(transcribed_text)} characters")
                return transcribed_text
                
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
                
                logger.error(f"Speech recognition API error: {error_message}")
                raise SpeechRecognitionError(error_message)
                
        except requests.exceptions.Timeout:
            logger.error(f"Speech recognition timeout after {self.timeout} seconds")
            raise TranscriptionTimeoutError()
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error during speech recognition: {e}")
            raise SpeechRecognitionError(f"Connection error: {str(e)}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error during speech recognition: {e}")
            raise SpeechRecognitionError(f"Request error: {str(e)}")
            
        finally:
            # 重置文件指针 (Reset file pointer)
            if hasattr(audio_file, 'seek'):
                audio_file.seek(0)
    
    def _estimate_audio_duration(self, audio_file: UploadedFile) -> float:
        """
        估算音频时长 (Estimate audio duration)
        
        Args:
            audio_file: Django UploadedFile对象 (Django UploadedFile object)
            
        Returns:
            float: 估算的音频时长（秒） (Estimated audio duration in seconds)
        """
        # 简单的时长估算，基于文件大小 (Simple duration estimation based on file size)
        # 这是一个粗略的估算，实际项目中可能需要使用音频处理库
        # (This is a rough estimation, actual projects might need audio processing libraries)
        
        # 假设平均比特率为64kbps (Assume average bitrate of 64kbps)
        average_bitrate = 64 * 1024 / 8  # 64kbps in bytes per second
        estimated_duration = audio_file.size / average_bitrate
        
        # 限制在合理范围内 (Limit to reasonable range)
        return min(max(estimated_duration, 0.1), VoiceServiceConfig.AUDIO_MAX_DURATION)
    
    def get_supported_formats(self) -> list:
        """
        获取支持的音频格式列表 (Get list of supported audio formats)
        
        Returns:
            list: 支持的音频格式 (Supported audio formats)
        """
        return VoiceServiceConfig.AUDIO_ALLOWED_FORMATS.copy()
    
    def get_max_file_size(self) -> int:
        """
        获取最大文件大小限制 (Get maximum file size limit)
        
        Returns:
            int: 最大文件大小（字节） (Maximum file size in bytes)
        """
        return VoiceServiceConfig.AUDIO_UPLOAD_MAX_SIZE
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        获取服务状态信息 (Get service status information)
        
        Returns:
            Dict[str, Any]: 服务状态 (Service status)
        """
        return {
            'service_name': 'OpenAI Whisper Speech Recognition',
            'api_key_configured': bool(self.api_key),
            'api_url': self.whisper_url,
            'timeout': self.timeout,
            'max_file_size': self.get_max_file_size(),
            'supported_formats': self.get_supported_formats(),
            'max_duration': VoiceServiceConfig.AUDIO_MAX_DURATION
        }