from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
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
        username = request.POST['username'].strip()  # Remove whitespace but keep original case
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
        profile.chinese_level = request.POST.get('chinese_level', profile.chinese_level or 'beginner')
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

@login_required
def change_password_view(request):
    """View for users to change their password"""
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validate current password
        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return render(request, 'accounts/change_password.html')
        
        # Validate new password
        if len(new_password) < 8:
            messages.error(request, 'New password must be at least 8 characters long.')
            return render(request, 'accounts/change_password.html')
        
        # Check if new passwords match
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return render(request, 'accounts/change_password.html')
        
        # Check if new password is different from current
        if request.user.check_password(new_password):
            messages.error(request, 'New password must be different from current password.')
            return render(request, 'accounts/change_password.html')
        
        # Update password
        request.user.set_password(new_password)
        request.user.save()
        
        # Keep user logged in after password change
        update_session_auth_hash(request, request.user)
        
        messages.success(request, 'Password changed successfully!')
        return redirect(reverse('accounts:profile'))
    
    return render(request, 'accounts/change_password.html')
