from django.urls import path
from . import views

app_name = 'chatbots'

urlpatterns = [
    path('', views.chatbot_list, name='chatbot_list'),
    path('<int:chatbot_id>/', views.chatbot_detail, name='chatbot_detail'),
    path('<int:chatbot_id>/clear/', views.clear_conversation, name='clear_conversation'),
    path('tts/', views.text_to_speech, name='text_to_speech'),
]
