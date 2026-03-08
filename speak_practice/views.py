from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.html import escape
from django.middleware.csrf import get_token
from accounts.models import StudentProfile
from .models import (
    ChatSession,
    ChatMessage,
    PracticeSceneTemplate,
    UserSceneExposure,
    SCENE_SOURCE_CHOICES,
)
from .security import (
    secure_api, 
    AudioSecurityValidator, 
    InputSanitizer, 
    RateLimiter
)
from .security_monitor import log_security_event
import json
import requests
import base64
import os
import logging
import re
import html
import hashlib
import secrets
from datetime import timedelta

# OpenAI & Google Cloud Configuration
OPENAI_API_KEY = settings.OPENAI_API_KEY
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"
OPENAI_REALTIME_CLIENT_SECRET_URL = "https://api.openai.com/v1/realtime/client_secrets"
OPENAI_REALTIME_MODEL = os.getenv('OPENAI_REALTIME_MODEL', 'gpt-realtime')
OPENAI_REALTIME_VOICE = os.getenv('OPENAI_REALTIME_VOICE', 'marin')
# Note: It's better to get the Google API key from settings or environment variables
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_TTS_URL = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_API_KEY}"
logger = logging.getLogger(__name__)


@login_required
def scene_selection(request):
    profile = _get_student_profile(request.user)
    profile_summary = _build_profile_summary(profile)
    active_template_count = PracticeSceneTemplate.objects.filter(is_active=True).count()

    if request.method == 'POST':
        raw_scene = request.POST.get('scene', '')
        scene = InputSanitizer.sanitize_text(raw_scene, 1000, allow_html=False)
        scene_source = request.POST.get('scene_source', 'custom')
        template_id = request.POST.get('scene_template_id')
        template = None

        allowed_sources = {choice[0] for choice in SCENE_SOURCE_CHOICES}
        if scene_source not in allowed_sources:
            scene_source = 'custom'

        if template_id:
            try:
                template = PracticeSceneTemplate.objects.get(id=int(template_id), is_active=True)
                scene = template.scene_prompt
                scene_source = 'template'
            except (PracticeSceneTemplate.DoesNotExist, TypeError, ValueError):
                template = None

        if not scene:
            return redirect('speak_practice:scene_selection')

        scene_signature = _build_scene_signature(scene)
        session = ChatSession.objects.create(
            user=request.user,
            scene=scene,
            scene_template=template,
            scene_source=scene_source,
            scene_signature=scene_signature,
        )
        _record_scene_exposure(
            user=request.user,
            topic={
                'title': template.title if template else request.POST.get('scene_title', '')[:120],
                'scene_text': scene,
                'template_id': template.id if template else None,
                'source': scene_source,
            },
            exposure_type='selected',
            session=session,
        )

        return redirect('speak_practice:chat_view', session_id=session.id)

    # GET请求：不再生成话题，直接渲染页面
    return render(request, 'speak_practice/scene_selection.html', {
        'load_topics_async': True,  # 标记使用异步加载
        'profile_ready': _profile_has_context(profile),
        'profile_summary': profile_summary,
        'active_template_count': active_template_count,
    })


@login_required
def chat_view(request, session_id):
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
        messages = session.messages.order_by('timestamp')
        latest_ai_message = session.messages.filter(sender_type='ai').order_by('-timestamp').first()
        initial_ai_audio = None
        if latest_ai_message:
            initial_ai_audio = latest_ai_message.message_content.get('tts_audio')
        conversation_history = []
        for message in messages:
            payload = message.message_content or {}
            conversation_history.append({
                'sender_type': message.sender_type,
                'text': payload.get('chinese_text') or payload.get('chinese') or '',
                'pinyin': payload.get('pinyin') or '',
                'input_method': message.input_method,
            })
        return render(request, 'speak_practice/chat.html', {
            'session': session,
            'messages': messages,
            'initial_ai_audio': initial_ai_audio,
            'conversation_history': conversation_history,
        })
    except ChatSession.DoesNotExist:
        return redirect('speak_practice:scene_selection')


