"""
增强聊天交互功能集成测试 (Enhanced chat interaction integration tests)

这个测试文件包含完整的语音消息流程、文本翻译和TTS生成的集成测试，
以及错误处理和恢复机制的验证。
(This test file contains complete voice message flow, text translation and TTS generation integration tests,
as well as error handling and recovery mechanism verification.)
"""

import json
import tempfile
import unittest
from unittest.mock import patch, Mock, MagicMock
from io import BytesIO
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import override_settings
from django.middleware.csrf import get_token

from speak_practice.models import ChatSession, ChatMessage
from speak_practice.services.speech_recognition import SpeechRecognitionService
from speak_practice.services.text_to_speech import TextToSpeechService
from speak_practice.services.translation import TranslationService
from speak_practice.services.exceptions import (
    SpeechRecognitionError, TTSError, TranslationError,
    AudioValidationError, TranscriptionTimeoutError,
    TTSServiceUnavailableError, UnsupportedLanguageError
)


class ChatInteractionIntegrationTest(TestCase):
    """聊天交互集成测试类 (Chat interaction integration test class)"""
    
    def setUp(self):
        """测试设置 (Test setup)"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # 创建测试会话 (Create test session)
        self.session = ChatSession.objects.create(
            user=self.user,
            scene='咖啡店点餐 (Coffee shop ordering)'
        )
        
        # 模拟音频文件 (Mock audio file)
        self.mock_audio_content = b'fake_audio_content'
        self.mock_audio_file = SimpleUploadedFile(
            "test_audio.webm",
            self.mock_audio_content,
            content_type="audio/webm"
        )
    
    def tearDown(self):
        """测试清理 (Test cleanup)"""
        # 清理测试数据 (Clean up test data)
        ChatMessage.objects.filter(session=self.session).delete()
        ChatSession.objects.filter(user=self.user).delete()
    
    @patch('speak_practice.services.speech_recognition.SpeechRecognitionService.process')
    @patch('speak_practice.services.translation.TranslationService.process')
    def test_complete_voice_message_flow(self, mock_translation, mock_speech):
        """
        测试完整的语音消息流程 (Test complete voice message flow)
        
        测试从语音录制到转录、翻译、确认和发送的完整流程
        (Test complete flow from voice recording to transcription, translation, confirmation and sending)
        """
        # 设置模拟返回值 (Set up mock return values)
        mock_speech.return_value = {
            'transcribed_text': '你好，我想要一杯咖啡',
            'audio_duration': 3.5,
            'audio_size': 1024,
            'audio_format': 'webm'
        }
        
        mock_translation.return_value = {
            'translated_text': 'Hello, I would like a cup of coffee',
            'source_language': 'zh',
            'target_language': 'en',
            'character_count': 9
        }
        
        # 步骤1: 语音转录 (Step 1: Voice transcription)
        with patch('speak_practice.views._validate_request_origin', return_value=True):
            transcribe_url = reverse('speak_practice:transcribe_audio_api')
            transcribe_response = self.client.post(
                transcribe_url,
                {'audio': self.mock_audio_file},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
        
        self.assertEqual(transcribe_response.status_code, 200)
        transcribe_data = json.loads(transcribe_response.content)
        
        self.assertTrue(transcribe_data['success'])
        self.assertEqual(transcribe_data['chinese_text'], '你好，我想要一杯咖啡')
        self.assertEqual(transcribe_data['english_translation'], 'Hello, I would like a cup of coffee')
        self.assertIn('audio_info', transcribe_data)
        self.assertEqual(transcribe_data['audio_info']['duration'], 3.5)
        
        # 步骤2: 发送确认的消息到聊天API (Step 2: Send confirmed message to chat API)
        with patch('speak_practice.views.get_ai_response') as mock_ai_response, \
             patch('speak_practice.services.text_to_speech.tts_service.generate_speech') as mock_tts, \
             patch('speak_practice.views._validate_request_origin', return_value=True):
            
            # 设置AI响应模拟 (Set up AI response mock)
            mock_ai_response.return_value = json.dumps({
                'chinese': '好的，您要什么样的咖啡？',
                'pinyin': 'hǎo de, nín yào shén me yàng de kā fēi?'
            })
            
            # 设置TTS模拟 (Set up TTS mock)
            mock_tts.return_value = 'base64_encoded_audio_data'
            
            chat_url = reverse('speak_practice:chat_api')
            chat_response = self.client.post(
                chat_url,
                json.dumps({
                    'message': '你好，我想要一杯咖啡',
                    'session_id': self.session.id
                }),
                content_type='application/json',
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            self.assertEqual(chat_response.status_code, 200)
            chat_data = json.loads(chat_response.content)
            
            self.assertTrue(chat_data['success'])
            self.assertIn('ai_response', chat_data)
            self.assertEqual(chat_data['ai_response']['chinese'], '好的，您要什么样的咖啡？')
            self.assertIn('tts_audio', chat_data)
            self.assertTrue(chat_data['tts_available'])
        
        # 验证数据库中的消息记录 (Verify message records in database)
        messages = ChatMessage.objects.filter(session=self.session).order_by('timestamp')
        self.assertEqual(messages.count(), 2)  # 用户消息 + AI回复 (User message + AI reply)
        
        user_message = messages[0]
        self.assertEqual(user_message.sender_type, 'user')
        self.assertEqual(user_message.message_content['chinese_text'], '你好，我想要一杯咖啡')
        
        ai_message = messages[1]
        self.assertEqual(ai_message.sender_type, 'ai')
        self.assertEqual(ai_message.message_content['chinese'], '好的，您要什么样的咖啡？')
    
    @patch('speak_practice.services.translation.TranslationService.process')
    @patch('speak_practice.services.text_to_speech.tts_service.generate_speech')
    def test_text_translation_and_tts_integration(self, mock_tts, mock_translation):
        """
        测试文本翻译和TTS生成的集成 (Test text translation and TTS generation integration)
        
        测试英文输入翻译为中文并生成语音的完整流程
        (Test complete flow of English input translation to Chinese and speech generation)
        """
        # 设置模拟返回值 (Set up mock return values)
        mock_translation.return_value = {
            'translated_text': '我可以帮助您吗？',
            'source_language': 'en',
            'target_language': 'zh',
            'character_count': 7
        }
        
        mock_tts.return_value = 'base64_encoded_tts_audio'
        
        # 调用翻译API (Call translation API)
        with patch('speak_practice.views._validate_request_origin', return_value=True):
            translate_url = reverse('speak_practice:translate_text_api')
            translate_response = self.client.post(
                translate_url,
                json.dumps({'text': 'Can I help you?'}),
                content_type='application/json',
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
        
        self.assertEqual(translate_response.status_code, 200)
        translate_data = json.loads(translate_response.content)
        
        self.assertTrue(translate_data['success'])
        self.assertEqual(translate_data['chinese_text'], '我可以帮助您吗？')
        self.assertIn('pinyin', translate_data)
        self.assertEqual(translate_data['tts_audio'], 'base64_encoded_tts_audio')
        self.assertTrue(translate_data['tts_available'])
        self.assertIn('translation_info', translate_data)
        
        # 验证翻译服务被正确调用 (Verify translation service was called correctly)
        mock_translation.assert_called_once()
        call_args = mock_translation.call_args[0][0]
        self.assertEqual(call_args['text'], 'Can I help you?')
        self.assertEqual(call_args['source_lang'], 'en')
        self.assertEqual(call_args['target_lang'], 'zh')
        
        # 验证TTS服务被正确调用 (Verify TTS service was called correctly)
        mock_tts.assert_called_once_with('我可以帮助您吗？', 'cmn-CN')
    
    @patch('speak_practice.services.speech_recognition.SpeechRecognitionService.process')
    def test_speech_recognition_error_handling(self, mock_speech):
        """
        测试语音识别错误处理 (Test speech recognition error handling)
        
        测试各种语音识别错误情况的处理和恢复机制
        (Test handling and recovery mechanisms for various speech recognition error scenarios)
        """
        # 测试音频验证错误 (Test audio validation error)
        mock_speech.side_effect = AudioValidationError("Invalid audio format")
        
        with patch('speak_practice.views._validate_request_origin', return_value=True):
            transcribe_url = reverse('speak_practice:transcribe_audio_api')
            response = self.client.post(
                transcribe_url,
                {'audio': self.mock_audio_file},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertEqual(data['error_code'], 'audio_validation_error')
        
        # 测试转录超时错误 (Test transcription timeout error)
        mock_speech.side_effect = TranscriptionTimeoutError("Transcription timeout")
        
        with patch('speak_practice.views._validate_request_origin', return_value=True):
            response = self.client.post(
                transcribe_url,
                {'audio': self.mock_audio_file},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
        
        self.assertEqual(response.status_code, 408)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertEqual(data['error_code'], 'transcription_timeout')
        
        # 测试一般语音识别错误 (Test general speech recognition error)
        mock_speech.side_effect = SpeechRecognitionError("Recognition failed")
        
        with patch('speak_practice.views._validate_request_origin', return_value=True):
            response = self.client.post(
                transcribe_url,
                {'audio': self.mock_audio_file},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertEqual(data['error_code'], 'transcription_error')
    
    @patch('speak_practice.services.text_to_speech.tts_service.generate_speech')
    def test_tts_error_handling_and_fallback(self, mock_tts):
        """
        测试TTS错误处理和降级策略 (Test TTS error handling and fallback strategy)
        
        测试TTS服务不可用时的降级处理
        (Test fallback handling when TTS service is unavailable)
        """
        # 设置TTS服务不可用 (Set TTS service unavailable)
        mock_tts.side_effect = TTSServiceUnavailableError("TTS service unavailable")
        
        with patch('speak_practice.views.get_ai_response') as mock_ai_response, \
             patch('speak_practice.views._validate_request_origin', return_value=True):
            mock_ai_response.return_value = json.dumps({
                'chinese': '很抱歉，语音服务暂时不可用',
                'pinyin': 'hěn bào qiàn, yǔ yīn fú wù zàn shí bù kě yòng'
            })
            
            chat_url = reverse('speak_practice:chat_api')
            response = self.client.post(
                chat_url,
                json.dumps({
                    'message': '测试消息',
                    'session_id': self.session.id
                }),
                content_type='application/json',
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            
            # 即使TTS失败，聊天功能仍应正常工作 (Chat should still work even if TTS fails)
            self.assertTrue(data['success'])
            self.assertIn('ai_response', data)
            self.assertIsNone(data['tts_audio'])  # TTS音频应为None (TTS audio should be None)
            self.assertFalse(data['tts_available'])  # TTS不可用标记 (TTS unavailable flag)
    
    @patch('speak_practice.services.translation.TranslationService.process')
    def test_translation_error_recovery(self, mock_translation):
        """
        测试翻译错误恢复机制 (Test translation error recovery mechanism)
        
        测试翻译失败时的恢复策略
        (Test recovery strategy when translation fails)
        """
        # 在语音转录中测试翻译失败 (Test translation failure in voice transcription)
        with patch('speak_practice.services.speech_recognition.SpeechRecognitionService.process') as mock_speech:
            mock_speech.return_value = {
                'transcribed_text': '测试中文文本',
                'audio_duration': 2.0,
                'audio_size': 512,
                'audio_format': 'webm'
            }
            
            # 设置翻译失败 (Set translation failure)
            mock_translation.side_effect = TranslationError("Translation failed")
            
            transcribe_url = reverse('speak_practice:transcribe_audio_api')
            response = self.client.post(
                transcribe_url,
                {'audio': self.mock_audio_file},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            
            # 即使翻译失败，仍应返回中文文本 (Should still return Chinese text even if translation fails)
            self.assertTrue(data['success'])
            self.assertEqual(data['chinese_text'], '测试中文文本')
            self.assertEqual(data['english_translation'], 'Translation unavailable')
            self.assertTrue(data['translation_error'])
    
    def test_csrf_protection_integration(self):
        """
        测试CSRF保护集成 (Test CSRF protection integration)
        
        验证所有API端点的CSRF保护
        (Verify CSRF protection for all API endpoints)
        """
        # 测试没有CSRF令牌的请求 (Test request without CSRF token)
        client_no_csrf = Client(enforce_csrf_checks=True)
        client_no_csrf.login(username='testuser', password='testpass123')
        
        # 测试聊天API (Test chat API)
        chat_url = reverse('speak_practice:chat_api')
        response = client_no_csrf.post(
            chat_url,
            json.dumps({
                'message': '测试消息',
                'session_id': self.session.id
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403)  # CSRF失败 (CSRF failure)
        
        # 测试带有正确CSRF令牌的请求 (Test request with correct CSRF token)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username='testuser', password='testpass123')
        
        # 获取CSRF令牌 (Get CSRF token)
        # Create a mock request to get CSRF token
        from django.http import HttpRequest
        mock_request = HttpRequest()
        csrf_token = get_token(mock_request)
        
        with patch('speak_practice.views.get_ai_response') as mock_ai_response, \
             patch('speak_practice.services.text_to_speech.tts_service.generate_speech') as mock_tts:
            
            mock_ai_response.return_value = json.dumps({
                'chinese': '测试回复',
                'pinyin': 'cè shì huí fù'
            })
            mock_tts.return_value = 'test_audio_data'
            
            response = csrf_client.post(
                chat_url,
                json.dumps({
                    'message': '测试消息',
                    'session_id': self.session.id
                }),
                content_type='application/json',
                HTTP_X_CSRFTOKEN=csrf_token
            )
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
    
    def test_session_isolation_and_security(self):
        """
        测试会话隔离和安全性 (Test session isolation and security)
        
        验证用户只能访问自己的会话
        (Verify users can only access their own sessions)
        """
        # 创建另一个用户和会话 (Create another user and session)
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        other_session = ChatSession.objects.create(
            user=other_user,
            scene='其他用户的会话 (Other user session)'
        )
        
        try:
            # 尝试访问其他用户的会话 (Try to access other user's session)
            with patch('speak_practice.views.get_ai_response') as mock_ai_response:
                mock_ai_response.return_value = json.dumps({
                    'chinese': '不应该看到这个回复',
                    'pinyin': 'bù yīng gāi kàn dào zhè gè huí fù'
                })
                
                chat_url = reverse('speak_practice:chat_api')
                response = self.client.post(
                    chat_url,
                    json.dumps({
                        'message': '尝试访问其他用户会话',
                        'session_id': other_session.id
                    }),
                    content_type='application/json',
                    HTTP_X_REQUESTED_WITH='XMLHttpRequest'
                )
                
                self.assertEqual(response.status_code, 404)  # 会话不存在（对当前用户）(Session not found for current user)
                data = json.loads(response.content)
                self.assertFalse(data['success'])
        
        finally:
            # 清理测试数据 (Clean up test data)
            other_session.delete()
            other_user.delete()
    
    @patch('speak_practice.services.speech_recognition.SpeechRecognitionService.process')
    @patch('speak_practice.services.translation.TranslationService.process')
    def test_message_content_format_validation(self, mock_translation, mock_speech):
        """
        测试消息内容格式验证 (Test message content format validation)
        
        验证不同输入方法的消息内容格式
        (Verify message content format for different input methods)
        """
        # 测试语音消息格式 (Test voice message format)
        mock_speech.return_value = {
            'transcribed_text': '语音测试消息',
            'audio_duration': 4.2,
            'audio_size': 2048,
            'audio_format': 'webm'
        }
        
        mock_translation.return_value = {
            'translated_text': 'Voice test message',
            'source_language': 'zh',
            'target_language': 'en',
            'character_count': 6
        }
        
        # 发送语音转录请求 (Send voice transcription request)
        transcribe_url = reverse('speak_practice:transcribe_audio_api')
        transcribe_response = self.client.post(
            transcribe_url,
            {'audio': self.mock_audio_file},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(transcribe_response.status_code, 200)
        
        # 发送语音消息到聊天 (Send voice message to chat)
        with patch('speak_practice.views.get_ai_response') as mock_ai_response, \
             patch('speak_practice.services.text_to_speech.tts_service.generate_speech') as mock_tts:
            
            mock_ai_response.return_value = json.dumps({
                'chinese': 'AI回复语音消息',
                'pinyin': 'AI huí fù yǔ yīn xiāo xī'
            })
            mock_tts.return_value = 'ai_response_audio'
            
            chat_url = reverse('speak_practice:chat_api')
            chat_response = self.client.post(
                chat_url,
                json.dumps({
                    'message': '语音测试消息',
                    'session_id': self.session.id
                }),
                content_type='application/json',
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            self.assertEqual(chat_response.status_code, 200)
        
        # 验证数据库中的消息格式 (Verify message format in database)
        user_message = ChatMessage.objects.filter(
            session=self.session,
            sender_type='user'
        ).first()
        
        self.assertIsNotNone(user_message)
        self.assertEqual(user_message.input_method, 'text')  # 默认为文本输入 (Default to text input)
        self.assertIn('chinese_text', user_message.message_content)
        self.assertEqual(user_message.message_content['chinese_text'], '语音测试消息')
        
        ai_message = ChatMessage.objects.filter(
            session=self.session,
            sender_type='ai'
        ).first()
        
        self.assertIsNotNone(ai_message)
        self.assertIn('chinese', ai_message.message_content)
        self.assertIn('pinyin', ai_message.message_content)
        self.assertEqual(ai_message.message_content['chinese'], 'AI回复语音消息')
    
    def test_concurrent_request_handling(self):
        """
        测试并发请求处理 (Test concurrent request handling)
        
        验证系统能够处理多个并发请求
        (Verify system can handle multiple concurrent requests)
        """
        import threading
        import time
        
        results = []
        errors = []
        
        def make_request(request_id):
            """发送并发请求的辅助函数 (Helper function for concurrent requests)"""
            try:
                with patch('speak_practice.views.get_ai_response') as mock_ai_response, \
                     patch('speak_practice.services.text_to_speech.tts_service.generate_speech') as mock_tts:
                    
                    mock_ai_response.return_value = json.dumps({
                        'chinese': f'并发回复 {request_id}',
                        'pinyin': f'bìng fā huí fù {request_id}'
                    })
                    mock_tts.return_value = f'audio_data_{request_id}'
                    
                    chat_url = reverse('speak_practice:chat_api')
                    response = self.client.post(
                        chat_url,
                        json.dumps({
                            'message': f'并发测试消息 {request_id}',
                            'session_id': self.session.id
                        }),
                        content_type='application/json',
                        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
                    )
                    
                    results.append({
                        'request_id': request_id,
                        'status_code': response.status_code,
                        'success': json.loads(response.content).get('success', False)
                    })
                    
            except Exception as e:
                errors.append({
                    'request_id': request_id,
                    'error': str(e)
                })
        
        # 创建并启动多个线程 (Create and start multiple threads)
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成 (Wait for all threads to complete)
        for thread in threads:
            thread.join(timeout=10)  # 10秒超时 (10 second timeout)
        
        # 验证结果 (Verify results)
        self.assertEqual(len(results), 5, f"Expected 5 results, got {len(results)}. Errors: {errors}")
        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")
        
        for result in results:
            self.assertEqual(result['status_code'], 200)
            self.assertTrue(result['success'])
        
        # 验证数据库中有正确数量的消息 (Verify correct number of messages in database)
        message_count = ChatMessage.objects.filter(session=self.session).count()
        self.assertEqual(message_count, 10)  # 5个用户消息 + 5个AI回复 (5 user messages + 5 AI replies)


class ServiceIntegrationTest(TestCase):
    """服务集成测试类 (Service integration test class)"""
    
    def setUp(self):
        """测试设置 (Test setup)"""
        self.speech_service = SpeechRecognitionService()
        self.tts_service = TextToSpeechService()
        self.translation_service = TranslationService()
    
    @patch('speak_practice.services.speech_recognition.requests.post')
    @patch('speak_practice.services.translation.requests.post')
    def test_speech_to_translation_pipeline(self, mock_translation_api, mock_speech_api):
        """
        测试语音到翻译的完整管道 (Test complete speech-to-translation pipeline)
        
        测试语音识别和翻译服务的集成
        (Test integration of speech recognition and translation services)
        """
        # 设置语音识别API模拟 (Set up speech recognition API mock)
        mock_speech_response = Mock()
        mock_speech_response.status_code = 200
        mock_speech_response.json.return_value = {'text': '你好世界'}
        mock_speech_api.return_value = mock_speech_response
        
        # 设置翻译API模拟 (Set up translation API mock)
        mock_translation_response = Mock()
        mock_translation_response.status_code = 200
        mock_translation_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Hello world'
                }
            }]
        }
        mock_translation_api.return_value = mock_translation_response
        
        # 创建模拟音频文件 (Create mock audio file)
        mock_audio = SimpleUploadedFile(
            "test.webm",
            b"fake_audio_content",
            content_type="audio/webm"
        )
        
        # 执行语音识别 (Execute speech recognition)
        speech_result = self.speech_service.process(mock_audio)
        self.assertEqual(speech_result['transcribed_text'], '你好世界')
        
        # 执行翻译 (Execute translation)
        translation_input = {
            'text': speech_result['transcribed_text'],
            'source_lang': 'zh',
            'target_lang': 'en'
        }
        translation_result = self.translation_service.process(translation_input)
        self.assertEqual(translation_result['translated_text'], 'Hello world')
    
    @patch('speak_practice.services.text_to_speech.requests.post')
    @patch('speak_practice.services.translation.requests.post')
    def test_translation_to_tts_pipeline(self, mock_translation_api, mock_tts_api):
        """
        测试翻译到TTS的完整管道 (Test complete translation-to-TTS pipeline)
        
        测试翻译和TTS服务的集成
        (Test integration of translation and TTS services)
        """
        # 设置翻译API模拟 (Set up translation API mock)
        mock_translation_response = Mock()
        mock_translation_response.status_code = 200
        mock_translation_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': '你好，欢迎光临'
                }
            }]
        }
        mock_translation_api.return_value = mock_translation_response
        
        # 设置TTS API模拟 (Set up TTS API mock)
        mock_tts_response = Mock()
        mock_tts_response.status_code = 200
        mock_tts_response.json.return_value = {
            'audioContent': 'base64_encoded_audio_content'
        }
        mock_tts_api.return_value = mock_tts_response
        
        # 执行翻译 (Execute translation)
        translation_input = {
            'text': 'Hello, welcome',
            'source_lang': 'en',
            'target_lang': 'zh'
        }
        translation_result = self.translation_service.process(translation_input)
        self.assertEqual(translation_result['translated_text'], '你好，欢迎光临')
        
        # 执行TTS (Execute TTS)
        tts_result = self.tts_service.generate_speech(
            translation_result['translated_text'],
            'cmn-CN'
        )
        self.assertEqual(tts_result, 'base64_encoded_audio_content')
    
    def test_service_error_propagation(self):
        """
        测试服务错误传播 (Test service error propagation)
        
        验证服务层错误能够正确传播到上层
        (Verify service layer errors propagate correctly to upper layers)
        """
        # 测试语音识别服务错误 (Test speech recognition service error)
        with patch('speak_practice.services.speech_recognition.requests.post') as mock_api:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = 'Bad Request'
            mock_api.return_value = mock_response
            
            mock_audio = SimpleUploadedFile(
                "test.webm",
                b"fake_audio_content",
                content_type="audio/webm"
            )
            
            with self.assertRaises(SpeechRecognitionError):
                self.speech_service.process(mock_audio)
        
        # 测试翻译服务错误 (Test translation service error)
        with patch('speak_practice.services.translation.requests.post') as mock_api:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = 'Internal Server Error'
            mock_api.return_value = mock_response
            
            translation_input = {
                'text': 'Test text',
                'source_lang': 'en',
                'target_lang': 'zh'
            }
            
            with self.assertRaises(TranslationError):
                self.translation_service.process(translation_input)
        
        # 测试TTS服务错误 (Test TTS service error)
        with patch('speak_practice.services.text_to_speech.requests.post') as mock_api:
            mock_response = Mock()
            mock_response.status_code = 503
            mock_response.text = 'Service Unavailable'
            mock_api.return_value = mock_response
            
            with self.assertRaises(TTSServiceUnavailableError):
                self.tts_service.generate_speech('测试文本', 'cmn-CN')


if __name__ == '__main__':
    unittest.main()