"""
安全措施实现模块 (Security Measures Implementation Module)
包含API速率限制、音频文件安全验证、输入清理等功能
"""

import time
import hashlib
import mimetypes
import magic
import re
import html
import logging
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from typing import Dict, List, Optional, Tuple, Any
import os
import tempfile

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    API速率限制器 (API Rate Limiter)
    实现基于用户和IP的速率限制机制
    """
    
    # 默认速率限制配置 (Default rate limit configuration)
    DEFAULT_LIMITS = {
        'chat_api': {'requests': 30, 'window': 60},  # 30 requests per minute
        'transcribe_audio': {'requests': 10, 'window': 60},  # 10 requests per minute
        'translate_text': {'requests': 20, 'window': 60},  # 20 requests per minute
        'general': {'requests': 100, 'window': 60}  # 100 requests per minute for other APIs
    }
    
    @classmethod
    def get_cache_key(cls, identifier: str, endpoint: str) -> str:
        """生成缓存键 (Generate cache key)"""
        return f"rate_limit:{endpoint}:{identifier}"
    
    @classmethod
    def get_user_identifier(cls, request) -> str:
        """获取用户标识符 (Get user identifier)"""
        if request.user.is_authenticated:
            return f"user:{request.user.id}"
        else:
            # 使用IP地址作为匿名用户标识符 (Use IP address for anonymous users)
            ip = cls.get_client_ip(request)
            return f"ip:{ip}"
    
    @classmethod
    def get_client_ip(cls, request) -> str:
        """获取客户端真实 IP (Get the client's real IP).

        站点位于 Cloudflare → nginx 之后。按可信度优先取：
          1. CF-Connecting-IP —— Cloudflare 设置的权威客户端 IP（在"源站只接受 CF 回源"
             的前提下不可伪造）；
          2. X-Real-IP —— nginx 设置的真实 IP；
          3. X-Forwarded-For 最左值 —— 仅作回退（可被客户端伪造，不应单独信任）；
          4. REMOTE_ADDR。
        要彻底防 XFF 伪造，需在源站防火墙只放行 Cloudflare 回源网段。
        (Prefer trusted proxy headers; XFF is spoofable and used only as a fallback.)
        """
        cf_ip = request.META.get('HTTP_CF_CONNECTING_IP')
        if cf_ip:
            return cf_ip.strip()

        real_ip = request.META.get('HTTP_X_REAL_IP')
        if real_ip:
            return real_ip.strip()

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()

        return request.META.get('REMOTE_ADDR', '127.0.0.1')
    
    @classmethod
    def is_rate_limited(cls, request, endpoint: str) -> Tuple[bool, Dict[str, Any]]:
        """
        检查是否超出速率限制 (Check if rate limited)
        
        Returns:
            Tuple[bool, Dict]: (is_limited, rate_info)
        """
        identifier = cls.get_user_identifier(request)
        cache_key = cls.get_cache_key(identifier, endpoint)
        
        # 获取速率限制配置 (Get rate limit configuration)
        limits = cls.DEFAULT_LIMITS.get(endpoint, cls.DEFAULT_LIMITS['general'])
        max_requests = limits['requests']
        window_seconds = limits['window']
        
        # 获取当前时间戳 (Get current timestamp)
        now = int(time.time())
        window_start = now - window_seconds
        
        # 获取请求历史 (Get request history)
        request_history = cache.get(cache_key, [])
        
        # 清理过期的请求记录 (Clean expired request records)
        request_history = [timestamp for timestamp in request_history if timestamp > window_start]
        
        # 检查是否超出限制 (Check if limit exceeded)
        is_limited = len(request_history) >= max_requests
        
        if not is_limited:
            # 添加当前请求到历史记录 (Add current request to history)
            request_history.append(now)
            cache.set(cache_key, request_history, window_seconds + 10)  # 额外10秒缓存时间
        
        # 计算重置时间 (Calculate reset time)
        reset_time = window_start + window_seconds if request_history else now
        remaining_requests = max(0, max_requests - len(request_history))
        
        rate_info = {
            'limit': max_requests,
            'remaining': remaining_requests,
            'reset_time': reset_time,
            'window_seconds': window_seconds
        }
        
        return is_limited, rate_info
    
    @classmethod
    def log_rate_limit_violation(cls, request, endpoint: str, rate_info: Dict[str, Any]):
        """记录速率限制违规 (Log rate limit violation)"""
        identifier = cls.get_user_identifier(request)
        ip = cls.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
        
        logger.warning(
            f"Rate limit exceeded - Endpoint: {endpoint}, "
            f"Identifier: {identifier}, IP: {ip}, "
            f"User-Agent: {user_agent}, "
            f"Limit: {rate_info['limit']}, "
            f"Window: {rate_info['window_seconds']}s"
        )


def rate_limit(endpoint: str):
    """
    速率限制装饰器 (Rate limiting decorator)
    
    Args:
        endpoint: API端点名称 (API endpoint name)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            is_limited, rate_info = RateLimiter.is_rate_limited(request, endpoint)
            
            if is_limited:
                RateLimiter.log_rate_limit_violation(request, endpoint, rate_info)
                
                return JsonResponse({
                    'success': False,
                    'error': 'Rate limit exceeded. Please try again later.',
                    'error_code': 'rate_limit_exceeded',
                    'rate_limit_info': {
                        'limit': rate_info['limit'],
                        'reset_time': rate_info['reset_time'],
                        'window_seconds': rate_info['window_seconds']
                    }
                }, status=429)
            
            # 在响应头中添加速率限制信息 (Add rate limit info to response headers)
            response = view_func(request, *args, **kwargs)
            if hasattr(response, '__setitem__'):  # JsonResponse支持设置头部
                response['X-RateLimit-Limit'] = str(rate_info['limit'])
                response['X-RateLimit-Remaining'] = str(rate_info['remaining'])
                response['X-RateLimit-Reset'] = str(rate_info['reset_time'])
            
            return response
        return wrapper
    return decorator


class AudioSecurityValidator:
    """
    音频文件安全验证器 (Audio File Security Validator)
    实现音频文件的安全验证和扫描功能
    """
    
    # 允许的音频MIME类型 (Allowed audio MIME types)
    ALLOWED_MIME_TYPES = {
        'audio/wav',
        'audio/wave',
        'audio/x-wav',
        'audio/mpeg',
        'audio/mp3',
        'audio/mp4',
        'audio/m4a',
        'audio/aac',
        'audio/ogg',
        'audio/webm',
        'audio/flac'
    }
    
    # 允许的文件扩展名 (Allowed file extensions)
    ALLOWED_EXTENSIONS = {
        '.wav', '.mp3', '.mp4', '.m4a', '.aac', '.ogg', '.webm', '.flac'
    }
    
    # 最大文件大小 (Maximum file size) - 10MB
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    # 最大音频时长 (Maximum audio duration) - 5 minutes
    MAX_DURATION_SECONDS = 300
    
    # 危险的文件头部签名 (Dangerous file header signatures)
    DANGEROUS_SIGNATURES = [
        b'\x4D\x5A',  # PE executable
        b'\x7F\x45\x4C\x46',  # ELF executable
        b'\xCA\xFE\xBA\xBE',  # Java class file
        b'\x50\x4B\x03\x04',  # ZIP archive (could contain malware)
        b'\x52\x61\x72\x21',  # RAR archive
        b'<script',  # HTML script tag
        b'javascript:',  # JavaScript protocol
    ]
    
    @classmethod
    def validate_file_basic(cls, audio_file) -> Dict[str, Any]:
        """
        基础文件验证 (Basic file validation)
        
        Args:
            audio_file: Django UploadedFile对象
            
        Returns:
            Dict: 验证结果
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'file_info': {}
        }
        
        # 检查文件是否存在 (Check if file exists)
        if not audio_file:
            validation_result['is_valid'] = False
            validation_result['errors'].append('No audio file provided')
            return validation_result
        
        # 检查文件大小 (Check file size)
        if audio_file.size > cls.MAX_FILE_SIZE:
            validation_result['is_valid'] = False
            validation_result['errors'].append(
                f'File size ({audio_file.size} bytes) exceeds maximum allowed size ({cls.MAX_FILE_SIZE} bytes)'
            )
        
        # 检查文件名 (Check filename)
        if not audio_file.name:
            validation_result['warnings'].append('No filename provided')
        else:
            # 检查文件扩展名 (Check file extension)
            file_ext = os.path.splitext(audio_file.name.lower())[1]
            if file_ext not in cls.ALLOWED_EXTENSIONS:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f'File extension {file_ext} not allowed')
        
        # 记录文件信息 (Record file info)
        validation_result['file_info'] = {
            'name': audio_file.name,
            'size': audio_file.size,
            'content_type': getattr(audio_file, 'content_type', 'unknown')
        }
        
        return validation_result
    
    @classmethod
    def validate_mime_type(cls, audio_file) -> Dict[str, Any]:
        """
        MIME类型验证 (MIME type validation)
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'detected_mime_type': None
        }
        
        try:
            # 使用python-magic检测真实的MIME类型 (Use python-magic to detect real MIME type)
            # 读取文件头部进行检测 (Read file header for detection)
            audio_file.seek(0)
            file_header = audio_file.read(1024)  # 读取前1KB
            audio_file.seek(0)  # 重置文件指针
            
            # 使用magic库检测MIME类型 (Use magic library to detect MIME type)
            try:
                detected_mime = magic.from_buffer(file_header, mime=True)
                validation_result['detected_mime_type'] = detected_mime
                
                if detected_mime not in cls.ALLOWED_MIME_TYPES:
                    validation_result['is_valid'] = False
                    validation_result['errors'].append(
                        f'Detected MIME type {detected_mime} not allowed'
                    )
            except Exception as e:
                # 如果magic库不可用，使用mimetypes作为后备 (Use mimetypes as fallback if magic is unavailable)
                logger.warning(f"Magic library detection failed: {e}")
                guessed_mime, _ = mimetypes.guess_type(audio_file.name)
                validation_result['detected_mime_type'] = guessed_mime
                
                if guessed_mime and guessed_mime not in cls.ALLOWED_MIME_TYPES:
                    validation_result['is_valid'] = False
                    validation_result['errors'].append(
                        f'Guessed MIME type {guessed_mime} not allowed'
                    )
        
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f'MIME type validation failed: {str(e)}')
        
        return validation_result
    
    @classmethod
    def scan_for_malicious_content(cls, audio_file) -> Dict[str, Any]:
        """
        恶意内容扫描 (Malicious content scanning)
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'threats_detected': []
        }
        
        try:
            audio_file.seek(0)
            file_content = audio_file.read(2048)  # 读取前2KB进行扫描
            audio_file.seek(0)  # 重置文件指针
            
            # 检查危险的文件签名 (Check for dangerous file signatures)
            for signature in cls.DANGEROUS_SIGNATURES:
                if signature in file_content:
                    validation_result['is_valid'] = False
                    validation_result['threats_detected'].append(f'Dangerous signature detected: {signature.hex()}')
            
            # 检查可疑的字符串模式 (Check for suspicious string patterns)
            suspicious_patterns = [
                b'<script',
                b'javascript:',
                b'vbscript:',
                b'data:text/html',
                b'eval(',
                b'exec(',
                b'system(',
                b'shell_exec'
            ]
            
            for pattern in suspicious_patterns:
                if pattern in file_content.lower():
                    validation_result['is_valid'] = False
                    validation_result['threats_detected'].append(f'Suspicious pattern detected: {pattern.decode("utf-8", errors="ignore")}')
            
            if validation_result['threats_detected']:
                validation_result['errors'].append('Malicious content detected in file')
        
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f'Malicious content scan failed: {str(e)}')
        
        return validation_result
    
    @classmethod
    def validate_audio_properties(cls, audio_file) -> Dict[str, Any]:
        """
        音频属性验证 (Audio properties validation)
        使用基础方法验证音频文件属性
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'audio_info': {}
        }
        
        try:
            # 基础音频文件验证 (Basic audio file validation)
            # 这里可以添加更复杂的音频属性检查，如使用pydub或其他音频库
            # 目前使用简单的文件大小和时长估算
            
            file_size = audio_file.size
            
            # 估算音频时长（基于文件大小的粗略估算）
            # 假设平均比特率为128kbps (Rough duration estimation based on file size)
            estimated_duration = (file_size * 8) / (128 * 1000)  # 秒
            
            if estimated_duration > cls.MAX_DURATION_SECONDS:
                validation_result['is_valid'] = False
                validation_result['errors'].append(
                    f'Estimated audio duration ({estimated_duration:.1f}s) exceeds maximum allowed ({cls.MAX_DURATION_SECONDS}s)'
                )
            
            validation_result['audio_info'] = {
                'estimated_duration': estimated_duration,
                'file_size': file_size
            }
        
        except Exception as e:
            validation_result['warnings'].append(f'Audio properties validation failed: {str(e)}')
        
        return validation_result
    
    @classmethod
    def comprehensive_validate(cls, audio_file) -> Dict[str, Any]:
        """
        综合音频文件验证 (Comprehensive audio file validation)
        
        Args:
            audio_file: Django UploadedFile对象
            
        Returns:
            Dict: 完整的验证结果
        """
        final_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'file_info': {},
            'validation_details': {}
        }
        
        # 执行各项验证 (Perform various validations)
        validations = [
            ('basic', cls.validate_file_basic),
            ('mime_type', cls.validate_mime_type),
            ('malicious_content', cls.scan_for_malicious_content),
            ('audio_properties', cls.validate_audio_properties)
        ]
        
        for validation_name, validation_func in validations:
            try:
                result = validation_func(audio_file)
                final_result['validation_details'][validation_name] = result
                
                if not result['is_valid']:
                    final_result['is_valid'] = False
                
                final_result['errors'].extend(result.get('errors', []))
                final_result['warnings'].extend(result.get('warnings', []))
                
                # 合并文件信息 (Merge file info)
                if 'file_info' in result:
                    final_result['file_info'].update(result['file_info'])
                if 'audio_info' in result:
                    final_result['file_info'].update(result['audio_info'])
                
            except Exception as e:
                final_result['is_valid'] = False
                final_result['errors'].append(f'{validation_name} validation failed: {str(e)}')
                logger.error(f"Audio validation error in {validation_name}: {str(e)}")
        
        # 记录验证结果 (Log validation result)
        if not final_result['is_valid']:
            logger.warning(f"Audio file validation failed: {final_result['errors']}")
        else:
            logger.info(f"Audio file validation passed: {final_result['file_info']}")
        
        return final_result


