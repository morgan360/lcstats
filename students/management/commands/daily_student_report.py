from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from students.models import StudentProfile, QuestionAttempt
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Generate and send daily student activity report'

    def add_arguments(self, parser):
        parser.add_argument(
            '--exclude-user',
            type=str,
            help='Username to exclude from the report (e.g., teacher account)',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email address to send the report to',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='Number of days to include in the report (default: 1)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print report without sending email',
        )

    def handle(self, *args, **options):
        exclude_username = options.get('exclude_user')
        recipient_email = options.get('email')
        days = options.get('days', 1)
        dry_run = options.get('dry_run', False)

        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        self.stdout.write(
            self.style.SUCCESS(
                f'\nGenerating report for period: {start_date.strftime("%Y-%m-%d %H:%M")} '
                f'to {end_date.strftime("%Y-%m-%d %H:%M")}\n'
            )
        )

        # Get all students, excluding specified user if provided
        students_query = StudentProfile.objects.select_related('user')
        if exclude_username:
            students_query = students_query.exclude(user__username=exclude_username)
            self.stdout.write(f'Excluding user: {exclude_username}\n')

        # Get attempts in the date range
        attempts_in_period = QuestionAttempt.objects.filter(
            attempted_at__gte=start_date,
            attempted_at__lte=end_date
        )

        if exclude_username:
            attempts_in_period = attempts_in_period.exclude(
                student__user__username=exclude_username
            )

        # Overall statistics
        total_attempts = attempts_in_period.count()
        correct_attempts = attempts_in_period.filter(is_correct=True).count()
        accuracy = (correct_attempts / total_attempts * 100) if total_attempts > 0 else 0

        # Unique students who attempted questions
        active_students = attempts_in_period.values_list(
            'student__user__username', 'student__user__first_name', 'student__user__last_name'
        ).distinct()

        # Topics worked on
        topics_data = attempts_in_period.values(
            'question__topic__name'
        ).annotate(
            attempt_count=Count('id'),
            correct_count=Count('id', filter=Q(is_correct=True)),
            avg_score=Avg('score_awarded')
        ).order_by('-attempt_count')

        # Questions completed (distinct questions)
        unique_questions = attempts_in_period.values(
            'question__id'
        ).distinct().count()

        # Per-student breakdown
        student_stats = []
        for student in students_query:
            student_attempts = attempts_in_period.filter(student=student)
            attempt_count = student_attempts.count()

            if attempt_count > 0:  # Only include students with activity
                correct_count = student_attempts.filter(is_correct=True).count()
                student_accuracy = (correct_count / attempt_count * 100) if attempt_count > 0 else 0
                avg_score = student_attempts.aggregate(Avg('score_awarded'))['score_awarded__avg'] or 0

                # Topics for this student
                student_topics = student_attempts.values(
                    'question__topic__name'
                ).annotate(
                    count=Count('id')
                ).order_by('-count')

                student_stats.append({
                    'username': student.user.username,
                    'full_name': student.user.get_full_name() or student.user.username,
                    'attempt_count': attempt_count,
                    'correct_count': correct_count,
                    'accuracy': student_accuracy,
                    'avg_score': avg_score,
                    'topics': list(student_topics),
                    'total_score': student.total_score,
                    'lessons_completed': student.lessons_completed,
                })

        # Sort by attempt count
        student_stats.sort(key=lambda x: x['attempt_count'], reverse=True)

        # Prepare context for template
        context = {
            'period_start': start_date,
            'period_end': end_date,
            'days': days,
            'total_attempts': total_attempts,
            'correct_attempts': correct_attempts,
            'accuracy': accuracy,
            'active_student_count': len(active_students),
            'unique_questions': unique_questions,
            'topics_data': topics_data,
            'student_stats': student_stats,
            'excluded_user': exclude_username,
        }

        # Generate report
        report_text = self._generate_text_report(context)

        if dry_run:
            self.stdout.write(self.style.SUCCESS('\n=== DRY RUN - Report Preview ===\n'))
            self.stdout.write(report_text)
            self.stdout.write(self.style.SUCCESS('\n=== End of Report ===\n'))
            return

        # Send email if recipient specified
        if recipient_email:
            subject = f'Daily Student Activity Report - {end_date.strftime("%Y-%m-%d")}'

            try:
                send_mail(
                    subject=subject,
                    message=report_text,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient_email],
                    fail_silently=False,
                )
                self.stdout.write(
                    self.style.SUCCESS(f'\nReport sent successfully to {recipient_email}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'\nFailed to send email: {str(e)}')
                )
        else:
            self.stdout.write(self.style.WARNING('\nNo email address provided. Printing report:\n'))
            self.stdout.write(report_text)

    def _generate_text_report(self, context):
        """Generate a plain text report"""
        lines = []
        lines.append('=' * 70)
        lines.append('DAILY STUDENT ACTIVITY REPORT')
        lines.append('=' * 70)
        lines.append(f"Period: {context['period_start'].strftime('%Y-%m-%d %H:%M')} to {context['period_end'].strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"Duration: {context['days']} day(s)")
        if context['excluded_user']:
            lines.append(f"Excluded user: {context['excluded_user']}")
        lines.append('')

        # Overall Summary
        lines.append('-' * 70)
        lines.append('OVERALL SUMMARY')
        lines.append('-' * 70)
        lines.append(f"Active Students: {context['active_student_count']}")
        lines.append(f"Total Attempts: {context['total_attempts']}")
        lines.append(f"Correct Answers: {context['correct_attempts']}")
        lines.append(f"Overall Accuracy: {context['accuracy']:.1f}%")
        lines.append(f"Unique Questions Attempted: {context['unique_questions']}")
        lines.append('')

        # Topics Summary
        if context['topics_data']:
            lines.append('-' * 70)
            lines.append('TOPICS WORKED ON')
            lines.append('-' * 70)
            lines.append(f"{'Topic':<30} {'Attempts':<10} {'Correct':<10} {'Avg Score':<10}")
            lines.append('-' * 70)
            for topic in context['topics_data']:
                topic_name = topic['question__topic__name'] or 'Uncategorized'
                lines.append(
                    f"{topic_name:<30} {topic['attempt_count']:<10} "
                    f"{topic['correct_count']:<10} {topic['avg_score']:.1f}%"
                )
            lines.append('')

        # Per-Student Breakdown
        if context['student_stats']:
            lines.append('-' * 70)
            lines.append('STUDENT BREAKDOWN')
            lines.append('-' * 70)
            for student in context['student_stats']:
                lines.append(f"\n{student['full_name']} ({student['username']})")
                lines.append(f"  Attempts: {student['attempt_count']}")
                lines.append(f"  Correct: {student['correct_count']} ({student['accuracy']:.1f}%)")
                lines.append(f"  Average Score: {student['avg_score']:.1f}%")
                lines.append(f"  Total Score (cumulative): {student['total_score']}")
                lines.append(f"  Lessons Completed (cumulative): {student['lessons_completed']}")

                if student['topics']:
                    lines.append(f"  Topics:")
                    for topic in student['topics'][:5]:  # Show top 5 topics
                        topic_name = topic['question__topic__name'] or 'Uncategorized'
                        lines.append(f"    - {topic_name}: {topic['count']} attempts")
        else:
            lines.append('No student activity in this period.')

        lines.append('')
        lines.append('=' * 70)
        lines.append(f"Report generated at: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append('=' * 70)

        return '\n'.join(lines)
