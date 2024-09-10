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
    # 512 char limit #TODO 
    
    if request.method == 'POST':
        text = request.POST.get('text', '')
        logger.info(f"Received TTS request for text: {text[:50]}...")  # 记录前50个字符
        
        # 替换为你的百度 API 密钥
        APP_ID = '115502863'
        API_KEY = 'rq7cYlg8xnSDLCopaUdxEkll'
        SECRET_KEY = 'VY3VuptumfY7H553oeKJSD5R9ijNuzxw'

        client = AipSpeech(APP_ID, API_KEY, SECRET_KEY)
        auth_resp = client._auth()
        if isinstance(auth_resp, dict) and 'access_token' in auth_resp:
            print("Access token obtained successfully")
        else:
            print("Failed to obtain access token:", auth_resp)
        
        result = client.synthesis(text, 'zh', 1, {
            'spd': 5,  # 语速
            'pit': 5,  # 音调
            'vol': 5,  # 音量
            'per': 5,  # 发音人, 4 为情感合成-度丫丫
        })

        if not isinstance(result, dict):
            logger.info("TTS synthesis successful")
            return HttpResponse(result, content_type='audio/mp3')
        else:
            logger.error(f"TTS synthesis failed: {result}")
            return HttpResponse("语音合成失败", status=400)
    logger.warning("Invalid TTS request method")
    return HttpResponse("Invalid request", status=400)