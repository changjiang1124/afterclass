from django.urls import path
from . import views

app_name = 'typingchinese'

urlpatterns = [
    path('', views.home, name='home'),
    path('generate/', views.generate_text, name='generate_text'),
    path('generate-ai/', views.generate_ai_text, name='generate_ai_text'),
    path('practice/', views.practice, name='practice'),
    path('process-pinyin/', views.process_pinyin, name='process_pinyin'),
    path('topic-suggestions/', views.generate_topic_suggestions, name='topic_suggestions'),
    path('translate/', views.translate_text, name='translate_text'),
] 