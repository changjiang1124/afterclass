from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    features = [
        {
            'label': '学',
            'title': '中文学习',
            'description': '开始您的中文学习之旅',
            'link': '/chatbots/',
            'color': '#99E7C5'
        },
        {
            'label': '练',
            'title': '练习',
            'description': '巩固您的中文知识',
            'link': '#',
            'color': '#B5B0F6'
        },
        {
            'label': '测',
            'title': '测试',
            'description': '检验您的学习成果',
            'link': '#',
            'color': '#EDA3A3'
        },
        {
            'label': '资',
            'title': '学习资源',
            'description': '丰富的中文学习材料',
            'link': '#',
            'color': '#F4CB9B'
        }
    ]
    return render(request, 'dashboard/dashboard.html', {'features': features})

# Create your views here.