@secure_api('chat_api', require_auth=True)
@csrf_protect
@require_http_methods(["POST"])
def chat_api(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

    try:
        # 验证请求来源
        if not _validate_request_origin(request):
            return _create_safe_error_response("Invalid request origin", "permission_error", 403)
        
        # 解析和验证JSON数据
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return _create_safe_error_response("Invalid JSON data", "validation_error", 400)
        
        # 验证必需字段
        if not _validate_json_structure(data, ['message', 'session_id']):
            return _create_safe_error_response("Missing required fields", "validation_error", 400)
        
        # 使用增强的输入清理和验证 (Use enhanced input sanitization and validation)
        field_configs = {
            'message': {'max_length': 1000, 'allow_html': False}
        }
        sanitized_data = InputSanitizer.sanitize_json_data(data, field_configs)
        user_message = sanitized_data.get('message', '')
        session_id = data.get('session_id')
        
        # 验证消息内容安全性 (Validate message content security)
        security_check = InputSanitizer.validate_text_content(user_message)
        if not security_check['is_safe']:
            log_security_event('malicious_input_detected', request, {
                'endpoint': 'chat_api',
                'threats': security_check['threats_detected'],
                'risk_level': security_check['risk_level'],
                'input_preview': user_message[:100]
            })
            return _create_safe_error_response("Invalid message content", "security_violation", 400)
        
        if not user_message:
            return _create_safe_error_response("Message cannot be empty", "validation_error", 400)
        
        # 验证session_id格式
        if not isinstance(session_id, int) or session_id <= 0:
            return _create_safe_error_response("Invalid session ID", "validation_error", 400)

        session = ChatSession.objects.get(id=session_id, user=request.user)

        # Create user message
        ChatMessage.objects.create(
            session=session,
            sender_type='user',
            message_content={
                'chinese_text': user_message,
                'english_translation': data.get('english_translation'),
                'input_method': data.get('input_method', 'text'),
            },
            input_method=data.get('input_method', 'text')
        )

        # Check token count before generating AI response
        current_tokens = count_tokens_in_conversation(session_id)
        should_end = should_end_conversation(session_id)
        
        # Build conversation history
        history = list(session.messages.order_by('timestamp').values('sender_type', 'message_content'))
        
        # Enhanced system prompt with token awareness
        base_system_prompt = f"""You are a Chinese language practice partner in this scenario: {session.scene}

RESPONSE FORMAT: Always respond in JSON format with 'chinese' and 'pinyin' fields.

CONVERSATION RULES:
1. Stay in character for the given scenario
2. Keep responses natural and contextually appropriate
3. Ask follow-up questions to maintain conversation flow
4. Provide gentle corrections when needed
5. Use vocabulary appropriate for the scenario difficulty level"""

        if should_end:
            system_prompt = base_system_prompt + """

IMPORTANT: This conversation is approaching the token limit. You should naturally conclude the conversation in your next response. End on a positive note with appropriate closing remarks for the scenario (e.g., "谢谢您光临!" for café, "很高兴认识您!" for introductions, etc.)."""
        else:
            system_prompt = base_system_prompt

        conversation_history = [{"role": "system", "content": system_prompt}]
        
        for msg in history:
            role = "user" if msg['sender_type'] == 'user' else "assistant"
            content = msg['message_content'].get('chinese_text') or msg['message_content'].get('chinese')
            conversation_history.append({"role": role, "content": content})

        # Get AI response
        ai_response_content = get_ai_response(conversation_history)
        if not ai_response_content:
            return JsonResponse({'success': False, 'error': 'Failed to get AI response'}, status=500)

        ai_response_data = json.loads(ai_response_content)
        
        # Create AI message
        ChatMessage.objects.create(session=session, sender_type='ai', message_content=ai_response_data)
        
        # Generate TTS audio using new service
        try:
            from .services.text_to_speech import tts_service
            from .services.exceptions import TTSError, TTSServiceUnavailableError
            
            chinese_text = ai_response_data.get('chinese')
            if chinese_text:
                tts_audio_b64 = tts_service.generate_speech(chinese_text, 'cmn-CN')
            else:
                tts_audio_b64 = None
                
        except (TTSError, TTSServiceUnavailableError) as e:
            # Log TTS error but don't fail the entire request
            logger = logging.getLogger(__name__)
            logger.warning(f"TTS generation failed for user {request.user.id}: {e.message}")
            tts_audio_b64 = None
            
        except Exception as e:
            # Log unexpected TTS errors
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected TTS error for user {request.user.id}: {str(e)}")
            tts_audio_b64 = None

        # Calculate final token count and status
        final_tokens = count_tokens_in_conversation(session_id)
        conversation_ended = should_end_conversation(session_id)
        
        response_data = {
            'success': True,
            'ai_response': ai_response_data,
            'tts_audio': tts_audio_b64,
            'tts_available': tts_audio_b64 is not None,
            'token_info': {
                'current_tokens': final_tokens,
                'max_tokens': 10000,
                'percentage_used': round((final_tokens / 10000) * 100, 1),
                'approaching_limit': final_tokens >= (10000 * 0.8),  # 80% warning
                'conversation_ended': conversation_ended
            }
        }
        
        return JsonResponse(response_data)

    except ChatSession.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@secure_api('transcribe_audio', require_auth=True)
@csrf_protect
@require_http_methods(["POST"])
def transcribe_audio_api(request):
    """
    语音转文本API端点，使用新的语音识别服务
    (Speech-to-text API endpoint using new speech recognition service)
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

    # 验证请求来源 (Validate request origin)
    if not _validate_request_origin(request):
        return _create_safe_error_response("Invalid request origin", "permission_error", 403)
    
    # 获取音频文件并进行安全验证 (Get audio file and perform security validation)
    audio_file = request.FILES.get('audio')
    if not audio_file:
        return _create_safe_error_response("No audio file provided", "validation_error", 400)
    
    # 执行综合音频文件安全验证 (Perform comprehensive audio file security validation)
    validation_result = AudioSecurityValidator.comprehensive_validate(audio_file)
    if not validation_result['is_valid']:
        log_security_event('malicious_audio_upload', request, {
            'endpoint': 'transcribe_audio_api',
            'filename': audio_file.name,
            'file_size': audio_file.size,
            'errors': validation_result['errors'],
            'validation_details': validation_result['validation_details']
        })
        return _create_safe_error_response("Invalid audio file", "audio_security_violation", 400)

    try:
        # 导入服务类 (Import service classes)
        from .services.speech_recognition import SpeechRecognitionService
        from .services.translation import TranslationService
        from .services.exceptions import (
            AudioValidationError, 
            SpeechRecognitionError, 
            TranscriptionTimeoutError,
            TranslationError,
            APIError
        )
        
        # 初始化语音识别服务 (Initialize speech recognition service)
        speech_service = SpeechRecognitionService()
        
        # 转录音频 (Transcribe audio)
        transcription_result = speech_service.process(audio_file)
        chinese_text = transcription_result['transcribed_text']
        
        # 使用增强的文本清理 (Use enhanced text sanitization)
        clean_chinese_text = InputSanitizer.sanitize_text(chinese_text, 1000, allow_html=False)
        
        # 初始化翻译服务并翻译为英文 (Initialize translation service and translate to English)
        translation_service = TranslationService()
        translation_input = {
            'text': clean_chinese_text,
            'source_lang': 'zh',
            'target_lang': 'en'
        }
        
        translation_result = translation_service.process(translation_input)
        english_translation = translation_result['translated_text']
        clean_english_translation = InputSanitizer.sanitize_text(english_translation, 1000, allow_html=False)
        
        # 记录成功的处理 (Log successful processing)
        logger = logging.getLogger(__name__)
        logger.info(f"Audio transcription successful for user {request.user.id}: "
                   f"{len(clean_chinese_text)} chars Chinese, {len(clean_english_translation)} chars English")
        
        return JsonResponse({
            'success': True, 
            'chinese_text': clean_chinese_text, 
            'english_translation': clean_english_translation,
            'audio_info': {
                'duration': transcription_result.get('audio_duration', 0),
                'size': transcription_result.get('audio_size', 0),
                'format': transcription_result.get('audio_format', 'unknown')
            },
            'csrf_token': get_token(request)
        })
        
    except AudioValidationError as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Audio validation error for user {request.user.id}: {e.message}")
        return _create_safe_error_response("Invalid audio file", e.error_code, 400)
        
    except TranscriptionTimeoutError as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Transcription timeout for user {request.user.id}")
        return _create_safe_error_response("Speech recognition timeout", e.error_code, 408)
        
    except SpeechRecognitionError as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Speech recognition error for user {request.user.id}: {e.message}")
        return _create_safe_error_response("Speech recognition failed", e.error_code, 500)
        
    except TranslationError as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Translation error for user {request.user.id}: {e.message}")
        # 如果翻译失败，仍然返回中文文本 (If translation fails, still return Chinese text)
        return JsonResponse({
            'success': True, 
            'chinese_text': clean_chinese_text, 
            'english_translation': "Translation unavailable",
            'translation_error': True,
            'csrf_token': get_token(request)
        })
        
    except APIError as e:
        logger = logging.getLogger(__name__)
        logger.error(f"API error for user {request.user.id}: {e.message}")
        return _create_safe_error_response("Service temporarily unavailable", e.error_code, 503)
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error in transcribe_audio_api for user {request.user.id}: {str(e)}")
        return _create_safe_error_response("Audio processing failed", "server_error", 500)


@secure_api('translate_text', require_auth=True)
@csrf_protect
@require_http_methods(["POST"])
def translate_text_api(request):
    """
    文本翻译API端点，使用新的翻译服务
    (Text translation API endpoint using new translation service)
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

    # 验证请求来源 (Validate request origin)
    if not _validate_request_origin(request):
        return _create_safe_error_response("Invalid request origin", "permission_error", 403)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return _create_safe_error_response("Invalid JSON data", "validation_error", 400)
    
    # 使用增强的输入清理和验证 (Use enhanced input sanitization and validation)
    raw_text = data.get('text', '')
    text = InputSanitizer.sanitize_text(raw_text, 1000, allow_html=False)
    if not text:
        return _create_safe_error_response("No text provided", "validation_error", 400)
    
    # 验证文本内容安全性 (Validate text content security)
    security_check = InputSanitizer.validate_text_content(text)
    if not security_check['is_safe']:
        log_security_event('malicious_input_detected', request, {
            'endpoint': 'translate_text_api',
            'threats': security_check['threats_detected'],
            'risk_level': security_check['risk_level'],
            'input_preview': text[:100]
        })
        return _create_safe_error_response("Invalid text content", "security_violation", 400)

    try:
        # 导入服务类 (Import service classes)
        from .services.translation import TranslationService
        from .services.exceptions import (
            TranslationError,
            TranslationTimeoutError,
            UnsupportedLanguageError,
            APIError
        )
        
        # 初始化翻译服务 (Initialize translation service)
        translation_service = TranslationService()
        
        # 准备翻译输入 (Prepare translation input)
        translation_input = {
            'text': text,
            'source_lang': 'en',
            'target_lang': 'zh'
        }
        
        # 执行翻译 (Execute translation)
        translation_result = translation_service.process(translation_input)
        chinese_text = translation_result['translated_text']
        
        # 使用增强的文本清理 (Use enhanced text sanitization)
        clean_chinese_text = InputSanitizer.sanitize_text(chinese_text, 1000, allow_html=False)
        
        # 生成拼音标注 (Generate pinyin annotation)
        pinyin_text = None
        try:
            from pypinyin import pinyin, Style
            pinyin_list = pinyin(clean_chinese_text, style=Style.TONE, heteronym=False)
            pinyin_text = ' '.join([item[0] for item in pinyin_list])
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Pinyin generation failed for user {request.user.id}: {str(e)}")
            pinyin_text = None
        
        # 生成TTS音频 (Generate TTS audio) using new service
        try:
            from .services.text_to_speech import tts_service
            from .services.exceptions import TTSError, TTSServiceUnavailableError
            
            tts_audio_b64 = tts_service.generate_speech(clean_chinese_text, 'cmn-CN')
            
        except (TTSError, TTSServiceUnavailableError) as e:
            # Log TTS error but don't fail the entire request
            logger = logging.getLogger(__name__)
            logger.warning(f"TTS generation failed for translation API, user {request.user.id}: {e.message}")
            tts_audio_b64 = None
            
        except Exception as e:
            # Log unexpected TTS errors
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected TTS error in translation API for user {request.user.id}: {str(e)}")
            tts_audio_b64 = None
        
        # 记录成功的处理 (Log successful processing)
        logger = logging.getLogger(__name__)
        logger.info(f"Text translation successful for user {request.user.id}: "
                   f"'{text[:50]}...' -> '{clean_chinese_text[:50]}...'")
        
        return JsonResponse({
            'success': True, 
            'chinese_text': clean_chinese_text,
            'pinyin': pinyin_text,
            'tts_audio': tts_audio_b64,
            'tts_available': tts_audio_b64 is not None,
            'translation_info': {
                'source_language': translation_result.get('source_language', 'en'),
                'target_language': translation_result.get('target_language', 'zh'),
                'character_count': translation_result.get('character_count', len(clean_chinese_text))
            },
            'csrf_token': get_token(request)
        })
        
    except UnsupportedLanguageError as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Unsupported language error for user {request.user.id}: {e.message}")
        return _create_safe_error_response("Unsupported language", e.error_code, 400)
        
    except TranslationTimeoutError as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Translation timeout for user {request.user.id}")
        return _create_safe_error_response("Translation timeout", e.error_code, 408)
        
    except TranslationError as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Translation error for user {request.user.id}: {e.message}")
        return _create_safe_error_response("Translation failed", e.error_code, 500)
        
    except APIError as e:
        logger = logging.getLogger(__name__)
        logger.error(f"API error for user {request.user.id}: {e.message}")
        return _create_safe_error_response("Service temporarily unavailable", e.error_code, 503)
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error in translate_text_api for user {request.user.id}: {str(e)}")
        return _create_safe_error_response("Translation failed", "server_error", 500)


@secure_api('translate_chinese', require_auth=True)
@csrf_protect
@require_http_methods(["POST"])
def translate_chinese_api(request):
    """
    中文到英文翻译API端点 (Chinese to English translation API endpoint)
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

    # 验证请求来源 (Validate request origin)
    if not _validate_request_origin(request):
        return _create_safe_error_response("Invalid request origin", "permission_error", 403)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return _create_safe_error_response("Invalid JSON data", "validation_error", 400)
    
    # 使用增强的输入清理和验证 (Use enhanced input sanitization and validation)
    raw_chinese_text = data.get('chinese_text', '')
    chinese_text = InputSanitizer.sanitize_text(raw_chinese_text, 500, allow_html=False)
    if not chinese_text:
        return _create_safe_error_response("No Chinese text provided", "validation_error", 400)
    
    # 验证文本内容安全性 (Validate text content security)
    security_check = InputSanitizer.validate_text_content(chinese_text)
    if not security_check['is_safe']:
        log_security_event('malicious_input_detected', request, {
            'endpoint': 'translate_chinese_api',
            'threats': security_check['threats_detected'],
            'risk_level': security_check['risk_level'],
            'input_preview': chinese_text[:100]
        })
        return _create_safe_error_response("Invalid text content", "security_violation", 400)

    try:
        # 导入服务类 (Import service classes)
        from .services.translation import TranslationService
        from .services.exceptions import (
            TranslationError,
            TranslationTimeoutError,
            UnsupportedLanguageError,
            APIError
        )
        
        # 初始化翻译服务 (Initialize translation service)
        translation_service = TranslationService()
        
        # 准备翻译输入 (Prepare translation input)
        translation_input = {
            'text': chinese_text,
            'source_lang': 'zh',
            'target_lang': 'en'
        }
        
        # 执行翻译 (Perform translation)
        translation_result = translation_service.translate_text(**translation_input)
        
        # 构建响应 (Build response)
        response_data = {
            'success': True,
            'chinese_text': chinese_text,
            'english_translation': translation_result['translated_text'],
            'csrf_token': get_token(request)
        }
        
        return JsonResponse(response_data)
        
    except UnsupportedLanguageError as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Unsupported language in translate_chinese_api for user {request.user.id}: {str(e)}")
        return _create_safe_error_response("Language not supported", "language_error", 400)
        
    except TranslationTimeoutError as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Translation timeout in translate_chinese_api for user {request.user.id}: {str(e)}")
        return _create_safe_error_response("Translation timeout", "timeout_error", 408)
        
    except (TranslationError, APIError) as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Translation service error in translate_chinese_api for user {request.user.id}: {str(e)}")
        return _create_safe_error_response("Translation service error", "service_error", 503)
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error in translate_chinese_api for user {request.user.id}: {str(e)}")
        return _create_safe_error_response("Translation failed", "server_error", 500)


# Security and validation helper functions
def _validate_request_origin(request):
    """验证请求来源，防止CSRF攻击"""
    # 在开发模式下放宽验证
    if settings.DEBUG:
        # 开发模式下，如果是Ajax请求就允许
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return True
    
    referer = request.META.get('HTTP_REFERER')
    if not referer:
        # 在开发模式下，没有referer也允许
        return settings.DEBUG
    
    # 检查referer是否来自允许的域名
    allowed_hosts = settings.ALLOWED_HOSTS + ['127.0.0.1', 'localhost', 'testserver']
    host = request.get_host()
    
    # 简单的referer验证
    for allowed_host in allowed_hosts:
        if allowed_host in referer:
            return True
    
    # 如果是本地开发环境，也允许
    if any(local_host in referer for local_host in ['127.0.0.1', 'localhost']):
        return True
    
    return False


def _sanitize_input(text, max_length=1000):
    """清理和验证用户输入，防止XSS攻击"""
    if not text or not isinstance(text, str):
        return ""
    
    # 限制长度
    text = text[:max_length]
    
    # HTML转义
    text = html.escape(text)
    
    # 移除潜在的恶意脚本标签
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
    
    # 清理多余的空白字符
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def _validate_json_structure(data, required_fields):
    """验证JSON数据结构"""
    if not isinstance(data, dict):
        return False
    
    for field in required_fields:
        if field not in data:
            return False
    
    return True


def _get_student_profile(user):
    profile, _ = StudentProfile.objects.get_or_create(user=user)
    return profile


def _profile_has_context(profile):
    return any([
        bool((profile.learning_goals or '').strip()),
        bool((profile.interests or '').strip()),
        bool((profile.personalised_prompts or '').strip()),
    ])


def _build_profile_summary(profile):
    summary_parts = [f"Level: {profile.get_chinese_level_display()}"]

    if profile.learning_goals:
        summary_parts.append(f"Goals: {profile.learning_goals.strip()}")
    if profile.interests:
        summary_parts.append(f"Background: {profile.interests.strip()}")
    if profile.personalised_prompts:
        summary_parts.append(f"Preferences: {profile.personalised_prompts.strip()}")

    return " | ".join(summary_parts)


def _generate_pinyin_text(chinese_text):
    if not chinese_text:
        return ''

    try:
        from pypinyin import pinyin, Style

        pinyin_list = pinyin(chinese_text, style=Style.TONE, heteronym=False)
        return ' '.join(item[0] for item in pinyin_list if item)
    except Exception as error:
        logger.warning("Pinyin generation failed: %s", error)
        return ''


def _build_scene_signature(scene_text):
    if not scene_text:
        return ""

    normalized = re.sub(r'\s+', ' ', scene_text).strip().lower()
    normalized = re.sub(r'[^a-z0-9\u4e00-\u9fff ]+', '', normalized)
    return hashlib.sha1(normalized.encode('utf-8')).hexdigest()


def _build_recent_context_summary(session, limit=6, max_chars_per_line=220):
    summary_lines = []
    recent_messages = session.messages.order_by('-timestamp')[:limit]

    for message in reversed(recent_messages):
        payload = message.message_content or {}
        text = payload.get('chinese_text') or payload.get('chinese') or ''
        if not text:
            continue
        text = text.strip()
        if len(text) > max_chars_per_line:
            text = text[:max_chars_per_line - 1].rstrip() + '...'
        speaker = 'User' if message.sender_type == 'user' else 'Assistant'
        summary_lines.append(f"{speaker}: {text}")

    return "\n".join(summary_lines)


def _build_realtime_instructions(session, profile):
    profile_lines = []
    if profile:
        if profile.learning_goals:
            profile_lines.append(f"Learning goals: {profile.learning_goals.strip()}")
        if profile.interests:
            profile_lines.append(f"Learner background: {profile.interests.strip()}")
        if profile.personalised_prompts:
            profile_lines.append(f"Conversation preferences: {profile.personalised_prompts.strip()}")
        if profile.preferred_learning_style:
            profile_lines.append(f"Preferred learning style: {profile.preferred_learning_style.strip()}")

    context_summary = _build_recent_context_summary(session)
    opening_rule = (
        "Open the scene with one short, natural Chinese line and then wait for the learner."
        if not session.messages.exists() else
        "Continue naturally from the prior exchange. Do not repeat the opening."
    )

    instruction_sections = [
        "You are a live Chinese speaking coach and scene partner.",
        f"Scene: {session.scene.strip()}",
        opening_rule,
        "Speak primarily in Simplified Chinese.",
        "Keep each reply short, usually 1 or 2 sentences.",
        "Sound natural, warm, and in-character for the scene.",
        "Respond to meaning first and keep the conversation moving.",
        "If the learner makes a noticeable Chinese mistake, give one brief correction naturally inside your reply.",
        "Avoid long English explanations. Use English only if the learner is clearly stuck or explicitly asks for it.",
        "Prefer everyday spoken Chinese over textbook phrasing.",
        "Leave a clear pause after each turn so the learner can answer.",
        "Do not chase or pressure the learner if they stay silent. Wait quietly for their next turn.",
    ]

    if profile_lines:
        instruction_sections.append("Learner context:\n" + "\n".join(profile_lines))
    if context_summary:
        instruction_sections.append("Recent conversation context:\n" + context_summary)

    return "\n\n".join(instruction_sections)


def _build_realtime_session_payload(session, profile):
    return {
        'session': {
            'type': 'realtime',
            'model': OPENAI_REALTIME_MODEL,
            'instructions': _build_realtime_instructions(session, profile),
            'audio': {
                'input': {
                    'turn_detection': None,
                    'transcription': {
                        'model': 'gpt-4o-mini-transcribe',
                    },
                },
                'output': {
                    'voice': OPENAI_REALTIME_VOICE,
                },
            },
        },
    }


def _extract_match_tokens(text):
    if not text:
        return []

    stop_words = {
        'the', 'and', 'for', 'with', 'that', 'this', 'from', 'your', 'about',
        'into', 'have', 'will', 'more', 'slow', 'than', 'you', 'are'
    }
    tokens = re.findall(r'[\u4e00-\u9fff]{1,}|[a-z0-9]+', text.lower())
    return [token for token in tokens if len(token) > 1 and token not in stop_words]


def _get_recent_scene_signatures(user, days=30, limit=30):
    cutoff = timezone.now() - timedelta(days=days)
    recent_session_signatures = list(
        ChatSession.objects.filter(user=user, created_at__gte=cutoff)
        .exclude(scene_signature='')
        .values_list('scene_signature', flat=True)[:limit]
    )
    recent_exposure_signatures = list(
        UserSceneExposure.objects.filter(user=user, created_at__gte=cutoff)
        .exclude(scene_signature='')
        .values_list('scene_signature', flat=True)[:limit]
    )
    return set(recent_session_signatures + recent_exposure_signatures)


def _get_recent_scene_examples(user, days=30, limit=12):
    cutoff = timezone.now() - timedelta(days=days)
    examples = []
    seen_signatures = set()

    exposure_rows = UserSceneExposure.objects.filter(
        user=user,
        created_at__gte=cutoff,
    ).order_by('-created_at').values('scene_signature', 'scene_title', 'scene_text')[:limit * 2]

    session_rows = ChatSession.objects.filter(
        user=user,
        created_at__gte=cutoff,
    ).order_by('-created_at').values('scene_signature', 'scene')[:limit * 2]

    for row in exposure_rows:
        signature = row.get('scene_signature')
        if not signature or signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        title = (row.get('scene_title') or '').strip()
        text = (row.get('scene_text') or '').strip()
        snippet = title or text[:100]
        if snippet:
            examples.append(snippet)
        if len(examples) >= limit:
            return examples

    for row in session_rows:
        signature = row.get('scene_signature')
        if not signature or signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        snippet = (row.get('scene') or '').strip()[:100]
        if snippet:
            examples.append(snippet)
        if len(examples) >= limit:
            break

    return examples


def _coerce_topic_source(source):
    allowed_sources = {choice[0] for choice in SCENE_SOURCE_CHOICES}
    return source if source in allowed_sources else 'custom'


def _build_scene_text_from_topic(topic):
    if not isinstance(topic, dict):
        return ""

    scene_text = topic.get('scene_text')
    if isinstance(scene_text, str) and scene_text.strip():
        return scene_text.strip()

    title = topic.get('title', '').strip()
    description = topic.get('description', '').strip()
    return f"{title}: {description}".strip(': ').strip()


def _serialize_template_topic(template):
    return {
        'title': template.title,
        'description': template.description,
        'level': template.get_level_display(),
        'icon': template.icon or 'fas fa-comments',
        'scene_text': template.scene_prompt,
        'template_id': template.id,
        'source': 'template',
        'category': template.category,
    }


def _prepare_topic_payloads(raw_topics, user, default_source='ai_generated', limit=6, recent_signatures=None):
    recent_signatures = recent_signatures or _get_recent_scene_signatures(user)
    sanitized_topics = _sanitize_topic_data(raw_topics)

    unseen_topics = []
    repeated_topics = []
    seen_in_batch = set()

    for topic in sanitized_topics:
        scene_text = _build_scene_text_from_topic(topic)
        if not scene_text:
            continue

        topic['scene_text'] = scene_text
        topic['source'] = _coerce_topic_source(topic.get('source') or default_source)
        topic['scene_signature'] = _build_scene_signature(scene_text)

        if topic['scene_signature'] in seen_in_batch:
            continue

        seen_in_batch.add(topic['scene_signature'])

        if topic['scene_signature'] in recent_signatures:
            repeated_topics.append(topic)
        else:
            unseen_topics.append(topic)

    return (unseen_topics + repeated_topics)[:limit]


def _merge_topic_lists(primary_topics, secondary_topics, limit=6):
    merged_topics = []
    seen_signatures = set()

    for topic in primary_topics + secondary_topics:
        scene_signature = topic.get('scene_signature')
        if not scene_signature or scene_signature in seen_signatures:
            continue

        merged_topics.append(topic)
        seen_signatures.add(scene_signature)

        if len(merged_topics) >= limit:
            break

    return merged_topics


def _get_template_topics_for_user(user, limit=6, recent_signatures=None):
    templates = list(PracticeSceneTemplate.objects.filter(is_active=True))
    if not templates:
        return []

    recent_signatures = recent_signatures or _get_recent_scene_signatures(user)
    profile = _get_student_profile(user)
    profile_text = " ".join([
        profile.chinese_level or '',
        profile.learning_goals or '',
        profile.interests or '',
        profile.personalised_prompts or '',
    ])
    profile_tokens = _extract_match_tokens(profile_text)

    ranked_templates = []
    for template in templates:
        signature = _build_scene_signature(template.scene_prompt)
        haystack = " ".join([
            template.title,
            template.description,
            template.scene_prompt,
            template.category,
            template.target_profile,
            template.keywords,
        ]).lower()
        token_hits = sum(1 for token in profile_tokens if token in haystack)
        score = token_hits * 2

        if template.level == profile.chinese_level:
            score += 4

        if signature not in recent_signatures:
            score += 6
        else:
            score -= 5

        ranked_templates.append((score, template.sort_order, template.title.lower(), template))

    ranked_templates.sort(key=lambda item: (-item[0], item[1], item[2]))
    serialized_topics = [_serialize_template_topic(item[3]) for item in ranked_templates]
    return _prepare_topic_payloads(serialized_topics, user, default_source='template', limit=limit, recent_signatures=recent_signatures)


def _record_scene_exposures(user, topics, exposure_type='shown', session=None):
    if not topics:
        return

    recent_cutoff = timezone.now() - timedelta(hours=12)
    normalized_topics = []
    signatures = set()
    template_ids = set()

    for topic in topics:
        scene_text = _build_scene_text_from_topic(topic)
        scene_signature = topic.get('scene_signature') or _build_scene_signature(scene_text)
        if not scene_text or not scene_signature:
            continue

        signatures.add(scene_signature)

        template_id = topic.get('template_id')
        if template_id:
            try:
                template_ids.add(int(template_id))
            except (TypeError, ValueError):
                pass

        normalized_topics.append({
            'title': (topic.get('title') or '')[:120],
            'scene_text': scene_text,
            'scene_signature': scene_signature,
            'scene_source': _coerce_topic_source(topic.get('source') or 'custom'),
            'template_id': template_id,
        })

    if not normalized_topics:
        return

    existing_signatures = set()
    if exposure_type == 'shown':
        existing_signatures = set(
            UserSceneExposure.objects.filter(
                user=user,
                exposure_type='shown',
                scene_signature__in=signatures,
                created_at__gte=recent_cutoff,
            ).values_list('scene_signature', flat=True)
        )

    template_map = {
        template.id: template
        for template in PracticeSceneTemplate.objects.filter(id__in=template_ids)
    }

    exposures = []
    for topic in normalized_topics:
        if exposure_type == 'shown' and topic['scene_signature'] in existing_signatures:
            continue

        template = None
        try:
            template = template_map.get(int(topic['template_id'])) if topic['template_id'] else None
        except (TypeError, ValueError):
            template = None

        exposures.append(UserSceneExposure(
            user=user,
            scene_template=template,
            session=session,
            scene_title=topic['title'],
            scene_text=topic['scene_text'],
            scene_signature=topic['scene_signature'],
            scene_source=topic['scene_source'],
            exposure_type=exposure_type,
        ))

    if exposures:
        UserSceneExposure.objects.bulk_create(exposures)


def _record_scene_exposure(user, topic, exposure_type='shown', session=None):
    _record_scene_exposures(user, [topic], exposure_type=exposure_type, session=session)


def _sanitize_topic_data(topics):
    """清理话题数据，防止XSS攻击"""
    if not isinstance(topics, list):
        return []
    
    sanitized_topics = []
    for topic in topics:
        if not isinstance(topic, dict):
            continue
        
        sanitized_topic = {
            'title': _sanitize_input(topic.get('title', ''), 100),
            'description': _sanitize_input(topic.get('description', ''), 500),
            'level': _sanitize_input(topic.get('level', ''), 50),
            'icon': _sanitize_icon_class(topic.get('icon', '')),
            'scene_text': _sanitize_input(topic.get('scene_text', ''), 1000),
            'source': _coerce_topic_source(topic.get('source')),
            'category': _sanitize_input(topic.get('category', ''), 100),
        }

        template_id = topic.get('template_id')
        if isinstance(template_id, int) or (isinstance(template_id, str) and template_id.isdigit()):
            sanitized_topic['template_id'] = int(template_id)
        else:
            sanitized_topic['template_id'] = None
        
        # 验证必需字段不为空
        if sanitized_topic['title'] and sanitized_topic['description'] and sanitized_topic['level'] and sanitized_topic['icon']:
            sanitized_topics.append(sanitized_topic)
    
    return sanitized_topics


def _sanitize_icon_class(icon_class):
    """验证和清理图标类名，只允许Font Awesome图标"""
    if not icon_class or not isinstance(icon_class, str):
        return "fas fa-comment"  # 默认图标
    
    # 只允许Font Awesome图标格式
    if re.match(r'^fas fa-[a-z0-9-]+$', icon_class):
        return icon_class
    
    return "fas fa-comment"  # 默认图标


def _create_safe_error_response(error_message, error_code=None, status=500):
    """创建安全的错误响应，不暴露敏感信息"""
    # 用户友好的错误信息映射
    safe_error_messages = {
        'timeout': 'Service temporarily unavailable. Please try again.',
        'connection_error': 'Unable to connect to service. Please check your connection.',
        'rate_limit': 'Service is busy. Please try again in a moment.',
        'validation_error': 'Invalid data provided.',
        'auth_error': 'Authentication required.',
        'permission_error': 'Access denied.',
        'server_error': 'Internal server error. Please try again.',
        'unknown_error': 'An unexpected error occurred. Please try again.'
    }
    
    # 根据错误代码选择安全的错误信息
    safe_message = safe_error_messages.get(error_code, safe_error_messages['unknown_error'])
    
    # 记录详细错误信息用于调试（不返回给客户端）
    logger = logging.getLogger(__name__)
    logger.error(f"API Error - Code: {error_code}, Message: {error_message}")
    
    return JsonResponse({
        'success': False,
        'error': safe_message,
        'error_code': error_code or 'unknown_error'
    }, status=status)


@secure_api('general', require_auth=True)
@csrf_protect
@require_http_methods(["POST"])
def realtime_session_api(request):
    if not _validate_request_origin(request):
        return _create_safe_error_response("Invalid request origin", "permission_error", 403)

    if not OPENAI_API_KEY:
        return _create_safe_error_response("Realtime service is not configured", "server_error", 503)

    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return _create_safe_error_response("Invalid JSON data", "validation_error", 400)

    session_id = data.get('session_id')
    if not isinstance(session_id, int) or session_id <= 0:
        return _create_safe_error_response("Invalid session ID", "validation_error", 400)

    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return _create_safe_error_response("Session not found", "validation_error", 404)

    profile = _get_student_profile(request.user)
    payload = _build_realtime_session_payload(session, profile)
    headers = {
        'Authorization': f"Bearer {OPENAI_API_KEY}",
        'Content-Type': 'application/json',
    }

    try:
        response = requests.post(
            OPENAI_REALTIME_CLIENT_SECRET_URL,
            headers=headers,
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        realtime_data = response.json()
    except requests.Timeout:
        logger.warning("Realtime client secret request timed out for user %s", request.user.id)
        return _create_safe_error_response("Realtime setup timed out", "timeout", 504)
    except requests.RequestException as error:
        logger.error("Realtime client secret request failed for user %s: %s", request.user.id, error)
        return _create_safe_error_response("Realtime setup failed", "connection_error", 502)

    client_secret = realtime_data.get('client_secret') or {}
    if not client_secret and realtime_data.get('value'):
        client_secret = {
            'value': realtime_data.get('value'),
            'expires_at': realtime_data.get('expires_at'),
        }
    session_data = realtime_data.get('session') or {}
    if not client_secret.get('value'):
        logger.error(
            "Realtime client secret missing value for user %s; response keys=%s",
            request.user.id,
            sorted(realtime_data.keys()),
        )
        return _create_safe_error_response("Realtime setup failed", "server_error", 502)

    return JsonResponse({
        'success': True,
        'client_secret': client_secret,
        'session': session_data,
        'model': session_data.get('model') or OPENAI_REALTIME_MODEL,
        'voice': OPENAI_REALTIME_VOICE,
    })


@secure_api('general', require_auth=True)
@csrf_protect
@require_http_methods(["POST"])
def realtime_message_api(request):
    if not _validate_request_origin(request):
        return _create_safe_error_response("Invalid request origin", "permission_error", 403)

    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return _create_safe_error_response("Invalid JSON data", "validation_error", 400)

    session_id = data.get('session_id')
    sender_type = data.get('sender_type')
    transcript = InputSanitizer.sanitize_text(data.get('transcript', ''), 1000, allow_html=False)
    english_translation = InputSanitizer.sanitize_text(data.get('english_translation', ''), 1000, allow_html=False)
    realtime_item_id = InputSanitizer.sanitize_text(data.get('item_id', ''), 100, allow_html=False)
    input_method = data.get('input_method', 'voice')

    if not isinstance(session_id, int) or session_id <= 0:
        return _create_safe_error_response("Invalid session ID", "validation_error", 400)
    if sender_type not in {'user', 'ai'}:
        return _create_safe_error_response("Invalid sender type", "validation_error", 400)
    if not transcript:
        return _create_safe_error_response("Transcript cannot be empty", "validation_error", 400)

    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return _create_safe_error_response("Session not found", "validation_error", 404)

    existing_message = None
    if realtime_item_id:
        existing_message = ChatMessage.objects.filter(
            session=session,
            sender_type=sender_type,
            message_content__realtime_item_id=realtime_item_id,
        ).first()

    if existing_message:
        existing_payload = existing_message.message_content or {}
        return JsonResponse({
            'success': True,
            'duplicate': True,
            'message_id': existing_message.id,
            'message': {
                'sender_type': sender_type,
                'text': existing_payload.get('chinese_text') or existing_payload.get('chinese') or transcript,
                'pinyin': existing_payload.get('pinyin') or '',
            },
        })

    message_content = {
        'realtime_item_id': realtime_item_id,
        'realtime_source': InputSanitizer.sanitize_text(data.get('source', 'realtime'), 40, allow_html=False) or 'realtime',
    }

    if sender_type == 'ai':
        message_content.update({
            'chinese': transcript,
            'pinyin': _generate_pinyin_text(transcript),
        })
        normalized_input_method = 'voice'
    else:
        message_content.update({
            'chinese_text': transcript,
            'english_translation': english_translation or None,
        })
        normalized_input_method = input_method if input_method in {'voice', 'text', 'translation'} else 'voice'

    message = ChatMessage.objects.create(
        session=session,
        sender_type=sender_type,
        message_content=message_content,
        input_method=normalized_input_method,
    )

    return JsonResponse({
        'success': True,
        'duplicate': False,
        'message_id': message.id,
        'message': {
            'sender_type': sender_type,
            'text': message_content.get('chinese_text') or message_content.get('chinese') or transcript,
            'pinyin': message_content.get('pinyin') or '',
        },
    })


@secure_api('general', require_auth=True)
@csrf_protect
@require_http_methods(["POST"])
def reply_suggestion_api(request):
    if not _validate_request_origin(request):
        return _create_safe_error_response("Invalid request origin", "permission_error", 403)

    if not OPENAI_API_KEY:
        return _create_safe_error_response("Suggestion service is not configured", "server_error", 503)

    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return _create_safe_error_response("Invalid JSON data", "validation_error", 400)

    session_id = data.get('session_id')
    latest_ai_line = InputSanitizer.sanitize_text(data.get('latest_ai_line', ''), 500, allow_html=False)

    if not isinstance(session_id, int) or session_id <= 0:
        return _create_safe_error_response("Invalid session ID", "validation_error", 400)

    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return _create_safe_error_response("Session not found", "validation_error", 404)

    suggestion = _generate_reply_suggestion(session, latest_ai_line=latest_ai_line)
    if not suggestion:
        return JsonResponse({
            'success': False,
            'error': 'Suggestion unavailable',
            'error_code': 'server_error',
        }, status=200)

    return JsonResponse({
        'success': True,
        'suggestion': suggestion,
        'tts_audio': _generate_tts_audio_b64(suggestion['chinese']),
    })


# Helper functions
def get_ai_response(conversation_history, model="gpt-4o"):
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": conversation_history, "response_format": {"type": "json_object"}}
    try:
        response = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except (requests.RequestException, KeyError, IndexError) as e:
        print(f"Error in get_ai_response: {e}")
        return None


def _generate_reply_suggestion(session, latest_ai_line=''):
    recent_context = _build_recent_context_summary(session)
    learner_level = ''
    try:
        profile = _get_student_profile(session.user)
        learner_level = profile.get_chinese_level_display()
    except Exception:
        learner_level = ''

    system_prompt = """You help a Chinese learner continue a live speaking practice conversation.

Return JSON with this exact schema:
{
  "suggestion": "one short natural Chinese reply the learner can say next",
  "tip": "a very short English tip for how to say it"
}

Rules:
- The suggestion must be in Simplified Chinese.
- Keep it short and speakable, usually 1 sentence and under 18 Chinese characters.
- Make it directly answer the assistant's latest line.
- Sound natural for spoken conversation, not textbook-like.
- Do not include pinyin, markdown, numbering, or explanation.
- The tip must be short, practical, and in English."""

    user_prompt_parts = [
        f"Scene: {session.scene.strip()}",
    ]
    if learner_level:
        user_prompt_parts.append(f"Learner level: {learner_level}")
    if recent_context:
        user_prompt_parts.append(f"Recent conversation:\n{recent_context}")
    if latest_ai_line:
        user_prompt_parts.append(f"Assistant's latest line:\n{latest_ai_line.strip()}")
    user_prompt_parts.append("Generate one suggested learner reply for the next turn.")

    response_text = get_ai_response([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "\n\n".join(user_prompt_parts)},
    ], model="gpt-4o-mini")
    if not response_text:
        return None

    try:
        suggestion_data = json.loads(response_text)
    except json.JSONDecodeError:
        logger.warning("Reply suggestion JSON decode failed")
        return None

    suggestion_text = InputSanitizer.sanitize_text(
        suggestion_data.get('suggestion', ''),
        120,
        allow_html=False,
    )
    tip_text = InputSanitizer.sanitize_text(
        suggestion_data.get('tip', ''),
        120,
        allow_html=False,
    )
    if not suggestion_text:
        return None

    return {
        'chinese': suggestion_text,
        'pinyin': _generate_pinyin_text(suggestion_text),
        'tip': tip_text,
    }


def _generate_tts_audio_b64(chinese_text):
    if not chinese_text:
        return None

    try:
        from .services.text_to_speech import tts_service
        from .services.exceptions import TTSError, TTSServiceUnavailableError

        return tts_service.generate_speech(chinese_text, 'cmn-CN')
    except (TTSError, TTSServiceUnavailableError) as error:
        logger.warning("Suggestion TTS generation failed: %s", getattr(error, 'message', str(error)))
        return None
    except Exception as error:
        logger.error("Unexpected suggestion TTS error: %s", error)
        return None

def get_initial_ai_message(scene):
    system_prompt = """You are a Chinese language practice partner. You will have conversations in Chinese to help users practice the language.

IMPORTANT RULES:
1. Your response must be in JSON format containing 'chinese' and 'pinyin'
2. Keep conversations natural and engaging
3. Ask follow-up questions to maintain the conversation flow
4. Correct pronunciation or grammar gently when appropriate
5. Use vocabulary appropriate for the scenario difficulty level

SCENARIO CONTEXT: Based on the user's chosen scene, act as an appropriate character (e.g., barista, friend, colleague, etc.) and start the conversation naturally."""
    
    user_prompt = f"The conversation scenario is: {scene}. Please start this conversation with a friendly, contextually appropriate opening in Chinese. Consider who you are in this scenario and begin naturally."
    return get_ai_response([{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}])

def get_tts_audio(text):
    payload = {
        'input': {'text': text},
        'voice': {'languageCode': 'cmn-CN', 'ssmlGender': 'NEUTRAL'},
        'audioConfig': {'audioEncoding': 'MP3'},
    }
    try:
        response = requests.post(GOOGLE_TTS_URL, json=payload, timeout=15)
        response.raise_for_status()
        return response.json().get('audioContent')
    except requests.RequestException as e:
        print(f"Error in get_tts_audio: {e}")
        return None

def transcribe_audio(audio_file):
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    files = {'file': (audio_file.name, audio_file.read(), audio_file.content_type)}
    data = {'model': 'whisper-1', 'language': 'zh'}
    try:
        response = requests.post(OPENAI_WHISPER_URL, headers=headers, files=files, data=data, timeout=20)
        response.raise_for_status()
        return response.json().get('text')
    except requests.RequestException as e:
        print(f"Error in transcribe_audio: {e}")
        return None

def translate_text_openai(text, target_language="en"):
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    messages = [
        {"role": "system", "content": f"Translate the following text to {target_language}."},
        {"role": "user", "content": text}
    ]
    payload = {"model": "gpt-4o", "messages": messages}
    try:
        response = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except (requests.RequestException, KeyError, IndexError) as e:
        print(f"Error in translate_text_openai: {e}")
        return None


def generate_dynamic_topic_cards(user=None, recent_examples=None, batch_size=10):
    """Generate 6 dynamic topic cards using AI for the scene selection page"""
    import random
    
    # 检查API密钥是否配置
    if not OPENAI_API_KEY:
        print("Warning: OPENAI_API_KEY not configured, using fallback topics")
        raise ValueError("OpenAI API key not configured")
    
    # 检查API密钥格式
    if not OPENAI_API_KEY.startswith('sk-'):
        print("Warning: Invalid OpenAI API key format, using fallback topics")
        raise ValueError("Invalid OpenAI API key format")
    
    batch_size = max(6, min(int(batch_size or 10), 12))
    random_seed = secrets.randbelow(1_000_000)
    recent_examples = recent_examples or (_get_recent_scene_examples(user) if user else [])
    recent_block = ""
    if recent_examples:
        recent_list = "\n".join(f"- {example}" for example in recent_examples[:12])
        recent_block = f"""

Avoid generating topics that are too similar to these recently shown or selected scenes:
{recent_list}
"""
    
    system_prompt = f"""You are a Chinese language learning assistant. Generate {batch_size} diverse and practical conversation scenarios for Chinese language practice.

IMPORTANT: Be creative and generate different scenarios each time. Current randomness seed: {random_seed}

Your response must be a JSON array with exactly {batch_size} objects, each containing:
{{
    "title": "Short catchy title (2-4 words)",
    "description": "Detailed scenario description for practice",
    "level": "Beginner|Intermediate|Advanced",
    "icon": "fas fa-[icon-name]" (Font Awesome icon class),
    "scene_text": "One sentence describing the exact roleplay setup"
}}

Make scenarios diverse across these categories:
- Daily life situations (shopping, dining, transport)
- Social interactions (meeting people, small talk)
- Professional contexts (work, business)
- Cultural experiences (festivals, traditions)
- Problem-solving scenarios (asking for help, complaints)
- Educational contexts (school, learning)

Ensure variety in difficulty levels and make each scenario unique and engaging.
Use noticeably different settings, roles, and communicative goals across the list.{recent_block}"""

    try:
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        messages = [{"role": "system", "content": system_prompt}]
        payload = {
            "model": "gpt-4o-mini",  # 使用4o-mini优化成本和速度
            "messages": messages, 
            "temperature": 1.15,
            "top_p": 0.95,
            "presence_penalty": 0.9,
            "frequency_penalty": 0.55
        }
        
        print(f"Making OpenAI API request to: {OPENAI_API_URL}")
        response = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=30)
        print(f"OpenAI API response status: {response.status_code}")
        response.raise_for_status()
        
        ai_response = response.json()['choices'][0]['message']['content']
        print(f"AI Response: {ai_response}")  # Debug log
        
        # 清理AI响应，移除可能的markdown格式
        cleaned_response = ai_response.strip()
        if cleaned_response.startswith('```json'):
            cleaned_response = cleaned_response[7:]  # 移除 ```json
        if cleaned_response.endswith('```'):
            cleaned_response = cleaned_response[:-3]  # 移除 ```
        cleaned_response = cleaned_response.strip()
        
        topics = json.loads(cleaned_response)
        
        # Validate the response structure
        if isinstance(topics, list) and len(topics) >= 6:
            for topic in topics:
                if not all(key in topic for key in ['title', 'description', 'level', 'icon']):
                    raise ValueError("Invalid topic structure")
            print("Successfully generated AI topics")  # Debug log
            return topics
        else:
            raise ValueError("Invalid response format")
            
    except requests.exceptions.HTTPError as e:
        if hasattr(e, 'response') and e.response.status_code == 401:
            print("Error: Invalid OpenAI API key - falling back to static topics")
        elif hasattr(e, 'response') and e.response.status_code == 429:
            print("Error: OpenAI API rate limit exceeded - falling back to static topics")
        else:
            print(f"Error: OpenAI API HTTP error - falling back to static topics")
        return get_fallback_topics()
    except (requests.RequestException, json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Error generating dynamic topics: {e}")
        print("Falling back to randomised static topics")  # Debug log
        
        # 返回静态备用话题
        return get_fallback_topics()


def get_fallback_topics():
    """获取静态备用话题列表 - 增强版本包含更多多样化的话题"""
    import random
    
    # 扩展的静态备用话题池，按难度级别分类
    beginner_topics = [
        {"title": "Café Chat", "description": "Ordering coffee and pastries at a local café", "level": "Beginner", "icon": "fas fa-coffee"},
        {"title": "Finding Places", "description": "Asking for directions to popular tourist attractions", "level": "Beginner", "icon": "fas fa-map-marked-alt"},
        {"title": "Weather Talk", "description": "Discussing today's weather and weekend plans", "level": "Beginner", "icon": "fas fa-cloud-sun"},
        {"title": "Hotel Check-in", "description": "Checking into a hotel and asking about facilities", "level": "Beginner", "icon": "fas fa-bed"},
        {"title": "Shopping Basic", "description": "Buying clothes and asking about sizes and prices", "level": "Beginner", "icon": "fas fa-shopping-cart"},
        {"title": "Transport Help", "description": "Asking about bus routes and train schedules", "level": "Beginner", "icon": "fas fa-bus"},
        {"title": "Greeting Friends", "description": "Meeting friends and making small talk", "level": "Beginner", "icon": "fas fa-users"},
        {"title": "Library Visit", "description": "Finding books and asking about library services", "level": "Beginner", "icon": "fas fa-book"}
    ]
    
    intermediate_topics = [
        {"title": "Work Intro", "description": "Introducing yourself and background to new colleagues", "level": "Intermediate", "icon": "fas fa-handshake"},
        {"title": "Market Deals", "description": "Bargaining for souvenirs at a traditional market", "level": "Intermediate", "icon": "fas fa-shopping-bag"},
        {"title": "Food Ordering", "description": "Ordering traditional Chinese dishes at a restaurant", "level": "Intermediate", "icon": "fas fa-utensils"},
        {"title": "Bank Visit", "description": "Opening a bank account and asking about services", "level": "Intermediate", "icon": "fas fa-university"},
        {"title": "Phone Call", "description": "Making a phone call to book an appointment", "level": "Intermediate", "icon": "fas fa-phone"},
        {"title": "Apartment Hunt", "description": "Inquiring about rental properties and lease terms", "level": "Intermediate", "icon": "fas fa-home"},
        {"title": "School Enrollment", "description": "Registering for classes and discussing course options", "level": "Intermediate", "icon": "fas fa-graduation-cap"},
        {"title": "Health Check", "description": "Scheduling a medical appointment and describing symptoms", "level": "Intermediate", "icon": "fas fa-stethoscope"}
    ]
    
    advanced_topics = [
        {"title": "Doctor Visit", "description": "Explaining symptoms to a doctor during a consultation", "level": "Advanced", "icon": "fas fa-user-md"},
        {"title": "Job Interview", "description": "Participating in a job interview for a local company", "level": "Advanced", "icon": "fas fa-briefcase"},
        {"title": "Emergency Help", "description": "Asking for help in an emergency situation", "level": "Advanced", "icon": "fas fa-exclamation-triangle"},
        {"title": "Legal Advice", "description": "Consulting with a lawyer about legal matters", "level": "Advanced", "icon": "fas fa-gavel"},
        {"title": "Business Meeting", "description": "Participating in a formal business discussion", "level": "Advanced", "icon": "fas fa-handshake"},
        {"title": "Insurance Claim", "description": "Filing an insurance claim and explaining the situation", "level": "Advanced", "icon": "fas fa-shield-alt"},
        {"title": "Tax Consultation", "description": "Discussing tax matters with an accountant", "level": "Advanced", "icon": "fas fa-calculator"},
        {"title": "Property Purchase", "description": "Negotiating a real estate transaction", "level": "Advanced", "icon": "fas fa-key"}
    ]
    
    # 合并所有话题
    all_topics = beginner_topics + intermediate_topics + advanced_topics
    
    # 确保选择的话题有适当的难度分布
    try:
        # 尝试选择2个初级、2个中级、2个高级话题
        selected_topics = []
        selected_topics.extend(random.sample(beginner_topics, min(2, len(beginner_topics))))
        selected_topics.extend(random.sample(intermediate_topics, min(2, len(intermediate_topics))))
        selected_topics.extend(random.sample(advanced_topics, min(2, len(advanced_topics))))
        
        # 如果不足6个，从剩余话题中随机选择
        if len(selected_topics) < 6:
            remaining_topics = [t for t in all_topics if t not in selected_topics]
            needed = 6 - len(selected_topics)
            selected_topics.extend(random.sample(remaining_topics, min(needed, len(remaining_topics))))
        
        # 随机打乱顺序
        random.shuffle(selected_topics)
        return selected_topics[:6]
        
    except (ValueError, IndexError):
        # 如果出现任何错误，回退到简单的随机选择
        return random.sample(all_topics, min(6, len(all_topics)))


def count_tokens_in_conversation(session_id):
    """Count approximate tokens in a conversation session"""
    session = ChatSession.objects.get(id=session_id)
    messages = ChatMessage.objects.filter(session=session).order_by('created_at')
    
    total_tokens = 0
    for message in messages:
        if message.sender_type == 'user':
            # For user messages, count the text length
            content = message.message_content
            if isinstance(content, dict) and 'text' in content:
                text = content['text']
            elif isinstance(content, str):
                text = content
            else:
                text = str(content)
            # Rough estimate: 1 token ≈ 4 characters for Chinese text
            total_tokens += len(text) // 3
        else:
            # For AI messages, count Chinese text
            content = message.message_content
            if isinstance(content, dict):
                chinese_text = content.get('chinese', '')
                # Rough estimate: 1 token ≈ 2-3 characters for Chinese text
                total_tokens += len(chinese_text) // 2
            elif isinstance(content, str):
                total_tokens += len(content) // 2
    
    # Add system prompt tokens (estimated)
    total_tokens += 200
    
    return total_tokens


def should_end_conversation(session_id, max_tokens=10000):
    """Check if conversation should end due to token limit"""
    current_tokens = count_tokens_in_conversation(session_id)
    return current_tokens >= (max_tokens * 0.9)  # 90% threshold


@csrf_protect
@login_required
@require_http_methods(["GET"])
def load_topics_api(request):
    """异步加载AI生成的话题卡片，包含完整的错误处理和降级策略"""
    
    # 验证请求来源
    if not _validate_request_origin(request):
        logger = logging.getLogger(__name__)
        logger.warning(f"Invalid request origin from user {request.user.id}: {request.META.get('HTTP_REFERER', 'No referer')}")
        return JsonResponse({'error': 'Invalid request origin'}, status=403)
    
    import logging
    logger = logging.getLogger(__name__)
    profile = _get_student_profile(request.user)
    recent_signatures = _get_recent_scene_signatures(request.user)
    recent_examples = _get_recent_scene_examples(request.user)
    
    try:
        template_topics = _get_template_topics_for_user(
            request.user,
            limit=6,
            recent_signatures=recent_signatures,
        )

        topics = list(template_topics)
        response_source = 'template_library' if topics else 'ai_generated'

        # 尝试生成动态话题，最多多轮补齐，降低重复概率
        generation_attempt = 0
        while len(topics) < 6 and generation_attempt < 3:
            generation_attempt += 1
            raw_topics = generate_dynamic_topic_cards(
                user=request.user,
                recent_examples=recent_examples,
                batch_size=10,
            )

            if not raw_topics or not isinstance(raw_topics, list) or len(raw_topics) == 0:
                raise ValueError("Generated topics are empty or invalid")

            ai_topics = _prepare_topic_payloads(
                raw_topics,
                request.user,
                default_source='ai_generated',
                limit=10,
                recent_signatures=recent_signatures,
            )
            topics = _merge_topic_lists(topics, ai_topics, limit=6)

            if template_topics and ai_topics:
                response_source = 'mixed'

            if len(topics) < 6:
                recent_examples = recent_examples + [
                    topic.get('title') or topic.get('description') or ''
                    for topic in topics
                ]

        if len(topics) == 0:
            raise ValueError("No valid topics after filtering")

        _record_scene_exposures(request.user, topics, exposure_type='shown')
        
        logger.info(f"Successfully generated and sanitized {len(topics)} AI topics")
        
        return JsonResponse({
            'success': True,
            'topics': topics,
            'source': response_source,
            'generated_at': timezone.now().isoformat(),
            'profile_ready': _profile_has_context(profile),
            'profile_summary': _build_profile_summary(profile),
            'template_library_count': PracticeSceneTemplate.objects.filter(is_active=True).count(),
            'csrf_token': get_token(request)  # 提供新的CSRF令牌
        })
        
    except requests.exceptions.Timeout as e:
        logger.warning(f"AI API timeout: {e}")
        return _handle_api_fallback(request, 'timeout', 'AI service timeout - using backup topics')
        
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"AI API connection error: {e}")
        return _handle_api_fallback(request, 'connection_error', 'Connection to AI service failed - using backup topics')
        
    except requests.exceptions.HTTPError as e:
        logger.warning(f"AI API HTTP error: {e}")
        if hasattr(e, 'response') and e.response.status_code == 429:
            return _handle_api_fallback(request, 'rate_limit', 'AI service rate limit exceeded - using backup topics')
        else:
            return _handle_api_fallback(request, 'http_error', f'AI service error ({e.response.status_code if hasattr(e, "response") else "unknown"}) - using backup topics')
    
    except json.JSONDecodeError as e:
        logger.warning(f"AI API response parsing error: {e}")
        return _handle_api_fallback(request, 'parse_error', 'AI service returned invalid data - using backup topics')
        
    except ValueError as e:
        logger.warning(f"AI API data validation error: {e}")
        return _handle_api_fallback(request, 'validation_error', 'AI service returned incomplete data - using backup topics')
        
    except Exception as e:
        logger.error(f"Unexpected error in load_topics_api: {e}")
        return _handle_api_fallback(request, 'unexpected_error', 'Unexpected error occurred - using backup topics')


