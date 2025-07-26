from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import ChatSession, ChatMessage
import json
import requests
import base64
import os

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

    # Generate dynamic topic cards using AI
    dynamic_scenes = generate_dynamic_topic_cards()
    return render(request, 'speak_practice/scene_selection.html', {'dynamic_scenes': dynamic_scenes})


@login_required
def chat_view(request, session_id):
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
        messages = session.messages.order_by('timestamp')
        return render(request, 'speak_practice/chat.html', {'session': session, 'messages': messages})
    except ChatSession.DoesNotExist:
        return redirect('speak_practice:scene_selection')


@csrf_exempt
@login_required
def chat_api(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

    try:
        data = json.loads(request.body)
        user_message = data.get('message')
        session_id = data.get('session_id')

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
        
        # Generate TTS audio
        tts_audio_b64 = get_tts_audio(ai_response_data.get('chinese'))
        if not tts_audio_b64:
            return JsonResponse({'success': False, 'error': 'Failed to generate TTS audio.'}, status=500)

        # Calculate final token count and status
        final_tokens = count_tokens_in_conversation(session_id)
        conversation_ended = should_end_conversation(session_id)
        
        response_data = {
            'success': True,
            'ai_response': ai_response_data,
            'tts_audio': tts_audio_b64,
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


@csrf_exempt
@login_required
def transcribe_audio_api(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

    audio_file = request.FILES.get('audio')
    if not audio_file:
        return JsonResponse({'success': False, 'error': 'No audio file provided'}, status=400)

    chinese_text = transcribe_audio(audio_file)
    if chinese_text:
        english_translation = translate_text_openai(chinese_text, target_language="en")
        return JsonResponse({'success': True, 'chinese_text': chinese_text, 'english_translation': english_translation})
    else:
        return JsonResponse({'success': False, 'error': 'Failed to transcribe audio'}, status=500)


@csrf_exempt
@login_required
def translate_text_api(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

    data = json.loads(request.body)
    text = data.get('text')
    if not text:
        return JsonResponse({'success': False, 'error': 'No text provided'}, status=400)

    chinese_text = translate_text_openai(text, target_language="zh")
    if chinese_text:
        tts_audio_b64 = get_tts_audio(chinese_text)
        return JsonResponse({'success': True, 'chinese_text': chinese_text, 'tts_audio': tts_audio_b64})
    else:
        return JsonResponse({'success': False, 'error': 'Failed to translate text'}, status=500)


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
    system_prompt = """You are a Chinese language learning assistant. Generate 6 diverse and practical conversation scenarios for Chinese language practice.

Your response must be a JSON array with exactly 6 objects, each containing:
{
    "title": "Short catchy title (2-4 words)",
    "description": "Detailed scenario description for practice",
    "level": "Beginner|Intermediate|Advanced",
    "icon": "fas fa-[icon-name]" (Font Awesome icon class)
}

Requirements:
1. Cover different aspects of daily life in China
2. Mix difficulty levels (2 Beginner, 2 Intermediate, 2 Advanced)
3. Make scenarios culturally authentic and practical
4. Vary the icons to match each scenario theme
5. Ensure scenarios are engaging and relevant for language learners"""

    try:
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        messages = [{"role": "system", "content": system_prompt}]
        payload = {"model": "gpt-4o", "messages": messages, "temperature": 0.9}
        
        response = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        ai_response = response.json()['choices'][0]['message']['content']
        topics = json.loads(ai_response)
        
        # Validate the response structure
        if isinstance(topics, list) and len(topics) == 6:
            for topic in topics:
                if not all(key in topic for key in ['title', 'description', 'level', 'icon']):
                    raise ValueError("Invalid topic structure")
            return topics
        else:
            raise ValueError("Invalid response format")
            
    except (requests.RequestException, json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Error generating dynamic topics: {e}")
        # Fallback to static topics if AI generation fails
        return [
            {
                "title": "Café Chat",
                "description": "Ordering coffee and pastries at a local café",
                "level": "Beginner",
                "icon": "fas fa-coffee"
            },
            {
                "title": "Finding Places",
                "description": "Asking for directions to popular tourist attractions",
                "level": "Beginner", 
                "icon": "fas fa-map-marked-alt"
            },
            {
                "title": "Weather Talk",
                "description": "Discussing today's weather and weekend plans",
                "level": "Beginner",
                "icon": "fas fa-cloud-sun"
            },
            {
                "title": "Work Intro",
                "description": "Introducing yourself and background to new colleagues",
                "level": "Intermediate",
                "icon": "fas fa-handshake"
            },
            {
                "title": "Market Deals",
                "description": "Bargaining for souvenirs at a traditional market",
                "level": "Intermediate",
                "icon": "fas fa-shopping-bag"
            },
            {
                "title": "Doctor Visit",
                "description": "Explaining symptoms to a doctor during a consultation",
                "level": "Advanced",
                "icon": "fas fa-user-md"
            }
        ]


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


@csrf_exempt
@login_required
def generate_scene_api(request):
    """API for generating AI-powered conversation scenarios"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        user_input = data.get('user_input', '').strip()
        
        if not user_input:
            return JsonResponse({'error': 'User input is required'}, status=400)
        
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
