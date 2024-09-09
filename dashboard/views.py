from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Feature
from tongcove.settings import DASHBOARD_COLORS

@login_required
def dashboard(request):
    features = Feature.objects.all()
    for index, feature in enumerate(features):
        feature.color = DASHBOARD_COLORS[index % len(DASHBOARD_COLORS)]

    return render(request, 'dashboard/dashboard.html', {'features': features})

# Create your views here.
