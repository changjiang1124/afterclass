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
    path('save-progress/', views.save_typing_progress, name='save_progress'),
    path('typing-history/', views.get_typing_history, name='typing_history'),
    path('continue/<int:record_id>/', views.continue_practice, name='continue_practice'),
    path('delete-record/', views.delete_typing_record, name='delete_record'),
    path('text-to-speech/', views.text_to_speech, name='text_to_speech'),
] 