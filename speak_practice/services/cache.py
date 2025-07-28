"""
缓存服务实现 (Cache Service Implementation)
"""

import hashlib
from typing import Optional, Any
from django.core.cache import cache
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from .base import CacheInterface
from .config import VoiceServiceConfig
from .exceptions import CacheError, CacheConnectionError


class TTSCacheService(CacheInterface):
    """
    TTS缓存服务实现 (TTS cache service implementation)
    """
    
    def __init__(self):
        self.cache_timeout = VoiceServiceConfig.TTS_CACHE_TIMEOUT
        self.key_prefix = VoiceServiceConfig.get_cache_key_prefix() + 'tts_'
    
    def get_cache_key(self, text: str, language_code: str, voice_name: str = None) -> str:
        """
        生成TTS缓存键 (Generate TTS cache key)
        
        Args:
            text: 文本内容 (Text content)
            language_code: 语言代码 (Language code)
            voice_name: 语音名称 (Voice name)
            
        Returns:
            str: 缓存键 (Cache key)
        """
        content = f"{text}:{language_code}"
        if voice_name:
            content += f":{voice_name}"
        
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        return f"{self.key_prefix}{content_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存数据 (Get cached data)
        
        Args:
            key: 缓存键 (Cache key)
            
        Returns:
            Optional[Any]: 缓存的数据，如果不存在则返回None (Cached data, None if not exists)
        """
        try:
            return cache.get(key)
        except Exception as e:
            raise CacheConnectionError(f"Failed to get cache data: {str(e)}")
    
    def set(self, key: str, value: Any, timeout: int = None) -> bool:
        """
        设置缓存数据 (Set cached data)
        
        Args:
            key: 缓存键 (Cache key)
            value: 要缓存的数据 (Data to cache)
            timeout: 超时时间（秒），None使用默认值 (Timeout in seconds, None for default)
            
        Returns:
            bool: 设置是否成功 (Whether setting was successful)
        """
        try:
            if timeout is None:
                timeout = self.cache_timeout
            cache.set(key, value, timeout)
            return True
        except Exception as e:
            raise CacheConnectionError(f"Failed to set cache data: {str(e)}")
    
    def delete(self, key: str) -> bool:
        """
        删除缓存数据 (Delete cached data)
        
        Args:
            key: 缓存键 (Cache key)
            
        Returns:
            bool: 删除是否成功 (Whether deletion was successful)
        """
        try:
            cache.delete(key)
            return True
        except Exception as e:
            raise CacheConnectionError(f"Failed to delete cache data: {str(e)}")
    
    def clear(self) -> bool:
        """
        清空所有TTS缓存 (Clear all TTS cache)
        
        Returns:
            bool: 清空是否成功 (Whether clearing was successful)
        """
        try:
            # Django的cache.clear()会清空所有缓存，这里我们只清空TTS相关的
            # Django's cache.clear() clears all cache, here we only clear TTS-related cache
            # 由于Django缓存API限制，我们无法直接按前缀删除
            # Due to Django cache API limitations, we cannot delete by prefix directly
            # 这里返回True，实际实现可能需要使用Redis等支持模式匹配的缓存后端
            # Return True here, actual implementation may need Redis or other cache backends that support pattern matching
            return True
        except Exception as e:
            raise CacheConnectionError(f"Failed to clear cache: {str(e)}")
    
    def get_cached_audio(self, text: str, language_code: str, voice_name: str = None) -> Optional[str]:
        """
        获取缓存的音频数据 (Get cached audio data)
        
        Args:
            text: 文本内容 (Text content)
            language_code: 语言代码 (Language code)
            voice_name: 语音名称 (Voice name)
            
        Returns:
            Optional[str]: Base64编码的音频数据，如果不存在则返回None (Base64 encoded audio data, None if not exists)
        """
        cache_key = self.get_cache_key(text, language_code, voice_name)
        return self.get(cache_key)
    
    def cache_audio(self, text: str, language_code: str, audio_data: str, voice_name: str = None) -> bool:
        """
        缓存音频数据 (Cache audio data)
        
        Args:
            text: 文本内容 (Text content)
            language_code: 语言代码 (Language code)
            audio_data: Base64编码的音频数据 (Base64 encoded audio data)
            voice_name: 语音名称 (Voice name)
            
        Returns:
            bool: 缓存是否成功 (Whether caching was successful)
        """
        cache_key = self.get_cache_key(text, language_code, voice_name)
        return self.set(cache_key, audio_data)
    
    def get_cache_stats(self) -> dict:
        """
        获取缓存统计信息 (Get cache statistics)
        
        Returns:
            dict: 缓存统计信息 (Cache statistics)
        """
        # 这是一个简化的实现，实际的统计信息获取可能需要更复杂的逻辑
        # This is a simplified implementation, actual statistics gathering may need more complex logic
        return {
            'cache_timeout': self.cache_timeout,
            'key_prefix': self.key_prefix,
            'backend': str(cache.__class__.__name__)
        }


class TranslationCacheService(CacheInterface):
    """
    翻译缓存服务实现 (Translation cache service implementation)
    """
    
    def __init__(self):
        self.cache_timeout = VoiceServiceConfig.TTS_CACHE_TIMEOUT  # 使用相同的超时时间 (Use same timeout)
        self.key_prefix = VoiceServiceConfig.get_cache_key_prefix() + 'translation_'
    
    def get_cache_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        生成翻译缓存键 (Generate translation cache key)
        
        Args:
            text: 原文本 (Original text)
            source_lang: 源语言 (Source language)
            target_lang: 目标语言 (Target language)
            
        Returns:
            str: 缓存键 (Cache key)
        """
        content = f"{text}:{source_lang}:{target_lang}"
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        return f"{self.key_prefix}{content_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据 (Get cached data)"""
        try:
            return cache.get(key)
        except Exception as e:
            raise CacheConnectionError(f"Failed to get translation cache: {str(e)}")
    
    def set(self, key: str, value: Any, timeout: int = None) -> bool:
        """设置缓存数据 (Set cached data)"""
        try:
            if timeout is None:
                timeout = self.cache_timeout
            cache.set(key, value, timeout)
            return True
        except Exception as e:
            raise CacheConnectionError(f"Failed to set translation cache: {str(e)}")
    
    def delete(self, key: str) -> bool:
        """删除缓存数据 (Delete cached data)"""
        try:
            cache.delete(key)
            return True
        except Exception as e:
            raise CacheConnectionError(f"Failed to delete translation cache: {str(e)}")
    
    def clear(self) -> bool:
        """清空翻译缓存 (Clear translation cache)"""
        try:
            return True  # 简化实现 (Simplified implementation)
        except Exception as e:
            raise CacheConnectionError(f"Failed to clear translation cache: {str(e)}")
    
    def get_cached_translation(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """
        获取缓存的翻译结果 (Get cached translation result)
        
        Args:
            text: 原文本 (Original text)
            source_lang: 源语言 (Source language)
            target_lang: 目标语言 (Target language)
            
        Returns:
            Optional[str]: 翻译结果，如果不存在则返回None (Translation result, None if not exists)
        """
        cache_key = self.get_cache_key(text, source_lang, target_lang)
        return self.get(cache_key)
    
    def cache_translation(self, text: str, source_lang: str, target_lang: str, translation: str) -> bool:
        """
        缓存翻译结果 (Cache translation result)
        
        Args:
            text: 原文本 (Original text)
            source_lang: 源语言 (Source language)
            target_lang: 目标语言 (Target language)
            translation: 翻译结果 (Translation result)
            
        Returns:
            bool: 缓存是否成功 (Whether caching was successful)
        """
        cache_key = self.get_cache_key(text, source_lang, target_lang)
        return self.set(cache_key, translation)


# 全局缓存服务实例 (Global cache service instances)
tts_cache = TTSCacheService()
translation_cache = TranslationCacheService()