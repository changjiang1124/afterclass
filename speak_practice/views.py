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
from .models import ChatSession, ChatMessage
import json
import requests
import base64
import os
import logging
import re
import html

# OpenAI & Google Cloud Configuration
OPENAI_API_KEY = settings.OPENAI_API_KEY
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"
# Note: It's better to get the Google API key from settings or environment variables
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_TTS_URL = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_API_KEY}"


@login_required
def scene_selection(request):
    if request.method == 'POST':
        # 保持现有POST逻辑不变
        scene = request.POST.get('scene')
        if not scene:
            return redirect('speak_practice:scene_selection')

        session = ChatSession.objects.create(user=request.user, scene=scene)
        
        # Start the conversation with an initial message from the AI
        initial_ai_message_content = get_initial_ai_message(scene)
        if initial_ai_message_content:
            ChatMessage.objects.create(
                session=session,
                sender_type='ai',
                message_content=json.loads(initial_ai_message_content)
            )

        return redirect('speak_practice:chat_view', session_id=session.id)

    # GET请求：不再生成话题，直接渲染页面
    return render(request, 'speak_practice/scene_selection.html', {
        'load_topics_async': True  # 标记使用异步加载
    })


@login_required
def chat_view(request, session_id):
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
        messages = session.messages.order_by('timestamp')
        return render(request, 'speak_practice/chat.html', {'session': session, 'messages': messages})
    except ChatSession.DoesNotExist:
        return redirect('speak_practice:scene_selection')


@csrf_protect
@login_required
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
        
        # 清理和验证输入
        user_message = _sanitize_input(data.get('message'), 1000)
        session_id = data.get('session_id')
        
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
            message_content={'chinese_text': user_message}
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


@csrf_protect
@login_required
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
    
    # 获取音频文件 (Get audio file)
    audio_file = request.FILES.get('audio')
    if not audio_file:
        return _create_safe_error_response("No audio file provided", "validation_error", 400)

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
        
        # 清理转录文本 (Clean transcribed text)
        clean_chinese_text = _sanitize_input(chinese_text, 1000)
        
        # 初始化翻译服务并翻译为英文 (Initialize translation service and translate to English)
        translation_service = TranslationService()
        translation_input = {
            'text': clean_chinese_text,
            'source_lang': 'zh',
            'target_lang': 'en'
        }
        
        translation_result = translation_service.process(translation_input)
        english_translation = translation_result['translated_text']
        clean_english_translation = _sanitize_input(english_translation, 1000)
        
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


@csrf_protect
@login_required
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
    
    # 清理和验证输入文本 (Clean and validate input text)
    text = _sanitize_input(data.get('text', ''), 1000)
    if not text:
        return _create_safe_error_response("No text provided", "validation_error", 400)

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
        
        # 清理翻译文本 (Clean translated text)
        clean_chinese_text = _sanitize_input(chinese_text, 1000)
        
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
            'icon': _sanitize_icon_class(topic.get('icon', ''))
        }
        
        # 验证必需字段不为空
        if all(sanitized_topic.values()):
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


# Helper functions
def get_ai_response(conversation_history):
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "gpt-4o", "messages": conversation_history, "response_format": {"type": "json_object"}}
    try:
        response = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except (requests.RequestException, KeyError, IndexError) as e:
        print(f"Error in get_ai_response: {e}")
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


