from django.db import models
from django.utils import timezone

class NameGenerationRequest(models.Model):
    """用户的姓名生成请求记录"""
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('not_specified', 'Rather not to specify'),
    ]
    
    PERSONALITY_CHOICES = [
        ('brave', 'Brave (勇敢)'),
        ('kind', 'Kind (善良)'),
        ('artistic', 'Artistic (文艺)'),
        ('calm', 'Calm (平静)'),
        ('cheerful', 'Cheerful (开朗)'),
        ('wise', 'Wise (智慧)'),
        ('gentle', 'Gentle (温和)'),
        ('strong', 'Strong (坚强)'),
        ('creative', 'Creative (创意)'),
        ('loyal', 'Loyal (忠诚)'),
    ]
    
    STYLE_CHOICES = [
        ('traditional', 'Traditional/Classical'),
        ('artistic', 'Artistic/Poetic'),
        ('modern', 'Modern/Cool'),
        ('professional', 'Professional/Formal'),
    ]
    
    # 用户信息
    first_name = models.CharField(max_length=50, verbose_name="First Name")
    surname = models.CharField(max_length=50, blank=True, null=True, verbose_name="Surname")
    gender = models.CharField(max_length=15, choices=GENDER_CHOICES, verbose_name="Gender")
    date_of_birth = models.DateField(blank=True, null=True, verbose_name="Date of Birth")
    personality_trait = models.CharField(max_length=20, choices=PERSONALITY_CHOICES, verbose_name="Personality Trait")
    preferred_style = models.CharField(max_length=20, choices=STYLE_CHOICES, verbose_name="Preferred Style")
    
    # 生成的姓名信息
    generated_chinese_name = models.CharField(max_length=20, blank=True, null=True, verbose_name="Generated Chinese Name")
    name_pinyin = models.CharField(max_length=100, blank=True, null=True, verbose_name="Name Pinyin")
    name_meaning = models.TextField(blank=True, null=True, verbose_name="Name Meaning")
    
    # 时间戳
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Created At")
    
    # 用户IP地址（用于统计分析）
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="IP Address")
    
    class Meta:
        verbose_name = "Name Generation Request"
        verbose_name_plural = "Name Generation Requests"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.first_name}'s Chinese Name: {self.generated_chinese_name or 'Pending'}"
    
    def get_chinese_zodiac(self):
        """根据出生年份计算生肖"""
        # TODO: could take Chinese calendar into consideration, as the year is different from the western calendar.
        if not self.date_of_birth:
            return None
            
        # 生肖循环：鼠、牛、虎、兔、龙、蛇、马、羊、猴、鸡、狗、猪
        zodiac_animals = [
            '鼠', '牛', '虎', '兔', '龙', '蛇', 
            '马', '羊', '猴', '鸡', '狗', '猪'
        ]
        
        # 1900年是鼠年，计算年份差
        year_diff = self.date_of_birth.year - 1900
        zodiac_index = year_diff % 12
        
        return zodiac_animals[zodiac_index]
    
    def get_season(self):
        """根据出生月份计算季节"""
        # TODO: could take the birth place into consideration, like northern hemisphere or southern hemisphere.
        
        if not self.date_of_birth:
            return None
            
        month = self.date_of_birth.month
        if month in [12, 1, 2]:
            return '冬'
        elif month in [3, 4, 5]:
            return '春'
        elif month in [6, 7, 8]:
            return '夏'
        else:
            return '秋'
