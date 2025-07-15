from django.urls import path
from . import views

app_name = 'namegen'

urlpatterns = [
    path('', views.home, name='home'),
    path('generate/', views.generate_name, name='generate_name'),
    path('result/<int:request_id>/', views.result, name='result'),
    path('text-to-speech/', views.text_to_speech, name='text_to_speech'),
    path('text-to-speech-advanced/', views.text_to_speech_advanced, name='text_to_speech_advanced'),
    path('namecard/', views.generate_name_card, name='generate_name_card'),
    
    # Statistics endpoints
    path('track-share/', views.track_share_click, name='track_share_click'),
    path('statistics/', views.statistics_dashboard, name='statistics_dashboard'),
    path('statistics/api/', views.statistics_api, name='statistics_api'),
    
    # SEO-friendly URLs
    path('sitemap.xml', views.sitemap, name='sitemap'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
] 