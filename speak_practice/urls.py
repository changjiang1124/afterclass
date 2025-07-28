from django.urls import path
from . import views

app_name = 'speak_practice'

urlpatterns = [
    path('', views.scene_selection, name='scene_selection'),
    path('chat/<int:session_id>/', views.chat_view, name='chat_view'),
    path('api/chat/', views.chat_api, name='chat_api'),
    path('api/transcribe/', views.transcribe_audio_api, name='transcribe_audio_api'),
    path('api/translate/', views.translate_text_api, name='translate_text_api'),
    path('api/translate-chinese/', views.translate_chinese_api, name='translate_chinese_api'),
    path('api/topics/', views.load_topics_api, name='load_topics_api'),
    path('api/generate-scene/', views.generate_scene_api, name='generate_scene_api'),
]
