"""
生产环境Django设置 (Production Django Settings)
包含所有生产环境所需的安全和性能配置
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# 加载环境变量 (Load environment variables)
load_dotenv(BASE_DIR / '.env.production')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY environment variable is required in production")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# 允许的主机 (Allowed hosts)
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
    raise ValueError("DJANGO_ALLOWED_HOSTS environment variable is required in production")

# 数据库配置 (Database configuration)
# 使用SQLite3作为生产数据库 (Use SQLite3 as production database)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 20,  # 数据库锁定超时时间 (Database lock timeout)
        },
    }
}

# 如果需要使用PostgreSQL，可以通过环境变量启用 (Enable PostgreSQL via environment variable if needed)
if os.environ.get('USE_POSTGRESQL', 'False').lower() == 'true':
    DATABASES = {
        'default': {
            'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.postgresql'),
            'NAME': os.environ.get('DB_NAME'),
            'USER': os.environ.get('DB_USER'),
            'PASSWORD': os.environ.get('DB_PASSWORD'),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'OPTIONS': {
                'sslmode': 'require',
            },
            'CONN_MAX_AGE': 600,  # 连接池
        }
    }

# 缓存配置 (Cache configuration)
# 使用本地内存缓存替代Redis (Use local memory cache instead of Redis)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'tongcove-production-cache',
        'TIMEOUT': 300,  # 5 minutes
        'OPTIONS': {
            'MAX_ENTRIES': 2000,  # 增加缓存条目数量 (Increase cache entries)
        }
    }
}

# 如果需要使用Redis，可以通过环境变量启用 (Enable Redis via environment variable if needed)
if os.environ.get('USE_REDIS', 'False').lower() == 'true':
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'CONNECTION_POOL_KWARGS': {
                    'max_connections': 50,
                    'retry_on_timeout': True,
                }
            },
            'KEY_PREFIX': 'tongcove_prod',
            'TIMEOUT': 300,
        }
    }

# 会话配置 (Session configuration)
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_AGE = 3600  # 1 hour

# CSRF配置 (CSRF configuration)
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')

# 安全设置 (Security settings)
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# 静态文件配置 (Static files configuration)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# 静态文件存储 (Static files storage)
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# 媒体文件配置 (Media files configuration)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 如果使用云存储 (If using cloud storage)
if os.environ.get('USE_S3_STORAGE', 'False').lower() == 'true':
    # AWS S3配置 (AWS S3 configuration)
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'ap-southeast-2')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_DEFAULT_ACL = None
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    
    # 静态文件使用S3 (Static files use S3)
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    
    STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

# 邮件配置 (Email configuration)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

# 日志配置 (Logging configuration)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'security.log'),
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'errors.log'),
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'speak_practice.security': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'speak_practice.security_monitor': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# API密钥配置 (API keys configuration)
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

# 验证必需的API密钥 (Validate required API keys)
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is required")

# 应用程序配置 (Application configuration)
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'accounts',
    'chatbots',
    'dashboard',
    'assignments',
    'stories',
    'pinyinit',
    'typingchinese',
    'namegen',
    'speak_practice',
    'ckeditor_uploader',
    'django_ckeditor_5',
]

# 中间件配置 (Middleware configuration)
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # 静态文件服务
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "namegen.middleware.StatisticsMiddleware",
]

# 模板配置 (Template configuration)
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / 'templates'],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# 国际化配置 (Internationalization configuration)
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get('TIME_ZONE', 'Australia/Perth')
USE_I18N = True
USE_TZ = True

# 认证配置 (Authentication configuration)
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
AUTHENTICATION_BACKENDS = [
    'accounts.backends.CaseInsensitiveModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# 密码验证 (Password validation)
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 12,  # 生产环境更强的密码要求
        }
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# 安全配置 (Security configuration)
CHAT_API_RATE_LIMIT = int(os.environ.get('CHAT_API_RATE_LIMIT', 20))  # 生产环境更严格
AUDIO_API_RATE_LIMIT = int(os.environ.get('AUDIO_API_RATE_LIMIT', 5))
TRANSLATE_API_RATE_LIMIT = int(os.environ.get('TRANSLATE_API_RATE_LIMIT', 10))

AUDIO_MAX_FILE_SIZE = int(os.environ.get('AUDIO_MAX_FILE_SIZE', 5 * 1024 * 1024))  # 5MB
AUDIO_MAX_DURATION = int(os.environ.get('AUDIO_MAX_DURATION', 180))  # 3 minutes
AUDIO_MALWARE_SCAN_ENABLED = True

INPUT_MAX_TEXT_LENGTH = int(os.environ.get('INPUT_MAX_TEXT_LENGTH', 500))  # 更严格的限制
INPUT_STRICT_VALIDATION = True

# 监控和告警配置 (Monitoring and alerting configuration)
SECURITY_ALERT_EMAIL = os.environ.get('SECURITY_ALERT_EMAIL')
SECURITY_ALERT_WEBHOOK = os.environ.get('SECURITY_ALERT_WEBHOOK')
SECURITY_LOG_RATE_LIMITS = True
SECURITY_LOG_MALICIOUS_UPLOADS = True
SECURITY_ALERT_THRESHOLD = int(os.environ.get('SECURITY_ALERT_THRESHOLD', 5))

# 性能配置 (Performance configuration)
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB

# 其他配置 (Other configuration)
ROOT_URLCONF = "tongcove.urls"
WSGI_APPLICATION = "tongcove.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CKEditor配置 (CKEditor configuration)
CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': ['heading', '|', 'bold', 'italic', 'link',
                    'bulletedList', 'numberedList', 'blockQuote'],
        'upload': {
            'types': ['png', 'jpg', 'jpeg', 'gif', 'webp'],
        }
    },
}
CKEDITOR_5_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# 仪表板颜色配置 (Dashboard colors configuration)
DASHBOARD_COLORS = [
    '#99E7C5',
    '#B5B0F6', 
    '#EDA3A3',
    '#F4CB9B'
]

# 确保日志目录存在 (Ensure log directory exists)
log_dir = os.path.join(BASE_DIR, 'logs')
os.makedirs(log_dir, exist_ok=True)

# 生产环境健康检查 (Production health check)
def validate_production_config():
    """验证生产环境配置 (Validate production configuration)"""
    errors = []
    
    if DEBUG:
        errors.append("DEBUG should be False in production")
    
    if not SECRET_KEY or len(SECRET_KEY) < 50:
        errors.append("SECRET_KEY should be at least 50 characters long")
    
    if not ALLOWED_HOSTS:
        errors.append("ALLOWED_HOSTS must be configured")
    
    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY is required")
    
    if not GOOGLE_API_KEY:
        errors.append("GOOGLE_API_KEY is required")
    
    if errors:
        raise ValueError("Production configuration errors:\n" + "\n".join(errors))

# 在导入时验证配置 (Validate configuration on import)
if 'runserver' not in sys.argv and 'migrate' not in sys.argv:
    validate_production_config()