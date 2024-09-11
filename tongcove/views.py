from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.http import HttpResponse
from aip import AipSpeech
import logging

logger = logging.getLogger(__name__)


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('chatbot_list')
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    return render(request, 'login.html')


def text_to_speech(request):
    if request.method == 'POST':
        text = request.POST.get('text', '')
        logger.info(f"Received TTS request for text: {text[:50]}...")

        APP_ID = '115502863'
        API_KEY = 'rq7cYlg8xnSDLCopaUdxEkll'
        SECRET_KEY = 'VY3VuptumfY7H553oeKJSD5R9ijNuzxw'

        client = AipSpeech(APP_ID, API_KEY, SECRET_KEY)

        def split_text(text, max_length=512):
            return [text[i:i+max_length] for i in range(0, len(text), max_length)]

        text_parts = split_text(text)
        audio_parts = []

        for part in text_parts:
            result = client.synthesis(part, 'zh', 1, {
                'spd': 5, 'pit': 5, 'vol': 5, 'per': 5,
            })

            if not isinstance(result, dict):
                audio_parts.append(result)
            else:
                logger.error(f"TTS synthesis failed for part: {result}")
                return HttpResponse("语音合成失败", status=400)

        if audio_parts:
            combined_audio = b''.join(audio_parts)
            logger.info("TTS synthesis successful for all parts")
            return HttpResponse(combined_audio, content_type='audio/mp3')
        else:
            logger.error("No audio parts were successfully synthesized")
            return HttpResponse("语音合成失败", status=400)

    logger.warning("Invalid TTS request method")
    return HttpResponse("Invalid request", status=400)