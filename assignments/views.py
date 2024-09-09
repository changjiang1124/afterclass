from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import AssignmentSet, Question
from django.utils import timezone

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
