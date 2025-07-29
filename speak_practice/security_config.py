"""
安全配置模块 (Security Configuration Module)
集中管理所有安全相关的配置和设置
"""

from django.conf import settings
import os

# 速率限制配置 (Rate Limiting Configuration)
RATE_LIMIT_CONFIG = {
    'chat_api': {
        'requests': getattr(settings, 'CHAT_API_RATE_LIMIT', 30),
        'window': 60,  # 1 minute
        'burst_limit': getattr(settings, 'CHAT_API_BURST_LIMIT', 5)  # 5 requests in 10 seconds
    },
    'transcribe_audio': {
        'requests': getattr(settings, 'AUDIO_API_RATE_LIMIT', 10),
        'window': 60,
        'burst_limit': getattr(settings, 'AUDIO_API_BURST_LIMIT', 3)
    },
    'translate_text': {
        'requests': getattr(settings, 'TRANSLATE_API_RATE_LIMIT', 20),
        'window': 60,
        'burst_limit': getattr(settings, 'TRANSLATE_API_BURST_LIMIT', 5)
    },
    'translate_chinese': {
        'requests': getattr(settings, 'TRANSLATE_CHINESE_API_RATE_LIMIT', 20),
        'window': 60,
        'burst_limit': getattr(settings, 'TRANSLATE_CHINESE_API_BURST_LIMIT', 5)
    },
    'general': {
        'requests': getattr(settings, 'GENERAL_API_RATE_LIMIT', 100),
        'window': 60,
        'burst_limit': getattr(settings, 'GENERAL_API_BURST_LIMIT', 10)
    }
}

# 音频文件安全配置 (Audio File Security Configuration)
AUDIO_SECURITY_CONFIG = {
    'max_file_size': getattr(settings, 'AUDIO_MAX_FILE_SIZE', 10 * 1024 * 1024),  # 10MB
    'max_duration': getattr(settings, 'AUDIO_MAX_DURATION', 300),  # 5 minutes
    'allowed_mime_types': getattr(settings, 'AUDIO_ALLOWED_MIME_TYPES', {
        'audio/wav', 'audio/wave', 'audio/x-wav',
        'audio/mpeg', 'audio/mp3', 'audio/mp4',
        'audio/m4a', 'audio/aac', 'audio/ogg',
        'audio/webm', 'audio/flac'
    }),
    'allowed_extensions': getattr(settings, 'AUDIO_ALLOWED_EXTENSIONS', {
        '.wav', '.mp3', '.mp4', '.m4a', '.aac', '.ogg', '.webm', '.flac'
    }),
    'scan_enabled': getattr(settings, 'AUDIO_MALWARE_SCAN_ENABLED', True),
    'quarantine_suspicious': getattr(settings, 'AUDIO_QUARANTINE_SUSPICIOUS', True)
}

# 输入验证配置 (Input Validation Configuration)
INPUT_VALIDATION_CONFIG = {
    'max_text_length': getattr(settings, 'INPUT_MAX_TEXT_LENGTH', 1000),
    'max_message_length': getattr(settings, 'INPUT_MAX_MESSAGE_LENGTH', 1000),
    'max_translation_length': getattr(settings, 'INPUT_MAX_TRANSLATION_LENGTH', 500),
    'allow_html': getattr(settings, 'INPUT_ALLOW_HTML', False),
    'strict_validation': getattr(settings, 'INPUT_STRICT_VALIDATION', True),
    'log_suspicious_input': getattr(settings, 'INPUT_LOG_SUSPICIOUS', True)
}

# 安全日志配置 (Security Logging Configuration)
SECURITY_LOGGING_CONFIG = {
    'log_rate_limits': getattr(settings, 'SECURITY_LOG_RATE_LIMITS', True),
    'log_malicious_uploads': getattr(settings, 'SECURITY_LOG_MALICIOUS_UPLOADS', True),
    'log_input_validation': getattr(settings, 'SECURITY_LOG_INPUT_VALIDATION', True),
    'log_authentication_failures': getattr(settings, 'SECURITY_LOG_AUTH_FAILURES', True),
    'alert_threshold': getattr(settings, 'SECURITY_ALERT_THRESHOLD', 10),  # 10 violations per hour
    'retention_days': getattr(settings, 'SECURITY_LOG_RETENTION_DAYS', 30)
}

