from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import NameGenerationRequest
from .statistics import StatisticsService
import json
import requests
import base64
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import qrcode
import io
import os
from google.cloud import texttospeech

# OpenAI API 配置 (仅用于名字生成)
OPENAI_API_KEY = settings.OPENAI_API_KEY
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

def get_google_tts_client():
    """初始化 Google Cloud TTS 客户端"""
    try:
        return texttospeech.TextToSpeechClient()
    except Exception as e:
        raise Exception(f"Failed to initialize Google TTS client: {str(e)}")

def get_safe_voice_config(voice_name, gender='female'):
    """获取安全的语音配置，包含回退选项"""
    # 按优先级排序的语音选项 - 使用实际可用的语音名称
    fallback_voices = [
        # 首选：标准语音（最广泛可用）
        {'female': 'cmn-CN-Standard-A', 'male': 'cmn-CN-Standard-B'},
        # 备选：其他标准语音  
        {'female': 'cmn-CN-Standard-D', 'male': 'cmn-CN-Standard-C'},
        # 高质量选择：Wavenet 语音
        {'female': 'cmn-CN-Wavenet-A', 'male': 'cmn-CN-Wavenet-B'},
        # 最新技术：Chirp 语音
        {'female': 'cmn-CN-Chirp3-HD-Achernar', 'male': 'cmn-CN-Chirp3-HD-Achird'},
        # 最后选择：仅语言代码，让Google自动选择
        {'female': None, 'male': None}
    ]
    
    # Google Cloud TTS 中文语音选项映射 - 使用实际可用的语音名称
    google_voices = {
        # 标准声音 (更广泛可用，免费额度更多)
        'cmn-CN-Standard-A': {'gender': 'female', 'name': 'cmn-CN-Standard-A'},
        'cmn-CN-Standard-B': {'gender': 'male', 'name': 'cmn-CN-Standard-B'},
        'cmn-CN-Standard-C': {'gender': 'male', 'name': 'cmn-CN-Standard-C'},
        'cmn-CN-Standard-D': {'gender': 'female', 'name': 'cmn-CN-Standard-D'},
        
        # 高质量 Wavenet 声音
        'cmn-CN-Wavenet-A': {'gender': 'female', 'name': 'cmn-CN-Wavenet-A'},
        'cmn-CN-Wavenet-B': {'gender': 'male', 'name': 'cmn-CN-Wavenet-B'},
        'cmn-CN-Wavenet-C': {'gender': 'male', 'name': 'cmn-CN-Wavenet-C'},
        'cmn-CN-Wavenet-D': {'gender': 'female', 'name': 'cmn-CN-Wavenet-D'},
        
        # 最新 Chirp 语音 (高质量，推荐使用)
        'cmn-CN-Chirp3-HD-Achernar': {'gender': 'female', 'name': 'cmn-CN-Chirp3-HD-Achernar'},
        'cmn-CN-Chirp3-HD-Achird': {'gender': 'male', 'name': 'cmn-CN-Chirp3-HD-Achird'},
        'cmn-CN-Chirp3-HD-Aoede': {'gender': 'female', 'name': 'cmn-CN-Chirp3-HD-Aoede'},
        'cmn-CN-Chirp3-HD-Algenib': {'gender': 'male', 'name': 'cmn-CN-Chirp3-HD-Algenib'},
        
        # 兼容 OpenAI 语音名称的映射 - 使用实际可用的语音
        'alloy': {'gender': 'female', 'name': 'cmn-CN-Standard-A'},
        'echo': {'gender': 'male', 'name': 'cmn-CN-Standard-B'},
        'fable': {'gender': 'female', 'name': 'cmn-CN-Standard-D'},
        'onyx': {'gender': 'male', 'name': 'cmn-CN-Standard-C'},
        'nova': {'gender': 'female', 'name': 'cmn-CN-Wavenet-A'},
        'shimmer': {'gender': 'female', 'name': 'cmn-CN-Chirp3-HD-Achernar'},
        
        # 向后兼容：旧的 zh-CN 格式映射到新的 cmn-CN 格式
        'zh-CN-Standard-A': {'gender': 'female', 'name': 'cmn-CN-Standard-A'},
        'zh-CN-Standard-B': {'gender': 'male', 'name': 'cmn-CN-Standard-B'},
        'zh-CN-Wavenet-A': {'gender': 'female', 'name': 'cmn-CN-Wavenet-A'},
        'zh-CN-Wavenet-B': {'gender': 'male', 'name': 'cmn-CN-Wavenet-B'},
    }
    
    # 如果指定的语音存在，直接使用
    if voice_name in google_voices:
        return google_voices[voice_name]
    
    # 否则按照回退顺序选择
    for fallback in fallback_voices:
        voice_choice = fallback.get(gender)
        if voice_choice and voice_choice in google_voices:
            return google_voices[voice_choice]
        elif voice_choice is None:
            # 最后回退：仅使用语言代码
            return {
                'gender': gender, 
                'name': None  # None 表示让Google自动选择
            }
    
    # 如果所有都失败，返回最基本的配置
    return {'gender': gender, 'name': None}

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
1. 生成3个不同的2字中文名字（不包括姓氏）
2. 每个名字适当考虑符合用户的性格特征和风格偏好, 且尽量在发音上与用户的英文名相似
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
                        
                        # 记录姓名生成统计
                        StatisticsService.record_activity(
                            request, 
                            'name_generation',
                            generated_name=name_request.generated_chinese_name,
                            request_id=name_request.id
                        )
                        
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
    
    # 记录结果查看统计
    StatisticsService.record_activity(
        request, 
        'result_view',
        generated_name=name_request.generated_chinese_name,
        request_id=name_request.id
    )
    
    context = {
        'name_request': name_request,
    }
    
    return render(request, 'namegen/result.html', context)

