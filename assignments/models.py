from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.

class AssignmentSet(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignment_sets')
    title = models.CharField(max_length=200)
    due_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    STATUS_CHOICES = (
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')

    def __str__(self):
        return f"{self.title} - {self.student.username}"

class Question(models.Model):
    QUESTION_TYPES = (
        ('single_choice', 'Single Choice'),
        ('text_input', 'Text Input'),
    )

    assignment_set = models.ForeignKey(AssignmentSet, on_delete=models.CASCADE, related_name='questions')
    description = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='single_choice')
    reference_answer = models.TextField(null=True, blank=True) # not for strict checking, as here might be for open questions
    student_answer = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Question for {self.assignment_set.title}"

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=200)
    # is_correct = models.BooleanField(default=False) # the check should be in questions, not choices, by comparing the answer with reference_answer

    def __str__(self):
        return self.text