class InputSanitizer:
    """
    输入清理和验证器 (Input Sanitizer and Validator)
    增强的用户输入验证和清理功能
    """
    
    # XSS攻击模式 (XSS attack patterns)
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'onload\s*=',
        r'onerror\s*=',
        r'onclick\s*=',
        r'onmouseover\s*=',
        r'onfocus\s*=',
        r'onblur\s*=',
        r'onchange\s*=',
        r'onsubmit\s*=',
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
        r'<link[^>]*>',
        r'<meta[^>]*>',
        r'data:text/html',
        r'data:application/javascript'
    ]
    
    # SQL注入模式 (SQL injection patterns)
    SQL_INJECTION_PATTERNS = [
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)',
        r'(\b(UNION|OR|AND)\s+\d+\s*=\s*\d+)',
        r'(\b(OR|AND)\s+[\'"]?\w+[\'"]?\s*=\s*[\'"]?\w+[\'"]?)',
        r'[\'"];?\s*(DROP|DELETE|INSERT|UPDATE)',
        r'(\b(EXEC|EXECUTE)\s*\()',
        r'(\b(SP_|XP_)\w+)',
        r'(--|\#|/\*|\*/)',
    ]
    
    # 命令注入模式 (Command injection patterns)
    COMMAND_INJECTION_PATTERNS = [
        r'(\b(system|exec|eval|shell_exec|passthru|popen|proc_open)\s*\()',
        r'(\$\(.*\))',
        r'(`.*`)',
        r'(\|\s*(rm|del|format|fdisk|mkfs))',
        r'(&&|\|\||;)\s*(rm|del|format)',
        r'(\b(wget|curl|nc|netcat|telnet|ssh)\b)',
    ]
    
    @classmethod
    def sanitize_text(cls, text: str, max_length: int = 1000, allow_html: bool = False) -> str:
        """
        清理文本输入 (Sanitize text input)
        
        Args:
            text: 输入文本
            max_length: 最大长度
            allow_html: 是否允许HTML标签
            
        Returns:
            str: 清理后的文本
        """
        if not text or not isinstance(text, str):
            return ""
        
        # 限制长度 (Limit length)
        text = text[:max_length]
        
        # 移除控制字符 (Remove control characters)
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
        
        if not allow_html:
            # HTML转义 (HTML escape)
            text = html.escape(text)
        
        # 移除XSS攻击模式 (Remove XSS attack patterns)
        for pattern in cls.XSS_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)

        # 注意：不再对 SQL/命令关键字做黑名单剥离。
        # 本项目全程使用 Django 参数化 ORM（无裸 SQL 拼接），也从不把用户输入当 shell 命令执行，
        # 因此剥离 SELECT/UPDATE/DELETE/and/or、rm/curl 等关键字几乎没有安全收益，
        # 却会破坏这个中英文学习聊天里的正常输入（如 "update my plan" / "select the red one"）。
        # SQL 安全由 ORM 保证，XSS 由上面的转义 + 模板/前端输出转义保证。
        # (No SQL/command keyword stripping: parameterised ORM handles SQL safety;
        #  blocklisting natural-language words corrupted legitimate learner input.)

        # 清理多余的空白字符 (Clean excessive whitespace)
        text = re.sub(r'\s+', ' ', text).strip()

        return text
    
    @classmethod
    def validate_text_content(cls, text: str) -> Dict[str, Any]:
        """
        验证文本内容安全性 (Validate text content security)
        
        Args:
            text: 要验证的文本
            
        Returns:
            Dict: 验证结果
        """
        validation_result = {
            'is_safe': True,
            'threats_detected': [],
            'risk_level': 'low'
        }
        
        if not text:
            return validation_result
        
        threat_count = 0

        # 仅检测 XSS 模式：这是唯一对本应用有实际意义的注入面（用户内容会被渲染）。
        # SQL/命令注入检测已移除 —— 参数化 ORM 已保证 SQL 安全，且把正常语言输入
        # （含 update/select/delete 等普通英文词）误判为威胁会拒收合法消息。
        # (Only XSS detection is meaningful here; SQL/command checks removed to avoid
        #  rejecting legitimate natural-language input in this learning chat.)
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                validation_result['threats_detected'].append(f'XSS pattern detected: {pattern}')
                threat_count += 1

        # 确定风险级别 (Determine risk level)
        if threat_count == 0:
            validation_result['risk_level'] = 'low'
        elif threat_count <= 2:
            validation_result['risk_level'] = 'medium'
            validation_result['is_safe'] = False
        else:
            validation_result['risk_level'] = 'high'
            validation_result['is_safe'] = False
        
        return validation_result
    
    @classmethod
    def sanitize_json_data(cls, data: Dict[str, Any], field_configs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        清理JSON数据 (Sanitize JSON data)
        
        Args:
            data: 输入的JSON数据
            field_configs: 字段配置，格式为 {field_name: {max_length: int, allow_html: bool}}
            
        Returns:
            Dict: 清理后的数据
        """
        sanitized_data = {}
        
        for field_name, field_config in field_configs.items():
            if field_name in data:
                value = data[field_name]
                if isinstance(value, str):
                    max_length = field_config.get('max_length', 1000)
                    allow_html = field_config.get('allow_html', False)
                    sanitized_data[field_name] = cls.sanitize_text(value, max_length, allow_html)
                else:
                    sanitized_data[field_name] = value
        
        return sanitized_data


def security_headers(view_func):
    """
    安全头部装饰器 (Security headers decorator)
    为响应添加安全相关的HTTP头部
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        
        # 添加安全头部 (Add security headers)
        if hasattr(response, '__setitem__'):
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'DENY'
            response['X-XSS-Protection'] = '1; mode=block'
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
        
        return response
    return wrapper


def log_security_event(event_type: str, request, details: Dict[str, Any]):
    """
    记录安全事件 (Log security event)
    
    Args:
        event_type: 事件类型
        request: Django请求对象
        details: 事件详情
    """
    user_id = request.user.id if request.user.is_authenticated else 'anonymous'
    ip_address = RateLimiter.get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
    
    logger.warning(
        f"Security Event - Type: {event_type}, "
        f"User: {user_id}, IP: {ip_address}, "
        f"User-Agent: {user_agent}, "
        f"Details: {details}"
    )


# 安全验证装饰器组合 (Security validation decorator combination)
def secure_api(endpoint: str, require_auth: bool = True):
    """
    安全API装饰器组合 (Secure API decorator combination)
    结合速率限制、安全头部等多种安全措施
    
    Args:
        endpoint: API端点名称
        require_auth: 是否需要认证
    """
    def decorator(view_func):
        # 应用多个装饰器 (Apply multiple decorators)
        decorated_func = view_func
        decorated_func = security_headers(decorated_func)
        decorated_func = rate_limit(endpoint)(decorated_func)
        
        if require_auth:
            from django.contrib.auth.decorators import login_required
            decorated_func = login_required(decorated_func)
        
        return decorated_func
    return decorator