from django.contrib import admin
from .models import AssignmentSet, Question, Choice

class AssignmentSetAdmin(admin.ModelAdmin):
    list_display = ['title', 'due_date', 'status']

class QuestionAdmin(admin.ModelAdmin):
    list_display = ['description', 'question_type', 'assignment_set']

class ChoiceAdmin(admin.ModelAdmin):
    list_display = ['text', 'question']

admin.site.register(AssignmentSet, AssignmentSetAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Choice, ChoiceAdmin)