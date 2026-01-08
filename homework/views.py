
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Count, Case, When, IntegerField
from datetime import timedelta
from .models import (
    TeacherProfile,
    TeacherClass,
    HomeworkAssignment,
    HomeworkTask,
    StudentHomeworkProgress,
    HomeworkSubmission,
    HomeworkNotificationSnooze
)


def get_homework_summary(user):
    """
    Get summary of student's homework status for notifications.
    Returns dict with overdue, due_soon, and incomplete counts/lists.
    """
    # Get all assignments for this student
    class_assignments = HomeworkAssignment.objects.filter(
        assigned_classes__students=user,
        is_published=True
    )
    individual_assignments = HomeworkAssignment.objects.filter(
        assigned_students=user,
        is_published=True
    )
    all_assignments = (class_assignments | individual_assignments).distinct()

    overdue = []
    due_soon = []  # Due within 3 days
    incomplete = []

    now = timezone.now()
    soon_threshold = now + timedelta(days=3)

    for assignment in all_assignments:
        # Check if submitted
        has_submitted = HomeworkSubmission.objects.filter(
            student=user,
            assignment=assignment
        ).exists()

        if not has_submitted:
            if assignment.due_date < now:
                overdue.append(assignment)
            elif assignment.due_date <= soon_threshold:
                due_soon.append(assignment)
            else:
                incomplete.append(assignment)

    return {
        'overdue': overdue,
        'overdue_count': len(overdue),
        'due_soon': due_soon,
        'due_soon_count': len(due_soon),
        'incomplete': incomplete,
        'incomplete_count': len(incomplete),
        'total_count': len(overdue) + len(due_soon) + len(incomplete),
        'has_homework': bool(overdue or due_soon or incomplete),
    }


@login_required
def student_homework_dashboard(request):
    """
    Main homework dashboard for students showing all their assignments.
    """
    user = request.user

    # Get all assignments for this student (from classes + individual assignments)
    class_assignments = HomeworkAssignment.objects.filter(
        assigned_classes__students=user,
        is_published=True
    )
    individual_assignments = HomeworkAssignment.objects.filter(
        assigned_students=user,
        is_published=True
    )

    all_assignments = (class_assignments | individual_assignments).distinct().order_by('due_date')

    # Annotate with completion status
    assignments_with_status = []
    for assignment in all_assignments:
        tasks = assignment.tasks.all()
        total_tasks = tasks.count()

        # Get or create progress records for this student
        completed_count = 0
        for task in tasks:
            progress, created = StudentHomeworkProgress.objects.get_or_create(
                student=user,
                assignment=assignment,
                task=task
            )
            # Check for auto-completion
            progress.check_auto_completion()

            if progress.is_completed:
                completed_count += 1

        # Check if submitted
        has_submitted = HomeworkSubmission.objects.filter(
            student=user,
            assignment=assignment
        ).exists()

        is_overdue = timezone.now() > assignment.due_date
        days_until_due = (assignment.due_date - timezone.now()).days

        assignments_with_status.append({
            'assignment': assignment,
            'total_tasks': total_tasks,
            'completed_tasks': completed_count,
            'completion_percentage': int((completed_count / total_tasks * 100) if total_tasks > 0 else 0),
            'is_overdue': is_overdue,
            'days_until_due': days_until_due,
            'has_submitted': has_submitted,
        })

    # Separate into active and completed
    active_assignments = [a for a in assignments_with_status if not a['has_submitted']]
    completed_assignments = [a for a in assignments_with_status if a['has_submitted']]

    context = {
        'active_assignments': active_assignments,
        'completed_assignments': completed_assignments,
    }

    return render(request, 'homework/student_dashboard.html', context)


