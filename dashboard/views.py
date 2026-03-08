from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.models import StudentProfile
from speak_practice.query_utils import ChatQueryOptimizer
from typingchinese.models import TypingRecord

@login_required
def dashboard(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    speaking_data = ChatQueryOptimizer.get_user_dashboard_data(request.user)
    speaking_session_count = speaking_data.get('session_count', 0)
    voice_message_count = speaking_data.get('voice_message_count', 0)
    recent_sessions = speaking_data.get('recent_sessions', [])
    recent_speaking_session = recent_sessions[0] if recent_sessions else None

    typing_record_count = TypingRecord.objects.filter(user=request.user).count()
    completed_typing_count = TypingRecord.objects.filter(user=request.user, is_completed=True).count()
    profile_ready = any([
        bool((profile.learning_goals or '').strip()),
        bool((profile.interests or '').strip()),
        bool((profile.personalised_prompts or '').strip()),
    ])
    
    return render(request, 'dashboard/dashboard.html', {
        'speaking_session_count': speaking_session_count,
        'voice_message_count': voice_message_count,
        'recent_speaking_session': recent_speaking_session,
        'typing_record_count': typing_record_count,
        'completed_typing_count': completed_typing_count,
        'profile_ready': profile_ready,
    })

# Create your views here.
