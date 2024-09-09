from django.contrib import admin
from .models import AssignmentSet, Question, Choice

# Register your models here.

admin.site.register(AssignmentSet)
admin.site.register(Question)
admin.site.register(Choice)