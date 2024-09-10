from django.shortcuts import render, get_object_or_404
from .models import Story
from django.contrib.auth.decorators import login_required
# Create your views here.

@login_required
def story_list(request):
    stories = Story.objects.all().order_by('-created_at')
    return render(request, 'stories/story_list.html', {'stories': stories})

@login_required
def story_detail(request, story_id):
    story = get_object_or_404(Story, id=story_id)
    return render(request, 'stories/story_detail.html', {'story': story})