def generate_dynamic_topic_cards():
    """Generate 6 dynamic topic cards using AI for the scene selection page"""
    import random
    import time
    
    # 检查API密钥是否配置
    if not OPENAI_API_KEY:
        print("Warning: OPENAI_API_KEY not configured, using fallback topics")
        raise ValueError("OpenAI API key not configured")
    
    # 检查API密钥格式
    if not OPENAI_API_KEY.startswith('sk-'):
        print("Warning: Invalid OpenAI API key format, using fallback topics")
        raise ValueError("Invalid OpenAI API key format")
    
    # Add randomness seed based on current time
    random_seed = int(time.time()) % 1000
    
    system_prompt = f"""You are a Chinese language learning assistant. Generate 6 diverse and practical conversation scenarios for Chinese language practice.

IMPORTANT: Be creative and generate different scenarios each time. Current randomness seed: {random_seed}

Your response must be a JSON array with exactly 6 objects, each containing:
{{
    "title": "Short catchy title (2-4 words)",
    "description": "Detailed scenario description for practice",
    "level": "Beginner|Intermediate|Advanced",
    "icon": "fas fa-[icon-name]" (Font Awesome icon class)
}}

Make scenarios diverse across these categories:
- Daily life situations (shopping, dining, transport)
- Social interactions (meeting people, small talk)
- Professional contexts (work, business)
- Cultural experiences (festivals, traditions)
- Problem-solving scenarios (asking for help, complaints)
- Educational contexts (school, learning)

Ensure variety in difficulty levels and make each scenario unique and engaging."""

    try:
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        messages = [{"role": "system", "content": system_prompt}]
        payload = {
            "model": "gpt-4o-mini",  # 使用4o-mini优化成本和速度
            "messages": messages, 
            "temperature": 1.0,  # Increased temperature for more randomness
            "top_p": 0.9,        # Add top_p for additional randomness
            "presence_penalty": 0.6,  # Encourage new topics
            "frequency_penalty": 0.3   # Reduce repetition
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
        if isinstance(topics, list) and len(topics) == 6:
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
    
    try:
        # 尝试生成动态话题
        raw_topics = generate_dynamic_topic_cards()
        
        # 验证话题数据的完整性
        if not raw_topics or not isinstance(raw_topics, list) or len(raw_topics) == 0:
            raise ValueError("Generated topics are empty or invalid")
        
        # 清理和验证话题数据
        topics = _sanitize_topic_data(raw_topics)
        
        if len(topics) == 0:
            raise ValueError("No valid topics after sanitization")
        
        logger.info(f"Successfully generated and sanitized {len(topics)} AI topics")
        
        return JsonResponse({
            'success': True,
            'topics': topics,
            'source': 'ai_generated',
            'generated_at': timezone.now().isoformat(),
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
    
    try:
        # 获取静态备用话题
        raw_fallback_topics = get_fallback_topics()
        
        # 清理备用话题数据
        fallback_topics = _sanitize_topic_data(raw_fallback_topics)
        
        if len(fallback_topics) == 0:
            raise ValueError("No valid fallback topics after sanitization")
        
        logger.info(f"Using fallback topics due to {error_type}")
        
        # 返回成功响应，但标记为降级模式
        return JsonResponse({
            'success': True,  # 对前端来说这仍然是成功的
            'topics': fallback_topics,
            'source': 'fallback',
            'fallback_reason': error_type,
            'message': _sanitize_input(error_message, 200),  # 清理错误信息
            'generated_at': timezone.now().isoformat(),
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
        safe_emergency_topics = _sanitize_topic_data(emergency_topics)
        
        return JsonResponse({
            'success': True,
            'topics': safe_emergency_topics,
            'source': 'emergency_fallback',
            'fallback_reason': 'complete_system_failure',
            'message': 'Using emergency backup topics',
            'generated_at': timezone.now().isoformat(),
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
        
        # Create AI prompt for scene generation
        system_prompt = """You are a Chinese language learning assistant. Generate creative and practical conversation scenarios for Chinese language practice based on user input. 

Your response should be a JSON object with the following structure:
{
    "scenarios": [
        {
            "title": "Short descriptive title",
            "description": "Detailed scenario description",
            "level": "Beginner|Intermediate|Advanced",
            "context": "Additional context or setting details"
        }
    ]
}

Generate 3-5 diverse scenarios that are:
1. Practical and relevant to real-life situations
2. Appropriate for Chinese language learning
3. Varied in difficulty levels
4. Culturally authentic"""
        
        user_prompt = f"Generate Chinese conversation practice scenarios based on this input: {user_input}"
        
        # Call OpenAI API
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        payload = {"model": "gpt-4o", "messages": messages, "temperature": 0.8}
        
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
