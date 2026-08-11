# apps/dashboard/context_processors.py
from django.db.models import Q, Count
from django.utils import timezone
from apps.accounts.models import Notification
from apps.letters.models import FACSLetters, ArtivaLetters, RadiusApproval, SessionsApproval


def notification_count(request):
    """Add notification count to all templates"""
    if request.user.is_authenticated:
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        return {'notification_count': count}
    return {'notification_count': 0}


def pending_approvals_count(request):
    """Add pending approval counts for sidebar badges"""
    if request.user.is_authenticated:
        context = {}

        # For CCO
        if request.user.role == 'CCO':
            facs_pending = FACSLetters.objects.filter(
                status='CCO_Review'
            ).count()
            artiva_pending = ArtivaLetters.objects.filter(
                status='CCO_Review'
            ).count()
            context['pending_final_count'] = facs_pending + artiva_pending

        # For Radius approvals
        if request.user.role in ['CCO', 'Representative', 'InternalReviewer']:
            radius_pending = RadiusApproval.objects.filter(
                approval_status='Pending'
            ).count()
            context['radius_pending_count'] = radius_pending

            sessions_pending = SessionsApproval.objects.filter(
                approval_status='Pending'
            ).count()
            context['sessions_pending_count'] = sessions_pending

        # For Client Managers
        if request.user.role == 'ClientManager':
            facs_client_pending = FACSLetters.objects.filter(
                status='Client_Pending'
            ).count()
            context['client_pending_count'] = facs_client_pending

        # Draft count - FIXED: Use direct model queries instead of related_name
        facs_drafts = FACSLetters.objects.filter(
            created_by=request.user,
            status='Draft'
        ).count()
        artiva_drafts = ArtivaLetters.objects.filter(
            created_by=request.user,
            status='Draft'
        ).count()
        context['draft_count'] = facs_drafts + artiva_drafts

        return context
    return {}


def notifications(request):
    """Add recent notifications to all templates"""
    if request.user.is_authenticated:
        notifications = Notification.objects.filter(
            user=request.user
        )[:10]
        return {'notifications': notifications}
    return {'notifications': []}


def user_stats(request):
    """Add user statistics to all templates"""
    if request.user.is_authenticated:
        user = request.user
        context = {}

        # Count letters created by user
        facs_count = FACSLetters.objects.filter(created_by=user).count()
        artiva_count = ArtivaLetters.objects.filter(created_by=user).count()
        context['user_letters_count'] = facs_count + artiva_count

        # Count approvals given by user
        if user.role in ['CCO', 'Representative', 'InternalReviewer']:
            radius_count = RadiusApproval.objects.filter(
                cco_or_representative=user
            ).count()
            context['user_approvals_count'] = radius_count
        else:
            context['user_approvals_count'] = 0

        # Count pending tasks
        pending = 0
        if user.role == 'CCO':
            pending = FACSLetters.objects.filter(status='CCO_Review').count() + \
                      ArtivaLetters.objects.filter(status='CCO_Review').count()
        elif user.role in ['Representative', 'InternalReviewer']:
            pending = RadiusApproval.objects.filter(approval_status='Pending').count() + \
                      SessionsApproval.objects.filter(approval_status='Pending').count()
        elif user.role == 'ClientManager':
            pending = FACSLetters.objects.filter(status='Client_Pending').count()

        context['user_pending_tasks'] = pending

        return context
    return {}


def system_stats(request):
    """Add system-wide statistics to all templates"""
    context = {}

    # Overall counts
    context['total_letters'] = FACSLetters.objects.count() + ArtivaLetters.objects.count()
    context['total_facs'] = FACSLetters.objects.count()
    context['total_artiva'] = ArtivaLetters.objects.count()

    # Status counts
    context['pending_radius'] = FACSLetters.objects.filter(status='Radius_Pending').count() + \
                                ArtivaLetters.objects.filter(status='Radius_Pending').count()
    context['pending_sessions'] = FACSLetters.objects.filter(status='Sessions_Pending').count() + \
                                  ArtivaLetters.objects.filter(status='Sessions_Pending').count()
    context['pending_cco'] = FACSLetters.objects.filter(status='CCO_Review').count() + \
                             ArtivaLetters.objects.filter(status='CCO_Review').count()
    context['completed_count'] = FACSLetters.objects.filter(status='Completed').count() + \
                                 ArtivaLetters.objects.filter(status='Completed').count()

    # Approval rates
    total_letters = context['total_letters']
    completed = context['completed_count']
    context['completion_rate'] = round((completed / total_letters * 100), 1) if total_letters > 0 else 0

    # Recent activity count (last 24 hours)
    yesterday = timezone.now() - timezone.timedelta(days=1)
    context['recent_activity_count'] = FACSLetters.objects.filter(created_at__gte=yesterday).count() + \
                                       ArtivaLetters.objects.filter(created_at__gte=yesterday).count()

    return context


def current_time(request):
    """Add current time to all templates"""
    return {'current_time': timezone.now()}