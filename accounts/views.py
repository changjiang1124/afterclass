from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

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
            return render(request, 'accounts/login.html', {'error': '用户名或密码不正确'})
    return render(request, 'accounts/login.html')

@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html')


def logout_view(request):
    logout(request)
    return redirect('/')