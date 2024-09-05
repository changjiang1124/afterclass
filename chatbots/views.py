from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Chatbot, Conversation
from openai import OpenAI
from django.http import JsonResponse
import markdown
from django.conf import settings
import re

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
