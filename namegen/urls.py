from django.urls import path
from . import views

app_name = 'namegen'

urlpatterns = [
    path('', views.home, name='home'),
    path('generate/', views.generate_name, name='generate_name'),
    path('result/<int:request_id>/', views.result, name='result'),
    path('tts/', views.text_to_speech, name='text_to_speech'),
    path('generate-card/', views.generate_name_card, name='generate_name_card'),
] 