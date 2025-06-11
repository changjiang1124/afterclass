from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import NameGenerationRequest
import json
import requests
import base64
from datetime import datetime

# OpenAI API 配置
OPENAI_API_KEY = settings.OPENAI_API_KEY
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

def get_client_ip(request):
    """获取客户端IP地址"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def home(request):
    """显示中文姓名生成表单"""
    return render(request, 'namegen/home.html')

@csrf_exempt
def generate_name(request):
    """处理姓名生成请求"""
    if request.method == 'POST':
        try:
            # 获取表单数据
            first_name = request.POST.get('first_name', '').strip()
            surname = request.POST.get('surname', '').strip()
            gender = request.POST.get('gender')
            date_of_birth = request.POST.get('date_of_birth')
            personality_trait = request.POST.get('personality_trait')
            preferred_style = request.POST.get('preferred_style')
            
            # 基本验证
            if not first_name or not gender or not personality_trait or not preferred_style:
                return JsonResponse({
                    'success': False,
                    'error': 'Please fill in all required fields'
                })
            
            # 创建请求记录
            name_request = NameGenerationRequest(
                first_name=first_name,
                surname=surname if surname else None,
                gender=gender,
                personality_trait=personality_trait,
                preferred_style=preferred_style,
                ip_address=get_client_ip(request)
            )
            
            # 处理出生日期
            if date_of_birth:
                try:
                    name_request.date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            # 构建AI提示词
            zodiac = name_request.get_chinese_zodiac()
            season = name_request.get_season()
            
            # 性格特征映射
            personality_map = {
                'brave': '勇敢、坚强',
                'kind': '善良、仁慈',
                'artistic': '文艺、优雅',
                'calm': '平静、沉稳',
                'cheerful': '开朗、活泼',
                'wise': '智慧、睿智',
                'gentle': '温和、柔和',
                'strong': '坚强、有力',
                'creative': '富有创意、创新',
                'loyal': '忠诚、可靠',
            }
            
            # 风格映射
            style_map = {
                'traditional': '传统古典，具有深厚文化底蕴',
                'artistic': '诗意文艺，具有艺术气息',
                'modern': '现代时尚，朗朗上口',
                'professional': '正式专业，适合商务场合',
            }
            
            personality_desc = personality_map.get(personality_trait, personality_trait)
            style_desc = style_map.get(preferred_style, preferred_style)
            
            # 构建系统提示词
            system_prompt = f"""你是一位专业的中文姓名学专家，擅长根据个人特质和偏好创造寓意深刻、朗朗上口的中文名字。

请根据以下信息为用户生成中文名字：
- 英文名：{first_name} {surname or ''}
- 性别：{gender}
- 性格特征：{personality_desc}
- 风格偏好：{style_desc}
{"- 生肖：" + zodiac if zodiac else ""}
{"- 出生季节：" + season if season else ""}

要求：
1. 生成3个不同的2-3字中文名字（不包括姓氏）
2. 每个名字都要符合用户的性格特征和风格偏好
3. 如果有生肖和季节信息，适当考虑这些因素
4. 名字要有美好的寓意，读音悦耳，且风格有所变化，且不要让中国人觉得奇怪
5. 拼音必须使用标准声调符号（如：yì xuán，不要用数字yi4 xuan2）
6. 字义说明必须用1-3个简短的英文关键词
7. 必须严格按照以下JSON格式返回，不要添加任何额外的文字说明：

{{
    "names": [
        {{
            "chinese_name": "生成的中文名字1",
            "pinyin": "yì xuān（使用声调符号的拼音）",
            "meaning": "名字的详细含义解释（中英文对照）",
            "reasoning": "选择这个名字的原因",
            "characters": [
                {{"char": "字1", "meaning": "1-3个英文关键词"}},
                {{"char": "字2", "meaning": "1-3个英文关键词"}}
            ]
        }},
        {{
            "chinese_name": "生成的中文名字2",
            "pinyin": "使用声调符号的拼音",
            "meaning": "名字的详细含义解释（中英文对照）",
            "reasoning": "选择这个名字的原因",
            "characters": [
                {{"char": "字1", "meaning": "1-3个英文关键词"}},
                {{"char": "字2", "meaning": "1-3个英文关键词"}}
            ]
        }},
        {{
            "chinese_name": "生成的中文名字3",
            "pinyin": "使用声调符号的拼音",
            "meaning": "名字的详细含义解释（中英文对照）",
            "reasoning": "选择这个名字的原因",
            "characters": [
                {{"char": "字1", "meaning": "1-3个英文关键词"}},
                {{"char": "字2", "meaning": "1-3个英文关键词"}}
            ]
        }}
    ]
}}