# CSRF保护配置 (CSRF Protection Configuration)
CSRF_CONFIG = {
    'cookie_secure': not settings.DEBUG,  # HTTPS only in production
    'cookie_httponly': True,
    'cookie_samesite': 'Strict',
    'trusted_origins': getattr(settings, 'CSRF_TRUSTED_ORIGINS', []),
    'failure_view': 'speak_practice.views.csrf_failure'
}

# 内容安全策略配置 (Content Security Policy Configuration)
CSP_CONFIG = {
    'default_src': ["'self'"],
    'script_src': ["'self'", "'unsafe-inline'"],  # 允许内联脚本用于现有功能
    'style_src': ["'self'", "'unsafe-inline'"],   # 允许内联样式
    'img_src': ["'self'", "data:", "https:"],
    'font_src': ["'self'", "https://fonts.gstatic.com"],
    'connect_src': ["'self'"],
    'media_src': ["'self'", "data:"],
    'object_src': ["'none'"],
    'base_uri': ["'self'"],
    'form_action': ["'self'"],
    'frame_ancestors': ["'none'"],
    'upgrade_insecure_requests': not settings.DEBUG
}

# API密钥安全配置 (API Key Security Configuration)
API_KEY_CONFIG = {
    'openai_key_required': True,
    'google_key_required': True,
    'key_rotation_days': getattr(settings, 'API_KEY_ROTATION_DAYS', 90),
    'key_usage_monitoring': getattr(settings, 'API_KEY_USAGE_MONITORING', True),
    'key_quota_alerts': getattr(settings, 'API_KEY_QUOTA_ALERTS', True)
}

# 会话安全配置 (Session Security Configuration)
SESSION_SECURITY_CONFIG = {
    'session_timeout': getattr(settings, 'SESSION_TIMEOUT_MINUTES', 30) * 60,  # 30 minutes
    'max_sessions_per_user': getattr(settings, 'MAX_SESSIONS_PER_USER', 5),
    'concurrent_session_limit': getattr(settings, 'CONCURRENT_SESSION_LIMIT', 3),
    'session_hijacking_detection': getattr(settings, 'SESSION_HIJACKING_DETECTION', True)
}

# 防暴力破解配置 (Brute Force Protection Configuration)
BRUTE_FORCE_CONFIG = {
    'max_login_attempts': getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5),
    'lockout_duration': getattr(settings, 'LOCKOUT_DURATION_MINUTES', 15) * 60,  # 15 minutes
    'progressive_delay': getattr(settings, 'PROGRESSIVE_DELAY_ENABLED', True),
    'ip_whitelist': getattr(settings, 'IP_WHITELIST', ['127.0.0.1', '::1']),
    'captcha_threshold': getattr(settings, 'CAPTCHA_THRESHOLD', 3)
}

# 数据加密配置 (Data Encryption Configuration)
ENCRYPTION_CONFIG = {
    'encrypt_sensitive_data': getattr(settings, 'ENCRYPT_SENSITIVE_DATA', True),
    'encryption_key_rotation': getattr(settings, 'ENCRYPTION_KEY_ROTATION_DAYS', 30),
    'hash_algorithm': getattr(settings, 'HASH_ALGORITHM', 'sha256'),
    'salt_rounds': getattr(settings, 'SALT_ROUNDS', 12)
}

# 监控和告警配置 (Monitoring and Alerting Configuration)
MONITORING_CONFIG = {
    'real_time_monitoring': getattr(settings, 'REAL_TIME_MONITORING', True),
    'anomaly_detection': getattr(settings, 'ANOMALY_DETECTION', True),
    'alert_email': getattr(settings, 'SECURITY_ALERT_EMAIL', None),
    'alert_webhook': getattr(settings, 'SECURITY_ALERT_WEBHOOK', None),
    'metrics_retention': getattr(settings, 'METRICS_RETENTION_DAYS', 90)
}

