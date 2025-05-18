from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.html import format_html
from .models import StudentProfile

# 内联编辑学生档案
class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = 'Student Profile'
    fk_name = 'user'

# 扩展用户管理
class CustomUserAdmin(UserAdmin):
    inlines = (StudentProfileInline, )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_chinese_level', 'edit_student_profile')
    list_select_related = ('student_profile',)
    
    def get_chinese_level(self, instance):
        if hasattr(instance, 'student_profile'):
            return instance.student_profile.get_chinese_level_display()
        return '-'
    get_chinese_level.short_description = 'Chinese Level'
    
    def edit_student_profile(self, instance):
        """创建一个自定义按钮，直接链接到学生档案编辑界面"""
        url = reverse('accounts:admin_edit_profile', args=[instance.id])
        return format_html('<a class="button" href="{}">编辑学生档案</a>', url)
    edit_student_profile.short_description = 'Student Profile'
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomUserAdmin, self).get_inline_instances(request, obj)

# 重新注册User模型
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