@csrf_exempt
def text_to_speech(request):
    """中文名字的语音播放功能 - 使用 Google Cloud Text-to-Speech"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            text = data.get('text', '').strip()
            
            if not text:
                return JsonResponse({'success': False, 'error': 'No text provided'})
            
            # 初始化 Google Cloud TTS 客户端
            client = get_google_tts_client()
            
            # 配置语音合成输入
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # 获取安全的语音配置
            voice_config = get_safe_voice_config('cmn-CN-Standard-A', 'female')
            
            # 配置语音参数
            voice_params = {
                'language_code': "zh-CN",
                'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE
            }
            
            # 只有在有具体语音名称时才添加 name 参数
            if voice_config['name']:
                voice_params['name'] = voice_config['name']
            
            voice = texttospeech.VoiceSelectionParams(**voice_params)
            
            # 配置音频输出格式
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=0.8  # 降低语速，让发音更清楚
            )
            
            # 执行文本转语音请求
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # 获取音频数据并转换为base64
            audio_data = response.audio_content
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # 记录TTS统计
            StatisticsService.record_activity(
                request, 
                'tts_request',
                generated_name=text
            )
            
            return JsonResponse({
                'success': True,
                'audio_data': audio_base64,
                'content_type': 'audio/mpeg'
            })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f"Google TTS service error: {str(e)}"
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def text_to_speech_advanced(request):
    """高级中文名字语音播放功能 - 使用 Google Cloud TTS，可自定义语速和音色"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            text = data.get('text', '').strip()
            speed = data.get('speed', 0.8)  # 默认0.8倍速，更清楚
            voice_name = data.get('voice', 'cmn-CN-Standard-A')  # 默认使用标准女声
            gender = data.get('gender', 'female')  # 性别选择
            
            if not text:
                return JsonResponse({'success': False, 'error': 'No text provided'})
            
            # 验证语速参数
            if not (0.25 <= speed <= 4.0):
                speed = 0.8
            
            # 获取安全的语音配置
            voice_config = get_safe_voice_config(voice_name, gender)
            
            # 初始化 Google Cloud TTS 客户端
            client = get_google_tts_client()
            
            # 配置语音合成输入
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # 配置语音参数
            voice_params = {
                'language_code': "zh-CN",
                'ssml_gender': (texttospeech.SsmlVoiceGender.MALE 
                               if voice_config['gender'] == 'male' 
                               else texttospeech.SsmlVoiceGender.FEMALE)
            }
            
            # 只有在有具体语音名称时才添加 name 参数
            if voice_config['name']:
                voice_params['name'] = voice_config['name']
            
            voice = texttospeech.VoiceSelectionParams(**voice_params)
            
            # 配置音频输出格式
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=speed,  # 语速控制
                pitch=0.0,  # 音调 (可以在 -20.0 到 20.0 之间)
                volume_gain_db=0.0  # 音量增益
            )
            
            # 执行文本转语音请求
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # 获取音频数据并转换为base64
            audio_data = response.audio_content
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # 记录高级TTS统计
            StatisticsService.record_activity(
                request, 
                'tts_request',
                generated_name=text
            )
            
            return JsonResponse({
                'success': True,
                'audio_data': audio_base64,
                'content_type': 'audio/mpeg',
                'settings': {
                    'voice': voice_config['name'],
                    'gender': voice_config['gender'],
                    'speed': speed,
                    'language': 'zh-CN',
                    'model': 'Google Cloud TTS'
                }
            })
                
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': f"Google Advanced TTS service error: {str(e)}"
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def generate_name_card(request):
    """生成名片图片"""
    if request.method == 'POST':
        try:
            # 解析请求数据
            data = json.loads(request.body)
            chinese_name = data.get('chinese_name', '')
            pinyin = data.get('pinyin', '')
            characters = data.get('characters', [])
            meaning = data.get('meaning', '')
            
            if not chinese_name:
                return JsonResponse({
                    'success': False,
                    'error': 'Chinese name is required'
                })
            
            # 创建名片图片
            image_data = create_name_card_image(chinese_name, pinyin, characters, meaning, request)
            
            # 记录名片生成统计
            StatisticsService.record_activity(
                request, 
                'name_card_generation',
                generated_name=chinese_name
            )
            
            return JsonResponse({
                'success': True,
                'image_data': image_data
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Failed to generate name card: {str(e)}'
            })
    else:
        return JsonResponse({
            'success': False,
            'error': 'Invalid request method'
        })

