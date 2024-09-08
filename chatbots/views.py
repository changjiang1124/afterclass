from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Chatbot, Conversation
from openai import OpenAI
from django.http import JsonResponse
import markdown
from django.conf import settings
import re
from django.http import HttpResponse
import io
from aip import AipSpeech

@login_required
def chatbot_list(request):
    chatbots = Chatbot.objects.all()
    return render(request, 'chatbots/chatbot_list.html', {'chatbots': chatbots})

@login_required
def chatbot_detail(request, chatbot_id):
    chatbot = get_object_or_404(Chatbot, id=chatbot_id)
    conversations = Conversation.objects.filter(user=request.user, chatbot=chatbot)
    
    for conversation in conversations:
        conversation.response = markdown.markdown(conversation.response)
        conversation.response = f'<span class="message-text">{conversation.response}</span><button class="btn btn-sm btn-outline-secondary ml-2 speak-button"><i class="fas fa-volume-up"></i></button>'
    
    if request.method == 'POST':
        message = request.POST['message']
        
        # 获取之前的对话内容
        previous_conversations = Conversation.objects.filter(user=request.user, chatbot=chatbot).order_by('-timestamp')[:50]  # 获取最近的5条对话
        context = [{"role": "system", "content": chatbot.prompt}]
        for conv in reversed(previous_conversations):
            context.append({"role": "user", "content": conv.message})
            context.append({"role": "assistant", "content": conv.response})
        context.append({"role": "user", "content": message})
        
        # 调用 OpenAI API
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=context
        )
        
        ai_response = response.choices[0].message.content
        
        # 对 AI 响应进行后处理
        # cannot do this, because the response is markdown
        # ai_response = ai_response.replace('\n', ' ').strip()
        # ai_response = re.sub(r'\s+', ' ', ai_response)  # 删除多余的空格
        
        # 创建新的 Conversation 对象，并保存用户的消息和 AI 的回复
        new_conversation = Conversation.objects.create(
            user=request.user, 
            chatbot=chatbot, 
            message=message, 
            response=ai_response
        )
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            ai_response_html = markdown.markdown(ai_response)
            ai_response_with_button = f'<span class="message-text">{ai_response_html}</span><button class="btn btn-sm btn-outline-secondary ml-2 speak-button"><i class="fas fa-volume-up"></i></button>'
            return JsonResponse({
                'message': message,
                'response': ai_response_with_button
            })
        return redirect('chatbots:chatbot_detail', chatbot_id=chatbot_id)
    
    return render(request, 'chatbots/chatbot_detail.html', {'chatbot': chatbot, 'conversations': conversations})

@login_required
def clear_conversation(request, chatbot_id):
    chatbot = get_object_or_404(Chatbot, id=chatbot_id)
    Conversation.objects.filter(user=request.user, chatbot=chatbot).delete()
    return redirect('chatbots:chatbot_detail', chatbot_id=chatbot_id)


# openai tts
# def text_to_speech(request):
#     if request.method == 'POST':
#         text = request.POST.get('text', '')
#         voice = request.POST.get('voice', 'alloy')

#         client = OpenAI(api_key=settings.OPENAI_API_KEY)
#         response = client.audio.speech.create(
#             model="tts-1",
#             voice=voice,
#             input=text
#         )

#         audio_content = io.BytesIO(response.content)
#         return HttpResponse(audio_content, content_type='audio/mpeg')
#     return HttpResponse("Invalid request", status=400)



def text_to_speech(request):
    if request.method == 'POST':
        text = request.POST.get('text', '')
        
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
            'per': 4,  # 发音人, 4 为情感合成-度丫丫
        })

        if not isinstance(result, dict):
            return HttpResponse(result, content_type='audio/mp3')
        else:
            return HttpResponse("语音合成失败", status=400)
    return HttpResponse("Invalid request", status=400)
