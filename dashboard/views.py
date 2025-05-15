from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Feature
from tongcove.settings import DASHBOARD_COLORS
from itertools import groupby
from django.db.models import F

@login_required
def dashboard(request):
    features = Feature.objects.all()
    for index, feature in enumerate(features):
        feature.color = DASHBOARD_COLORS[index % len(DASHBOARD_COLORS)]
    
    # 按类别分组
    grouped_features = {}
    for category, value in Feature.CATEGORY_CHOICES:
        grouped_features[category] = {
            'name': value,
            'features': [f for f in features if f.category == category]
        }
    
    return render(request, 'dashboard/dashboard.html', {
        'features': features,
        'grouped_features': grouped_features,
    })

# Create your views here.