def _handle_api_fallback(request, error_type, error_message):
    """处理API失败的统一降级逻辑，包含安全措施"""
    import logging
    logger = logging.getLogger(__name__)
    profile = _get_student_profile(request.user)
    recent_signatures = _get_recent_scene_signatures(request.user)
    
    try:
        template_topics = _get_template_topics_for_user(
            request.user,
            limit=6,
            recent_signatures=recent_signatures,
        )

        # 获取静态备用话题
        raw_fallback_topics = get_fallback_topics()
        
        fallback_topics = _prepare_topic_payloads(
            raw_fallback_topics,
            request.user,
            default_source='fallback',
            limit=6,
            recent_signatures=recent_signatures,
        )
        fallback_topics = _merge_topic_lists(template_topics, fallback_topics, limit=6)
        
        if len(fallback_topics) == 0:
            raise ValueError("No valid fallback topics after sanitization")

        _record_scene_exposures(request.user, fallback_topics, exposure_type='shown')
        
        logger.info(f"Using fallback topics due to {error_type}")
        
        # 返回成功响应，但标记为降级模式
        return JsonResponse({
            'success': True,  # 对前端来说这仍然是成功的
            'topics': fallback_topics,
            'source': 'fallback',
            'fallback_reason': error_type,
            'message': _sanitize_input(error_message, 200),  # 清理错误信息
            'generated_at': timezone.now().isoformat(),
            'profile_ready': _profile_has_context(profile),
            'profile_summary': _build_profile_summary(profile),
            'template_library_count': PracticeSceneTemplate.objects.filter(is_active=True).count(),
            'csrf_token': get_token(request)  # 提供新的CSRF令牌
        })
        
    except Exception as fallback_error:
        logger.error(f"Even fallback topics failed: {fallback_error}")
        
        # 最后的降级：硬编码的最小话题集
        emergency_topics = [
            {"title": "Café Chat", "description": "Ordering coffee and pastries at a local café", "level": "Beginner", "icon": "fas fa-coffee"},
            {"title": "Finding Places", "description": "Asking for directions to popular tourist attractions", "level": "Beginner", "icon": "fas fa-map-marked-alt"},
            {"title": "Weather Talk", "description": "Discussing today's weather and weekend plans", "level": "Beginner", "icon": "fas fa-cloud-sun"},
            {"title": "Work Intro", "description": "Introducing yourself and background to new colleagues", "level": "Intermediate", "icon": "fas fa-handshake"},
            {"title": "Food Ordering", "description": "Ordering traditional Chinese dishes at a restaurant", "level": "Intermediate", "icon": "fas fa-utensils"},
            {"title": "Emergency Help", "description": "Asking for help in an emergency situation", "level": "Advanced", "icon": "fas fa-exclamation-triangle"}
        ]
        
        # 清理紧急话题数据
        safe_emergency_topics = _prepare_topic_payloads(
            emergency_topics,
            request.user,
            default_source='emergency_fallback',
            limit=6,
            recent_signatures=recent_signatures,
        )
        _record_scene_exposures(request.user, safe_emergency_topics, exposure_type='shown')
        
        return JsonResponse({
            'success': True,
            'topics': safe_emergency_topics,
            'source': 'emergency_fallback',
            'fallback_reason': 'complete_system_failure',
            'message': 'Using emergency backup topics',
            'generated_at': timezone.now().isoformat(),
            'profile_ready': _profile_has_context(profile),
            'profile_summary': _build_profile_summary(profile),
            'template_library_count': PracticeSceneTemplate.objects.filter(is_active=True).count(),
            'csrf_token': get_token(request)
        })