@login_required
def assignment_detail(request, assignment_id):
    """
    Detailed view of a single assignment with all tasks.
    """
    assignment = get_object_or_404(HomeworkAssignment, id=assignment_id, is_published=True)
    user = request.user

    # Verify student has access to this assignment
    has_access = (
        assignment.assigned_classes.filter(students=user).exists() or
        assignment.assigned_students.filter(id=user.id).exists()
    )

    if not has_access:
        return redirect('homework:student_dashboard')

    # Get all tasks with progress
    tasks = assignment.tasks.all().order_by('order')
    tasks_with_progress = []

    for task in tasks:
        progress, created = StudentHomeworkProgress.objects.get_or_create(
            student=user,
            assignment=assignment,
            task=task
        )

        # Check for auto-completion based on student activity
        progress.check_auto_completion()

        tasks_with_progress.append({
            'task': task,
            'progress': progress,
            'content_url': task.get_content_url(),
        })

    # Check submission status
    submission = HomeworkSubmission.objects.filter(
        student=user,
        assignment=assignment
    ).first()

    is_overdue = timezone.now() > assignment.due_date
    total_tasks = tasks.count()
    completed_tasks = sum(1 for t in tasks_with_progress if t['progress'].is_completed)
    completion_percentage = int((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0)

    context = {
        'assignment': assignment,
        'tasks_with_progress': tasks_with_progress,
        'submission': submission,
        'is_overdue': is_overdue,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'completion_percentage': completion_percentage,
        'can_submit': completed_tasks == total_tasks and not submission,
    }

    return render(request, 'homework/assignment_detail.html', context)


@login_required
def toggle_task_completion(request, progress_id):
    """
    AJAX endpoint to toggle task completion status.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    progress = get_object_or_404(StudentHomeworkProgress, id=progress_id, student=request.user)

    # Toggle completion
    if progress.is_completed:
        progress.mark_incomplete()
        status = 'incomplete'
    else:
        progress.mark_complete()
        status = 'complete'

    return JsonResponse({
        'status': status,
        'completed_at': progress.completed_at.isoformat() if progress.completed_at else None
    })


@login_required
def submit_homework(request, assignment_id):
    """
    Submit completed homework for teacher review.
    """
    if request.method != 'POST':
        return redirect('homework:assignment_detail', assignment_id=assignment_id)

    assignment = get_object_or_404(HomeworkAssignment, id=assignment_id)
    user = request.user

    # Verify all tasks are completed
    tasks = assignment.tasks.all()
    all_completed = all(
        StudentHomeworkProgress.objects.filter(
            student=user,
            assignment=assignment,
            task=task,
            is_completed=True
        ).exists()
        for task in tasks
    )

    if not all_completed:
        return redirect('homework:assignment_detail', assignment_id=assignment_id)

    # Create submission (will auto-detect if late)
    submission, created = HomeworkSubmission.objects.get_or_create(
        student=user,
        assignment=assignment
    )

    return redirect('homework:assignment_detail', assignment_id=assignment_id)


# ============================================================================
# TEACHER VIEWS
# ============================================================================

@login_required
def teacher_dashboard(request):
    """
    Dashboard for teachers showing their classes and assignments.
    """
    # Check if user is a teacher
    try:
        teacher_profile = request.user.teacher_profile
    except:
        return redirect('homework:student_dashboard')

    # Get teacher's classes
    classes = teacher_profile.classes.all().annotate(
        student_count=Count('students')
    )

    # Get teacher's assignments
    assignments = teacher_profile.assignments.all().order_by('-due_date')[:10]

    # Annotate assignments with progress
    assignments_with_progress = []
    for assignment in assignments:
        total_students = assignment.get_all_assigned_students().count()
        submissions = assignment.submissions.count()

        assignments_with_progress.append({
            'assignment': assignment,
            'total_students': total_students,
            'submissions': submissions,
            'submission_percentage': int((submissions / total_students * 100) if total_students > 0 else 0),
        })

    context = {
        'teacher': teacher_profile,
        'classes': classes,
        'assignments': assignments_with_progress,
    }

    return render(request, 'homework/teacher_dashboard.html', context)


@login_required
def class_detail(request, class_id):
    """
    Detailed view of a class for teachers.
    """
    teacher_class = get_object_or_404(TeacherClass, id=class_id)

    # Verify teacher owns this class
    if not request.user.is_superuser:
        try:
            if teacher_class.teacher != request.user.teacher_profile:
                return redirect('homework:teacher_dashboard')
        except:
            return redirect('homework:student_dashboard')

    students = teacher_class.students.all()
    assignments = teacher_class.assignments.filter(is_published=True).order_by('-due_date')

    context = {
        'teacher_class': teacher_class,
        'students': students,
        'assignments': assignments,
    }

    return render(request, 'homework/class_detail.html', context)


@login_required
def assignment_progress(request, assignment_id):
    """
    View showing student progress on an assignment for teachers.
    """
    assignment = get_object_or_404(HomeworkAssignment, id=assignment_id)

    # Verify teacher owns this assignment
    if not request.user.is_superuser:
        try:
            if assignment.teacher != request.user.teacher_profile:
                return redirect('homework:teacher_dashboard')
        except:
            return redirect('homework:student_dashboard')

    # Get all assigned students
    students = assignment.get_all_assigned_students()
    tasks = assignment.tasks.all().order_by('order')

    # Build progress matrix
    student_progress = []
    for student in students:
        task_statuses = []
        completed_count = 0

        for task in tasks:
            progress = StudentHomeworkProgress.objects.filter(
                student=student,
                assignment=assignment,
                task=task
            ).first()

            task_statuses.append({
                'task': task,
                'completed': progress.is_completed if progress else False,
            })

            if progress and progress.is_completed:
                completed_count += 1

        # Check submission
        submission = HomeworkSubmission.objects.filter(
            student=student,
            assignment=assignment
        ).first()

        student_progress.append({
            'student': student,
            'task_statuses': task_statuses,
            'completed_count': completed_count,
            'total_count': tasks.count(),
            'completion_percentage': int((completed_count / tasks.count() * 100) if tasks.count() > 0 else 0),
            'submission': submission,
        })

    context = {
        'assignment': assignment,
        'tasks': tasks,
        'student_progress': student_progress,
    }

    return render(request, 'homework/assignment_progress.html', context)


# ============================================================================
# NOTIFICATION VIEWS
# ============================================================================

@login_required
def snooze_homework_notification(request):
    """
    Snooze homework notifications for 24 hours.
    """
    if request.method == 'POST':
        HomeworkNotificationSnooze.snooze_for_hours(request.user, hours=24)
        return JsonResponse({'status': 'success', 'message': 'Notifications snoozed for 24 hours'})

    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)


@login_required
def class_homework_report(request, class_id):
    """
    Simple homework completion report by class.
    Shows homework assignments as rows and students as columns.
    """
    teacher_class = get_object_or_404(TeacherClass, id=class_id)

    # Verify teacher owns this class
    if not request.user.is_superuser:
        try:
            if teacher_class.teacher != request.user.teacher_profile:
                return redirect('homework:teacher_dashboard')
        except:
            return redirect('homework:student_dashboard')

    # Get all students in the class
    students = teacher_class.students.all().order_by('last_name', 'first_name', 'username')

    # Get all assignments for this class
    assignments = teacher_class.assignments.filter(is_published=True).order_by('-due_date')

    # Build completion matrix
    report_data = []
    for assignment in assignments:
        tasks = assignment.tasks.all()
        total_tasks = tasks.count()

        student_statuses = []
        for student in students:
            # Count completed tasks for this student
            completed_tasks = StudentHomeworkProgress.objects.filter(
                student=student,
                assignment=assignment,
                is_completed=True
            ).count()

            # Determine status: ✓ (all done), ✗ (partially done), empty (not started)
            if completed_tasks == 0:
                status = ''
            elif completed_tasks == total_tasks:
                status = '✓'
            else:
                status = '✗'

            student_statuses.append({
                'student': student,
                'status': status,
                'completed_tasks': completed_tasks,
                'total_tasks': total_tasks,
            })

        report_data.append({
            'assignment': assignment,
            'total_tasks': total_tasks,
            'student_statuses': student_statuses,
        })

    context = {
        'teacher_class': teacher_class,
        'students': students,
        'report_data': report_data,
    }

    return render(request, 'homework/class_homework_report.html', context)