拼音声调符号参考：
- 第一声：ā ē ī ō ū ǖ
- 第二声：á é í ó ú ǘ  
- 第三声：ǎ ě ǐ ǒ ǔ ǚ
- 第四声：à è ì ò ù ǜ
- 轻声：a e i o u ü"""
            
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {OPENAI_API_KEY}"
                }
                
                payload = {
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": "请严格按照JSON格式为我生成3个中文名字，只返回JSON，不要添加其他说明文字。"}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1500,
                    "response_format": {"type": "json_object"}
                }
                
                response = requests.post(OPENAI_API_URL, headers=headers, json=payload)
                response_data = response.json()
                
                if response.status_code == 200 and "choices" in response_data:
                    ai_response = response_data["choices"][0]["message"]["content"].strip()
                    
                    # 尝试解析JSON响应
                    try:
                        # 清理响应文本
                        cleaned_response = ai_response.strip()
                        
                        # 提取JSON部分 - 多种格式的支持
                        json_str = None
                        if "```json" in cleaned_response:
                            json_start = cleaned_response.find("```json") + 7
                            json_end = cleaned_response.find("```", json_start)
                            json_str = cleaned_response[json_start:json_end].strip()
                        elif "```" in cleaned_response and "{" in cleaned_response:
                            # 处理没有明确json标记的代码块
                            json_start = cleaned_response.find("```") + 3
                            json_end = cleaned_response.find("```", json_start)
                            potential_json = cleaned_response[json_start:json_end].strip()
                            if potential_json.startswith("{"):
                                json_str = potential_json
                        elif "{" in cleaned_response and "}" in cleaned_response:
                            # 直接提取JSON对象
                            json_start = cleaned_response.find("{")
                            json_end = cleaned_response.rfind("}") + 1
                            json_str = cleaned_response[json_start:json_end]
                        
                        if not json_str:
                            raise ValueError("No JSON found in response")
                        
                        # 解析JSON
                        name_data = json.loads(json_str)
                        
                        # 验证JSON结构
                        if not isinstance(name_data, dict) or 'names' not in name_data:
                            raise ValueError("Invalid JSON structure: missing 'names' field")
                        
                        names_list = name_data.get('names', [])
                        if not names_list or len(names_list) == 0:
                            raise ValueError("No names generated in response")
                        
                        # 验证每个名字的结构
                        for i, name_obj in enumerate(names_list):
                            required_fields = ['chinese_name', 'pinyin', 'meaning', 'characters']
                            for field in required_fields:
                                if field not in name_obj:
                                    raise ValueError(f"Missing field '{field}' in name {i+1}")
                        
                        # 保存第一个名字到数据库作为主要记录
                        first_name_obj = names_list[0]
                        name_request.generated_chinese_name = first_name_obj.get('chinese_name', '')
                        name_request.name_pinyin = first_name_obj.get('pinyin', '')
                        name_request.name_meaning = f"{first_name_obj.get('meaning', '')}\n\n选择原因：{first_name_obj.get('reasoning', '')}"
                        name_request.save()
                        
                        return JsonResponse({
                            'success': True,
                            'request_id': name_request.id,
                            'names': names_list
                        })
                        
                    except json.JSONDecodeError as e:
                        # JSON解析错误
                        name_request.generated_chinese_name = "解析失败"
                        name_request.name_meaning = f"JSON解析错误: {str(e)}\n\n原始响应:\n{ai_response}"
                        name_request.save()
                        
                        return JsonResponse({
                            'success': False,
                            'error': f'JSON解析失败: {str(e)}',
                            'raw_response': ai_response[:500] + "..." if len(ai_response) > 500 else ai_response
                        })
                        
                    except ValueError as e:
                        # 结构验证错误
                        name_request.generated_chinese_name = "结构错误"
                        name_request.name_meaning = f"响应结构错误: {str(e)}\n\n原始响应:\n{ai_response}"
                        name_request.save()
                        
                        return JsonResponse({
                            'success': False,
                            'error': f'响应格式错误: {str(e)}',
                            'raw_response': ai_response[:500] + "..." if len(ai_response) > 500 else ai_response
                        })
                        
                else:
                    error_message = response_data.get("error", {}).get("message", "AI service unavailable")
                    return JsonResponse({
                        'success': False,
                        'error': error_message
                    })
                    
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': f"Service error: {str(e)}"
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f"Request processing failed: {str(e)}"
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def result(request, request_id):
    """显示生成结果页面"""
    name_request = get_object_or_404(NameGenerationRequest, id=request_id)
    
    context = {
        'name_request': name_request,
    }
    
    return render(request, 'namegen/result.html', context)

@csrf_exempt
def text_to_speech(request):
    """中文名字的语音播放功能"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            text = data.get('text', '').strip()
            
            if not text:
                return JsonResponse({'success': False, 'error': 'No text provided'})
            
            # 调用OpenAI TTS API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }
            
            payload = {
                "model": "tts-1",
                "input": text,
                "voice": "nova",  # nova 对中文发音比较好
                "response_format": "mp3"
            }
            
            response = requests.post(
                "https://api.openai.com/v1/audio/speech", 
                headers=headers, 
                json=payload
            )
            
            if response.status_code == 200:
                # 获取音频数据
                audio_data = response.content
                
                # 将音频数据转换为base64
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                
                return JsonResponse({
                    'success': True,
                    'audio_data': audio_base64,
                    'content_type': 'audio/mpeg'
                })
            else:
                error_message = "TTS service unavailable"
                try:
                    error_data = response.json()
                    error_message = error_data.get("error", {}).get("message", error_message)
                except:
                    pass
                
                return JsonResponse({
                    'success': False,
                    'error': error_message
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f"TTS service error: {str(e)}"
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})