@csrf_protect
@login_required
@require_http_methods(["POST"])
def generate_scene_api(request):
    """API for generating AI-powered conversation scenarios"""
    
    try:
        # 验证请求来源
        if not _validate_request_origin(request):
            return _create_safe_error_response("Invalid request origin", "permission_error", 403)
        
        # 解析和验证JSON数据
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return _create_safe_error_response("Invalid JSON data", "validation_error", 400)
        
        # 清理和验证用户输入
        user_input = _sanitize_input(data.get('user_input', ''), 500)
        
        if not user_input:
            return _create_safe_error_response("User input is required", "validation_error", 400)
        
        recent_examples = _get_recent_scene_examples(request.user, limit=8)
        recent_block = ""
        if recent_examples:
            recent_block = "\nAvoid ideas that are too similar to these recent scenes:\n" + "\n".join(
                f"- {example}" for example in recent_examples
            )

        random_seed = secrets.randbelow(1_000_000)

        # Create AI prompt for scene generation
        system_prompt = f"""You are a Chinese language learning assistant. Generate creative and practical conversation scenarios for Chinese language practice based on user input.

Your response should be a JSON object with the following structure:
{{
    "scenarios": [
        {{
            "title": "Short descriptive title",
            "description": "Detailed scenario description",
            "level": "Beginner|Intermediate|Advanced",
            "context": "Additional context or setting details"
        }}
    ]
}}

Generate 3-5 diverse scenarios that are:
1. Practical and relevant to real-life situations
2. Appropriate for Chinese language learning
3. Varied in difficulty levels
4. Culturally authentic
5. Distinct from one another

Randomness seed: {random_seed}.{recent_block}"""
        
        user_prompt = f"Generate Chinese conversation practice scenarios based on this input: {user_input}"
        
        # Call OpenAI API
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        payload = {
            "model": "gpt-4o-mini",
            "messages": messages,
            "temperature": 1.05,
            "top_p": 0.95,
            "presence_penalty": 0.8,
            "frequency_penalty": 0.45,
        }
        
        response = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        ai_response = response.json()['choices'][0]['message']['content']
        
        # Parse the AI response as JSON
        try:
            scenarios_data = json.loads(ai_response)
            return JsonResponse(scenarios_data)
        except json.JSONDecodeError:
            # If AI doesn't return valid JSON, create a fallback response
            return JsonResponse({
                'scenarios': [{
                    'title': 'Custom Scenario',
                    'description': ai_response,
                    'level': 'Intermediate',
                    'context': 'AI-generated scenario'
                }]
            })
        
    except requests.RequestException as e:
        print(f"Error calling OpenAI API: {e}")
        return JsonResponse({'error': 'Failed to generate scenarios'}, status=500)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request'}, status=400)
    except Exception as e:
        print(f"Unexpected error in generate_scene_api: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_protect
@login_required
@require_http_methods(["POST"])
def restart_session_api(request):
    """
    重启对话会话API端点 (Restart conversation session API endpoint)
    清除当前会话的所有消息并生成新的开场白
    """
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        skip_opening_message = bool(data.get('skip_opening_message'))
        
        if not session_id:
            return JsonResponse({
                'success': False,
                'error': 'Session ID is required'
            }, status=400)
        
        # 验证会话是否存在且属于当前用户 (Verify session exists and belongs to current user)
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Session not found or access denied'
            }, status=404)
        
        # 删除会话中的所有消息 (Delete all messages in the session)
        ChatMessage.objects.filter(session=session).delete()

        if skip_opening_message:
            return JsonResponse({
                'success': True,
                'message': 'Conversation cleared successfully'
            })

        # 生成新的开场白 (Generate new opening message)
        initial_ai_message_content = get_initial_ai_message(session.scene)
        
        if initial_ai_message_content:
            try:
                message_data = json.loads(initial_ai_message_content)
                
                # 创建新的AI开场消息 (Create new AI opening message)
                if message_data.get('chinese'):
                    message_data['tts_audio'] = get_tts_audio(message_data['chinese'])
                ChatMessage.objects.create(
                    session=session,
                    sender_type='ai',
                    message_content=message_data
                )
                
                # 生成TTS音频 (Generate TTS audio)
                tts_audio = message_data.get('tts_audio')
                
                return JsonResponse({
                    'success': True,
                    'opening_message': {
                        'chinese': message_data.get('chinese', ''),
                        'pinyin': message_data.get('pinyin', ''),
                        'tts_audio': tts_audio
                    },
                    'message': 'Conversation restarted successfully'
                })
                
            except json.JSONDecodeError:
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to parse AI response'
                }, status=500)
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to generate opening message'
            }, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logging.error(f"Error in restart_session_api: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)
