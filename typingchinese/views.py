from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import GeneratedText
import json
import random
from pinyinit.views import PinyinMarker
import requests
import os
from django.conf import settings

# 创建PinyinMarker实例
pinyin_marker = PinyinMarker()

# OpenAI API 配置
OPENAI_API_KEY = settings.OPENAI_API_KEY
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# Create your views here.

# 首页视图 - 显示文本输入框和生成按钮
def home(request):
    return render(request, 'typingchinese/home.html')

# 处理AI文本生成请求 - AJAX
@csrf_exempt
def generate_ai_text(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        instruction = data.get('instruction', '')
        length = data.get('length', 'medium')
        
        # 根据长度设置参数
        length_map = {
            'short': "短文本（50-100字）",
            'medium': "中等长度文本（100-200字）",
            'long': "长文本（200-300字）"
        }
        length_desc = length_map.get(length, "中等长度文本（100-200字）")
        
        # 系统提示词 - 确保生成的是适合中文练习的内容
        system_prompt = """
        你是一个专业的中文内容生成助手，用于帮助用户生成适合中文打字练习的文本。
        
        规则：
        1. 总是尝试用中文去生成回复，除非用户明确要求使用其他语言。只有当用户的指令可以用于生成适合中文练习的内容时才生成文本
        2. 如果用户的指令跟生成中文打字练习无关（如包含不当内容、无法理解、要求非中文内容等），回复"无效指令"并简要说明原因
        3. 生成的文本应该是纯中文的，可以包含标点符号，但不要包含英文、数字等非中文字符
        4. 不要在回复中加入任何前缀、标题或者解释，直接返回生成的文本内容
        5. 确保内容长度符合要求
        
        你的回复将直接用于中文打字练习，所以必须是纯文本格式。
        """
        
        # 用户指令转换为提示词
        user_prompt = f"""
        请根据以下指令生成一段适合中文打字练习的{length_desc}：
        
        指令：{instruction}
        """
        
        # 调用OpenAI API
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }
            
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            response = requests.post(OPENAI_API_URL, headers=headers, json=payload)
            response_data = response.json()
            
            if response.status_code == 200 and "choices" in response_data:
                generated_text = response_data["choices"][0]["message"]["content"].strip()
                
                # 检查生成的文本是否是"无效指令"的提示
                if generated_text.startswith("无效指令"):
                    return JsonResponse({
                        'success': False,
                        'error': generated_text
                    })
                
                # 创建并保存生成的文本
                text_obj = GeneratedText(
                    user=request.user if request.user.is_authenticated else None,
                    content=generated_text,
                    topic=instruction[:100]  # 使用指令前100个字符作为主题
                )
                text_obj.save()
                
                return JsonResponse({
                    'success': True,
                    'text': generated_text,
                    'id': text_obj.id
                })
            else:
                error_message = response_data.get("error", {}).get("message", "生成过程中出现问题，请重试")
                return JsonResponse({
                    'success': False,
                    'error': error_message
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f"API调用失败: {str(e)}"
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

# 处理文本生成请求 - AJAX (保留原始随机文本生成功能)
@csrf_exempt
def generate_text(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        topic = data.get('topic', '')
        length = data.get('length', 'medium')
        
        # 根据长度生成不同长度的文本
        length_map = {
            'short': (50, 100),
            'medium': (100, 200),
            'long': (200, 300)
        }
        
        # 示例文本生成 (实际应用中可以使用更复杂的AI生成逻辑)
        sample_texts = [
            "我喜欢在珀斯的海滩散步，特别是在夏天的时候。海水很蓝，沙子很细，人们都很友好。",
            "学习中文是一个有趣的过程，通过不断练习，你的语言能力会逐步提高。坚持是成功的关键。",
            "珀斯是一个美丽的城市，有许多公园和自然保护区。周末的时候，很多人喜欢去国王公园野餐。",
            "中国文化历史悠久，包含了丰富的传统艺术、美食和节日。了解这些文化元素能帮助你更好地学习中文。",
            "打字练习是提高中文输入速度的好方法，每天坚持练习十分钟，你会发现自己的打字速度逐渐提高。",
        ]
        
        # 随机选择并组合文本片段来生成所需长度的文本
        min_length, max_length = length_map.get(length, (100, 200))
        generated_text = ""
        while len(generated_text) < min_length:
            generated_text += random.choice(sample_texts) + " "
            
        # 创建并保存生成的文本
        text_obj = GeneratedText(
            user=request.user if request.user.is_authenticated else None,
            content=generated_text,
            topic=topic
        )
        text_obj.save()
        
        return JsonResponse({
            'success': True,
            'text': generated_text,
            'id': text_obj.id
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

# 处理拼音生成 - AJAX
@csrf_exempt
def process_pinyin(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        text = data.get('text', '')
        
        if text:
            # 分段处理带有换行符的文本
            paragraphs = text.split('\n')
            result_html = ""
            
            for i, paragraph in enumerate(paragraphs):
                if paragraph.strip():  # 跳过空段落
                    result_html += pinyin_marker.process_text(paragraph)
                    # 如果不是最后一段，添加换行标记
                    if i < len(paragraphs) - 1:
                        result_html += '<br />'*3
            
            return JsonResponse({
                'success': True,
                'html': result_html
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

# 练习页面视图
def practice(request):
    text_id = request.GET.get('text_id')
    text_content = request.GET.get('text')
    
    # 如果有text_id，从数据库获取文本
    if text_id:
        try:
            text_obj = GeneratedText.objects.get(id=text_id)
            text_content = text_obj.content
        except GeneratedText.DoesNotExist:
            text_content = ""
    
    # 如果没有text_id但有text参数，直接使用传入的文本
    context = {
        'text': text_content
    }
    
    return render(request, 'typingchinese/practice.html', context)
