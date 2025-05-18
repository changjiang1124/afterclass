from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

class StudentProfile(models.Model):
    """
    学生个人资料模型，与Django默认User模型一对一关联
    用于存储个性化AI提示所需的额外信息
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    
    # 基本信息
    chinese_name = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Chinese Name'))
    preferred_name = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Preferred Name'))
    date_of_birth = models.DateField(blank=True, null=True, verbose_name=_('Date of Birth'))
    
    # 学习信息
    LEVEL_CHOICES = [
        ('beginner', _('Beginner')),
        ('intermediate', _('Intermediate')),
        ('advanced', _('Advanced')),
    ]
    chinese_level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner', verbose_name=_('Chinese Level'))
    
    # 学习目标和兴趣
    learning_goals = models.TextField(blank=True, null=True, verbose_name=_('Learning Goals'))
    interests = models.TextField(blank=True, null=True, verbose_name=_('Interests'))
    
    # 学习偏好
    LEARNING_STYLE_CHOICES = [
        ('visual', _('Visual')),
        ('auditory', _('Auditory')),
        ('reading_writing', _('Reading/Writing')),
        ('kinesthetic', _('Kinesthetic')),
    ]
    preferred_learning_style = models.CharField(
        max_length=20, 
        choices=LEARNING_STYLE_CHOICES, 
        blank=True, 
        null=True,
        verbose_name=_('Preferred Learning Style')
    )
    
    # AI个性化设置
    personalised_prompts = models.TextField(blank=True, null=True, verbose_name=_('Personalised AI Prompts'))
    
    # 系统字段
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

    class Meta:
        verbose_name = _('Student Profile')
        verbose_name_plural = _('Student Profiles')


# 信号处理器，自动创建对应的StudentProfile
@receiver(post_save, sender=User)
def create_student_profile(sender, instance, created, **kwargs):
    """当创建新用户时自动创建学生档案"""
    if created:
        StudentProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_student_profile(sender, instance, **kwargs):
    """当保存用户时自动保存学生档案"""
    instance.student_profile.save()
