from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class GeneratedText(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField()
    topic = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.topic} - {self.created_at.strftime('%d/%m/%Y')}"

class TypingRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    source_text = models.TextField() # 目标文本内容
    current_input = models.TextField(blank=True) # 用户当前输入的内容 
    correct_chars = models.IntegerField(default=0) # 正确的字符数
    total_chars = models.IntegerField(default=0)  # 总字符数 
    is_completed = models.BooleanField(default=False) # 是否完成
    generated_text = models.ForeignKey(GeneratedText, on_delete=models.SET_NULL, null=True, blank=True) # 关联生成的文本
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at'] # 按更新时间倒序排列
    
    def __str__(self):
        completion_percentage = (self.correct_chars / self.total_chars * 100) if self.total_chars > 0 else 0
        return f"Typing Record {self.id} - {completion_percentage:.0f}% completed"
        
    def completion_percentage(self):
        if self.total_chars > 0:
            return int((self.correct_chars / self.total_chars) * 100)
        return 0