# 生产环境安全检查清单 (Production Security Checklist)
PRODUCTION_SECURITY_CHECKLIST = {
    'debug_disabled': not settings.DEBUG,
    'secret_key_secure': len(settings.SECRET_KEY) >= 50,
    'allowed_hosts_configured': bool(settings.ALLOWED_HOSTS),
    'https_enforced': getattr(settings, 'SECURE_SSL_REDIRECT', False),
    'secure_cookies': getattr(settings, 'SESSION_COOKIE_SECURE', False),
    'csrf_protection': 'django.middleware.csrf.CsrfViewMiddleware' in settings.MIDDLEWARE,
    'xframe_protection': getattr(settings, 'X_FRAME_OPTIONS', None) == 'DENY',
    'content_type_nosniff': getattr(settings, 'SECURE_CONTENT_TYPE_NOSNIFF', False),
    'hsts_enabled': getattr(settings, 'SECURE_HSTS_SECONDS', 0) > 0
}


def get_security_config(config_name: str) -> dict:
    """
    获取安全配置 (Get security configuration)
    
    Args:
        config_name: 配置名称
        
    Returns:
        dict: 配置字典
    """
    config_map = {
        'rate_limit': RATE_LIMIT_CONFIG,
        'audio_security': AUDIO_SECURITY_CONFIG,
        'input_validation': INPUT_VALIDATION_CONFIG,
        'security_logging': SECURITY_LOGGING_CONFIG,
        'csrf': CSRF_CONFIG,
        'csp': CSP_CONFIG,
        'api_key': API_KEY_CONFIG,
        'session_security': SESSION_SECURITY_CONFIG,
        'brute_force': BRUTE_FORCE_CONFIG,
        'encryption': ENCRYPTION_CONFIG,
        'monitoring': MONITORING_CONFIG,
        'production_checklist': PRODUCTION_SECURITY_CHECKLIST
    }
    
    return config_map.get(config_name, {})


def validate_production_security() -> dict:
    """
    验证生产环境安全配置 (Validate production security configuration)
    
    Returns:
        dict: 验证结果
    """
    checklist = PRODUCTION_SECURITY_CHECKLIST
    passed_checks = sum(1 for check in checklist.values() if check)
    total_checks = len(checklist)
    
    return {
        'passed': passed_checks,
        'total': total_checks,
        'percentage': (passed_checks / total_checks) * 100,
        'is_secure': passed_checks == total_checks,
        'failed_checks': [name for name, passed in checklist.items() if not passed],
        'details': checklist
    }


def get_security_headers() -> dict:
    """
    获取安全HTTP头部 (Get security HTTP headers)
    
    Returns:
        dict: 安全头部字典
    """
    csp_policy = "; ".join([
        f"{directive} {' '.join(sources)}"
        for directive, sources in CSP_CONFIG.items()
        if directive != 'upgrade_insecure_requests'
    ])
    
    if CSP_CONFIG.get('upgrade_insecure_requests'):
        csp_policy += "; upgrade-insecure-requests"
    
    headers = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Content-Security-Policy': csp_policy,
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains' if not settings.DEBUG else None,
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
    }
    
    # 移除None值 (Remove None values)
    return {k: v for k, v in headers.items() if v is not None}


# 导出配置常量 (Export configuration constants)
__all__ = [
    'RATE_LIMIT_CONFIG',
    'AUDIO_SECURITY_CONFIG', 
    'INPUT_VALIDATION_CONFIG',
    'SECURITY_LOGGING_CONFIG',
    'CSRF_CONFIG',
    'CSP_CONFIG',
    'API_KEY_CONFIG',
    'SESSION_SECURITY_CONFIG',
    'BRUTE_FORCE_CONFIG',
    'ENCRYPTION_CONFIG',
    'MONITORING_CONFIG',
    'PRODUCTION_SECURITY_CHECKLIST',
    'get_security_config',
    'validate_production_security',
    'get_security_headers'
]