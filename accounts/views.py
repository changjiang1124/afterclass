from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponseForbidden
from .models import StudentProfile
from django.urls import reverse
from datetime import datetime

# Create your views here.

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            return render(request, 'accounts/login.html', {'error': 'Incorrect username or password'})
    return render(request, 'accounts/login.html')

@login_required
def profile_view(request):
    """View and edit user profile"""
    # Try to get the user profile or create one if it doesn't exist
    profile, created = StudentProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Handle form submission - only basic personal information
        profile.chinese_name = request.POST.get('chinese_name', '')
        profile.preferred_name = request.POST.get('preferred_name', '')
        
        # Handle date of birth field
        dob = request.POST.get('date_of_birth', '')
        if dob:
            try:
                profile.date_of_birth = datetime.strptime(dob, '%Y-%m-%d').date()
            except ValueError:
                # If date format is invalid, leave it as is
                pass
        else:
            profile.date_of_birth = None
        
        # Save changes
        profile.save()
        
        # Update user basic info
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()
        
        messages.success(request, 'Profile updated successfully')
        return redirect(reverse('accounts:profile'))
    
    return render(request, 'accounts/profile.html', {'profile': profile})


def logout_view(request):
    logout(request)
    return redirect('/')

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_edit_profile(request, user_id):
    """Admin view to edit user profiles"""
    # Try to get the user profile or create one if it doesn't exist
    profile, created = StudentProfile.objects.get_or_create(user_id=user_id)
    
    if request.method == 'POST':
        # Handle form submission - admin can update all fields
        profile.chinese_name = request.POST.get('chinese_name', '')
        profile.preferred_name = request.POST.get('preferred_name', '')
        profile.chinese_level = request.POST.get('chinese_level', 'beginner')
        profile.learning_goals = request.POST.get('learning_goals', '')
        profile.interests = request.POST.get('interests', '')
        profile.preferred_learning_style = request.POST.get('preferred_learning_style', '')
        profile.personalised_prompts = request.POST.get('personalised_prompts', '')
        
        # Handle date of birth field
        dob = request.POST.get('date_of_birth', '')
        if dob:
            try:
                profile.date_of_birth = datetime.strptime(dob, '%Y-%m-%d').date()
            except ValueError:
                # If date format is invalid, leave it as is
                pass
        else:
            profile.date_of_birth = None
        
        # Save changes
        profile.save()
        
        # Update user basic info
        user = profile.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()
        
        messages.success(request, f'User {user.username}\'s profile has been updated')
        return redirect('admin:auth_user_change', user.id)
    
    return render(request, 'accounts/admin_edit_profile.html', {'profile': profile})