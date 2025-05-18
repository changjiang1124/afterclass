from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import GeneratedText, TypingRecord
import json
import random
from pinyinit.views import PinyinMarker
import requests
import os
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

# 创建PinyinMarker实例
pinyin_marker = PinyinMarker()

# OpenAI API 配置
OPENAI_API_KEY = settings.OPENAI_API_KEY
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# Create your views here.

# 首页视图 - 显示文本输入框和生成按钮
@login_required
def home(request):
    return render(request, 'typingchinese/home.html')

# 生成随机主题建议 - AJAX
@csrf_exempt
@login_required
@require_http_methods(["GET"])
def generate_topic_suggestions(request):
    try:
        # 调用OpenAI API生成主题建议
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        system_prompt = """
        You are a helpful assistant for Chinese learners. Please provide 5 short topic suggestions for Chinese typing practice, each with 1-3 words in Australian English.
        These topics should be diverse and interesting, and able to inspire users to generate meaningful Chinese content for typing practice.
        Only return the list of topics, no explanation or additional text. One topic per line.
        """
        
        user_prompt = "Please provide 4 short topic suggestions for Chinese typing practice in Australian English, covering life, culture, technology, education, etc. The topics should be diverse and interesting, and able to inspire users to generate meaningful Chinese content for typing practice."
        
        payload = {
            "model": "gpt-4.1",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.9,
            "max_tokens": 200
        }
        
        response = requests.post(OPENAI_API_URL, headers=headers, json=payload)
        response_data = response.json()
        
        if response.status_code == 200 and "choices" in response_data:
            topics_text = response_data["choices"][0]["message"]["content"].strip()
            
            # 将AI返回的多行主题文本分割为列表
            topics = [topic.strip() for topic in topics_text.split('\n') if topic.strip()]
            
            # 只取前5个主题
            topics = topics[:5]
            
            return JsonResponse({
                'success': True,
                'topics': topics
            })
        else:
            error_message = response_data.get("error", {}).get("message", "Error generating topics, please try again")
            return JsonResponse({
                'success': False,
                'error': error_message
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f"API调用失败: {str(e)}"
        })

# 处理AI文本生成请求 - AJAX
@csrf_exempt
@login_required
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
        1. 总是尝试用中文去生成回复（虽然输入可能会是任何语言），除非用户明确要求使用其他语言。只有当用户的指令可以用于生成适合中文练习的内容时才生成文本
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
                error_message = response_data.get("error", {}).get("message", "An error occurred during generation, please try again")
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
@login_required
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
@login_required
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

# 处理文本翻译 - AJAX
@csrf_exempt
@login_required
def translate_text(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        text = data.get('text', '')
        
        if text:
            # 调用OpenAI API进行翻译
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {OPENAI_API_KEY}"
                }
                
                system_prompt = """
                You are a professional translator. Translate the Chinese text provided by the user into English.
                Provide only the translated text without any additional explanation or comments.
                """
                
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Translate this Chinese text to English: {text}"}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1000
                }
                
                response = requests.post(OPENAI_API_URL, headers=headers, json=payload)
                response_data = response.json()
                
                if response.status_code == 200 and "choices" in response_data:
                    translated_text = response_data["choices"][0]["message"]["content"].strip()
                    
                    return JsonResponse({
                        'success': True,
                        'translation': translated_text
                    })
                else:
                    error_message = response_data.get("error", {}).get("message", "Translation failed, please try again")
                    return JsonResponse({
                        'success': False,
                        'error': error_message
                    })
                    
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': f"API调用失败: {str(e)}"
                })
        
        return JsonResponse({'success': False, 'error': 'No text provided'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

# 练习页面视图
@login_required
def practice(request):
    text_id = request.GET.get('text_id')
    text_content = request.GET.get('text')
    
    # 如果有text_id，从数据库获取文本
    if text_id:
        try:
            text_obj = GeneratedText.objects.get(id=text_id)
            text_content = text_obj.content
            
            # 计算汉字数量
            chinese_char_count = sum(1 for char in text_content if '\u4e00' <= char <= '\u9fff')
            
            # 确保至少有1个字符
            total_chars = max(chinese_char_count, 1)
            
            # 创建打字记录
            typing_record = TypingRecord.objects.create(
                user=request.user,
                source_text=text_content,
                total_chars=total_chars,
                generated_text=text_obj
            )
            record_id = typing_record.id
        except GeneratedText.DoesNotExist:
            text_content = ""
            record_id = None
    # 如果没有text_id但有text参数，直接使用传入的文本
    elif text_content:
        # 计算汉字数量
        chinese_char_count = sum(1 for char in text_content if '\u4e00' <= char <= '\u9fff')
        
        # 确保至少有1个字符
        total_chars = max(chinese_char_count, 1)
        
        # 创建打字记录
        typing_record = TypingRecord.objects.create(
            user=request.user,
            source_text=text_content,
            total_chars=total_chars
        )
        record_id = typing_record.id
    else:
        record_id = None
    
    context = {
        'text': text_content,
        'record_id': record_id
    }
    
    return render(request, 'typingchinese/practice.html', context)

# 保存打字进度 - AJAX
@csrf_exempt
@login_required
def save_typing_progress(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        record_id = data.get('record_id')
        current_input = data.get('current_input', '')
        correct_chars = data.get('correct_chars', 0)
        is_completed = data.get('is_completed', False)
        
        if record_id:
            try:
                record = TypingRecord.objects.get(id=record_id, user=request.user)
                record.current_input = current_input
                record.correct_chars = correct_chars
                record.is_completed = is_completed
                record.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Progress saved successfully'
                })
            except TypingRecord.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Record not found'
                })
        
        return JsonResponse({'success': False, 'error': 'No record ID provided'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

# 获取打字历史记录 - AJAX
@login_required
def get_typing_history(request):
    # 获取用户的所有打字记录，按更新时间倒序排列
    records = TypingRecord.objects.filter(user=request.user).order_by('-updated_at')[:10]  # 只获取最近的10条记录
    
    history_data = []
    for record in records:
        # 截取源文本前30个字符作为预览
        preview = record.source_text[:30] + "..." if len(record.source_text) > 30 else record.source_text
        
        # 重新计算完成百分比
        completion = record.completion_percentage()

        # 确保记录有正确的值
        print(f"Record ID: {record.id}, Correct: {record.correct_chars}, Total: {record.total_chars}, Completion: {completion}%")

        # 如果百分比为0但实际已完成，确保正确显示
        if record.is_completed and completion == 0:
            completion = 100
        
        # 使用ISO格式的时间，更容易被JavaScript处理
        updated_at_iso = record.updated_at.isoformat()
        
        history_data.append({
            'id': record.id,
            'preview': preview,
            'completion': completion,
            'is_completed': record.is_completed,
            'updated_at': record.updated_at.strftime('%d/%m/%Y %H:%M'),
            'updated_at_iso': updated_at_iso
        })
    
    return JsonResponse({
        'success': True,
        'history': history_data
    })

# 继续未完成的练习
@login_required
def continue_practice(request, record_id):
    try:
        record = TypingRecord.objects.get(id=record_id, user=request.user)
        
        context = {
            'text': record.source_text,
            'record_id': record.id,
            'current_input': record.current_input
        }
        
        return render(request, 'typingchinese/practice.html', context)
    except TypingRecord.DoesNotExist:
        return redirect('typingchinese:home')
