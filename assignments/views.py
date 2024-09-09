from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import AssignmentSet, Question
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST

# Create your views here.

@login_required
def assignment_list(request):
    incomplete_assignments = AssignmentSet.objects.filter(
        student=request.user,
        status__in=['not_started', 'in_progress']
    )
    return render(request, 'assignments/assignment_list.html', {'assignments': incomplete_assignments})

@login_required
def assignment_detail(request, assignment_id):
    assignment = get_object_or_404(AssignmentSet, id=assignment_id, student=request.user)
    questions = assignment.questions.all()
    
    if request.method == 'POST':
        all_answered = True
        for question in questions:
            answer = request.POST.get(f'question_{question.id}')
            if answer:
                question.student_answer = answer
                question.completed_at = timezone.now()
            else:
                all_answered = False
            question.save()
        
        if all_answered:
            assignment.status = 'completed'
        else:
            assignment.status = 'in_progress'
        assignment.save()
        
        return redirect('assignments:assignment_list')
    
    return render(request, 'assignments/assignment_detail.html', {'assignment': assignment, 'questions': questions})

@require_POST
@login_required
def submit_answer(request):
    question_id = request.POST.get('question_id')
    answer = request.POST.get('answer')
    
    question = get_object_or_404(Question, id=question_id)
    question.student_answer = answer
    question.completed_at = timezone.now()
    question.save()
    
    assignment = question.assignment_set
    if all(q.student_answer for q in assignment.questions.all()):
        assignment.status = 'completed'
    else:
        assignment.status = 'in_progress'
    assignment.save()
    
    return JsonResponse({'status': 'success'})