def create_name_card_image(chinese_name, pinyin, characters, meaning, request):
    """创建水墨风格的名片图片"""
    
    # 名片尺寸 (适合移动端分享，3:4比例)
    width, height = 800, 1200
    
    # 尝试加载背景图片
    bg_path = os.path.join(settings.BASE_DIR, 'static', 'namegen', 'images', 'namecardbg.png')
    if os.path.exists(bg_path):
        try:
            img = Image.open(bg_path)
            # 调整背景图片尺寸
            img = img.resize((width, height), Image.Resampling.LANCZOS)
            # 确保是RGB模式
            if img.mode != 'RGB':
                img = img.convert('RGB')
        except:
            # 如果背景图片加载失败，使用纯色背景
            img = Image.new('RGB', (width, height), '#f5f5f5')
    else:
        # 创建默认背景
        img = Image.new('RGB', (width, height), '#f5f5f5')
    
    draw = ImageDraw.Draw(img)
    
    try:
        # 按顺序尝试字体，确保路径正确
        chinese_font_large = None
        chinese_font_medium = None
        chinese_font_small = None
        english_font = None
        
        # 字体加载
        font_paths = [
            '/usr/share/fonts/truetype/arphic/ukai.ttc',  # 楷书字体
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',  # 文泉驿字体
            '/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc',
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    # 使用更大的字体尺寸确保可见性
                    chinese_font_large = ImageFont.truetype(font_path, 200)  # 更大的字体
                    chinese_font_medium = ImageFont.truetype(font_path, 100)
                    chinese_font_small = ImageFont.truetype(font_path, 60)
                    break
                except Exception:
                    continue
        
        # 英文字体
        english_font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
        ]
        
        for font_path in english_font_paths:
            if os.path.exists(font_path):
                try:
                    english_font = ImageFont.truetype(font_path, 50)
                    break
                except:
                    continue
        
        # 备用字体
        if not chinese_font_large:
            try:
                # 尝试加载默认字体
                chinese_font_large = ImageFont.load_default()
                chinese_font_medium = ImageFont.load_default()
                chinese_font_small = ImageFont.load_default()
            except:
                # 如果连默认字体都失败，创建简单版本
                return create_simple_name_card(chinese_name, pinyin, request)
        
        if not english_font:
            english_font = chinese_font_small
        
        # 绘制中文名字（垂直排列，传统书写方式）
        char_list = list(chinese_name)
        char_height = 200  # 更大的字符间距
        total_height = len(char_list) * char_height
        start_y = max(100, (height - total_height) // 2)  # 确保不会超出边界
        name_x = width // 2 - 100  # 居中偏左
        
        # 绘制每个汉字（垂直排列）
        for i, char in enumerate(char_list):
            char_y = start_y + i * char_height
            if char_y + 200 < height:  # 确保字符不会超出画布
                draw.text((name_x, char_y), char, font=chinese_font_large, fill='#000000')
        
        # 在名字右侧绘制拼音（垂直排列）
        if pinyin:
            pinyin_parts = pinyin.split(' ')
            if len(pinyin_parts) == len(char_list):
                pinyin_x = name_x + 220  # 在汉字右侧
                for i, pinyin_part in enumerate(pinyin_parts):
                    pinyin_y = start_y + i * char_height + 50
                    if pinyin_y + 50 < height:
                        draw.text((pinyin_x, pinyin_y), pinyin_part, font=english_font, fill='#333333')
        
        # 在名字左侧绘制字符含义（垂直排列）
        if characters and len(characters) > 0:
            meaning_x = max(20, name_x - 300)  # 在汉字左侧，确保不超出边界
            for i, char_info in enumerate(characters[:len(char_list)]):
                char = char_info.get('char', '')
                char_meaning = char_info.get('meaning', '')
                
                if char and char_meaning and i < len(char_list):
                    meaning_y = start_y + i * char_height + 50
                    if meaning_y + 60 < height and meaning_x > 0:
                        draw.text((meaning_x, meaning_y), char_meaning, font=chinese_font_small, fill='#444444')
        
        # 生成QR码
        qr_data = request.build_absolute_uri('/namegen/')
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=6,
            border=2,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # 创建QR码图片
        qr_img = qr.make_image(fill_color='#000000', back_color='#ffffff')
        qr_img = qr_img.resize((120, 120))
        
        # 将QR码放在左下角
        qr_x = 50
        qr_y = height - 180
        # 为QR码创建白色背景
        qr_bg = Image.new('RGB', (140, 140), (255, 255, 255))
        img.paste(qr_bg, (qr_x - 10, qr_y - 10))
        img.paste(qr_img, (qr_x, qr_y))
        
        # 绘制QR码说明文字
        qr_text = "Scan to generate yours"
        draw.text((qr_x, qr_y + 130), qr_text, font=english_font, fill='#000000')
        
        # 绘制版权信息在右下角
        copyright_text = "© 2025 Learn Chinese Perth"
        copyright_y = height - 30
        copyright_x = width - 300  # 固定位置，避免计算错误
        draw.text((copyright_x, copyright_y), copyright_text, font=chinese_font_small, fill='#666666')
        
        # 保存为base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', quality=95)
        img_data = buffer.getvalue()
        buffer.close()
        
        return base64.b64encode(img_data).decode()
        
    except Exception as e:
        # 如果出现错误，创建简单版本
        return create_simple_name_card(chinese_name, pinyin, request)

def create_simple_name_card(chinese_name, pinyin, request):
    """创建简化版名片"""
    try:
        # 设置画布尺寸 (16:9)
        width, height = 800, 450
        
        # 创建白色背景
        img = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(img)
        
        # 设置字体大小
        try:
            font_large = ImageFont.truetype("arial.ttf", 60)
            font_medium = ImageFont.truetype("arial.ttf", 30)
            font_small = ImageFont.truetype("arial.ttf", 20)
        except OSError:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # 绘制中文名字
        draw.text((400, 150), chinese_name, font=font_large, fill='black', anchor='mm')
        
        # 绘制拼音
        draw.text((400, 220), pinyin, font=font_medium, fill='gray', anchor='mm')
        
        # 绘制底部文字
        draw.text((400, 350), "Generated by Learn Chinese Perth", font=font_small, fill='darkgray', anchor='mm')
        draw.text((400, 380), "learnchineseperth.com.au", font=font_small, fill='blue', anchor='mm')
        
        # 保存到字节流
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG', quality=95)
        img_buffer.seek(0)
        
        return img_buffer.getvalue()
        
    except Exception as e:
        print(f"Error creating simple name card: {str(e)}")
        return None

# SEO-friendly views
def sitemap(request):
    """Generate XML sitemap for SEO"""
    from django.urls import reverse
    
    # Get the current domain
    domain = request.get_host()
    protocol = 'https' if request.is_secure() else 'http'
    
    sitemap_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>{protocol}://{domain}{reverse('namegen:home')}</loc>
        <lastmod>{datetime.datetime.now().strftime('%Y-%m-%d')}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>1.0</priority>
    </url>
</urlset>'''
    
    return HttpResponse(sitemap_xml, content_type='application/xml')

def robots_txt(request):
    """Generate robots.txt for SEO"""
    from django.urls import reverse
    
    # Get the current domain
    domain = request.get_host()
    protocol = 'https' if request.is_secure() else 'http'
    
    robots_content = f'''User-agent: *
Allow: /

# Sitemap
Sitemap: {protocol}://{domain}{reverse('namegen:sitemap')}

# Allow search engines to index our Chinese name generator
Allow: /namegen/
Allow: /static/

# Crawl-delay for respectful crawling
Crawl-delay: 1
'''
    
    return HttpResponse(robots_content, content_type='text/plain')

@csrf_exempt
def track_share_click(request):
    """跟踪分享按钮点击"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            platform = data.get('platform', 'unknown')
            chinese_name = data.get('chinese_name', '')
            
            # 记录分享点击统计
            StatisticsService.record_activity(
                request, 
                'share_click',
                share_platform=platform,
                generated_name=chinese_name
            )
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def statistics_dashboard(request):
    """统计数据仪表板"""
    # 获取统计摘要
    summary = StatisticsService.get_statistics_summary(days=30)
    popular_names = StatisticsService.get_popular_names(days=30)
    
    context = {
        'summary': summary,
        'popular_names': popular_names,
    }
    
    return render(request, 'namegen/statistics.html', context)

@csrf_exempt
def statistics_api(request):
    """统计API接口"""
    if request.method == 'GET':
        days = int(request.GET.get('days', 30))
        
        summary = StatisticsService.get_statistics_summary(days=days)
        popular_names = StatisticsService.get_popular_names(days=days)
        
        return JsonResponse({
            'success': True,
            'summary': summary,
            'popular_names': popular_names
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})
