from django.test import TestCase, Client
from django.urls import reverse
from .models import NameGenerationRequest
from datetime import date

class NameGenerationTests(TestCase):
    def setUp(self):
        self.client = Client()
    
    def test_home_page_loads(self):
        """测试主页是否能正常加载"""
        response = self.client.get(reverse('namegen:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Chinese Name Generator')
    
    def test_model_creation(self):
        """测试模型创建和方法"""
        request = NameGenerationRequest.objects.create(
            first_name='John',
            surname='Smith',
            gender='male',
            personality_trait='brave',
            preferred_style='traditional',
            date_of_birth=date(1990, 3, 15),
            generated_chinese_name='明德',
            name_pinyin='Míng Dé',
            name_meaning='Bright virtue',
            ip_address='127.0.0.1'
        )
        
        self.assertEqual(request.first_name, 'John')
        self.assertEqual(request.get_chinese_zodiac(), '马')  # 1990年是马年
        self.assertEqual(request.get_season(), '春')  # 3月是春季
        self.assertIn('明德', str(request))
    
    def test_form_validation_required_fields(self):
        """测试表单必填字段验证"""
        response = self.client.post(reverse('namegen:generate_name'), {
            'first_name': '',  # 空的必填字段
            'gender': 'male',
            'personality_trait': 'brave',
            'preferred_style': 'traditional'
        })
        
        # 应该返回错误
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('required fields', data['error'])
