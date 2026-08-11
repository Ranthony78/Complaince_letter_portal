# apps/dashboard/views.py
from django.shortcuts import render
from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from django.http import JsonResponse
from django.utils.dateparse import parse_date

from apps.letters.models import (
    FACSLetters, ArtivaLetters, RadiusApproval,
    SessionsApproval, Ticket, LetterVersion, DocumentAttachment
)
from apps.accounts.models import User, Notification, UserActivityLog, LoginAudit


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view with comprehensive statistics"""
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # ========== BASIC COUNTS ==========
        context['total_facs'] = FACSLetters.objects.count()
        context['total_artiva'] = ArtivaLetters.objects.count()
        context['total_letters'] = context['total_facs'] + context['total_artiva']

        # ========== STATUS COUNTS ==========
        # Draft counts
        context['draft_facs'] = FACSLetters.objects.filter(status='Draft').count()
        context['draft_artiva'] = ArtivaLetters.objects.filter(status='Draft').count()
        context['draft_count'] = context['draft_facs'] + context['draft_artiva']

        # Radius pending - FROM APPROVAL MODEL
        context['pending_radius'] = RadiusApproval.objects.filter(approval_status='Pending').count()

        # Sessions pending - FROM APPROVAL MODEL
        context['pending_sessions'] = SessionsApproval.objects.filter(approval_status='Pending').count()

        # Client pending (FACS only)
        context['pending_client'] = FACSLetters.objects.filter(status='Client_Pending').count()

        # CCO review pending
        context['pending_cco'] = FACSLetters.objects.filter(status='CCO_Review').count() + \
                                 ArtivaLetters.objects.filter(status='CCO_Review').count()

        # Completed counts
        context['completed_facs'] = FACSLetters.objects.filter(status='Completed').count()
        context['completed_artiva'] = ArtivaLetters.objects.filter(status='Completed').count()
        context['completed_count'] = context['completed_facs'] + context['completed_artiva']

        # Rejected counts
        context['rejected_facs'] = FACSLetters.objects.filter(status='Rejected').count()
        context['rejected_artiva'] = ArtivaLetters.objects.filter(status='Rejected').count()
        context['rejected_count'] = context['rejected_facs'] + context['rejected_artiva']

        # ========== PENDING LISTS FOR DASHBOARD CARDS (FIXED) ==========
        # Radius pending - wrap in object with 'approval' key
        radius_approvals = RadiusApproval.objects.filter(approval_status='Pending').select_related('content_type')[:5]
        radius_pending_list = []
        for approval in radius_approvals:
            if approval.letter:
                radius_pending_list.append({
                    'letter': approval.letter,
                    'approval': approval
                })
        context['radius_pending_list'] = radius_pending_list

        # Sessions pending - wrap in object with 'approval' key
        sessions_approvals = SessionsApproval.objects.filter(approval_status='Pending').select_related('content_type')[
                             :5]
        sessions_pending_list = []
        for approval in sessions_approvals:
            if approval.letter:
                sessions_pending_list.append({
                    'letter': approval.letter,
                    'approval': approval
                })
        context['sessions_pending_list'] = sessions_pending_list

        # Client pending - these are letters directly (no wrapper needed)
        context['client_pending_list'] = FACSLetters.objects.filter(status='Client_Pending')[:5]

        # CCO pending - these are letters directly (no wrapper needed)
        context['cco_pending_list'] = list(
            FACSLetters.objects.filter(status='CCO_Review')[:3]
        ) + list(
            ArtivaLetters.objects.filter(status='CCO_Review')[:3]
        )

        # ========== APPROVAL METRICS ==========
        # Approval times (average time from creation to completion)
        completed_facs = FACSLetters.objects.filter(status='Completed', completed_at__isnull=False)
        completed_artiva = ArtivaLetters.objects.filter(status='Completed', completed_at__isnull=False)

        facs_completion_times = []
        for letter in completed_facs:
            if letter.completed_at and letter.created_at:
                time_diff = (letter.completed_at - letter.created_at).days
                facs_completion_times.append(time_diff)

        artiva_completion_times = []
        for letter in completed_artiva:
            if letter.completed_at and letter.created_at:
                time_diff = (letter.completed_at - letter.created_at).days
                artiva_completion_times.append(time_diff)

        context['avg_facs_completion_days'] = sum(facs_completion_times) / len(
            facs_completion_times) if facs_completion_times else 0
        context['avg_artiva_completion_days'] = sum(artiva_completion_times) / len(
            artiva_completion_times) if artiva_completion_times else 0

        # Approval rates
        total_facs = FACSLetters.objects.count()
        total_artiva = ArtivaLetters.objects.count()

        context['facs_approval_rate'] = (context['completed_facs'] / total_facs * 100) if total_facs > 0 else 0
        context['artiva_approval_rate'] = (context['completed_artiva'] / total_artiva * 100) if total_artiva > 0 else 0

        # ========== USER STATISTICS ==========
        context['total_users'] = User.objects.count()
        context['active_users'] = User.objects.filter(is_active=True).count()
        context['cco_count'] = User.objects.filter(role='CCO').count()
        context['representative_count'] = User.objects.filter(role='Representative').count()
        context['reviewer_count'] = User.objects.filter(role='InternalReviewer').count()
        context['client_manager_count'] = User.objects.filter(role='ClientManager').count()
        context['viewer_count'] = User.objects.filter(role='Viewer').count()

        # User activity in last 7 days
        week_ago = timezone.now() - timedelta(days=7)
        context['active_users_last_week'] = UserActivityLog.objects.filter(
            timestamp__gte=week_ago
        ).values('user').distinct().count()

        # ========== RECENT ACTIVITY ==========
        # Recent letters
        context['recent_facs'] = FACSLetters.objects.all().order_by('-created_at')[:10]
        context['recent_artiva'] = ArtivaLetters.objects.all().order_by('-created_at')[:10]

        # Recent approvals
        context['recent_radius_approvals'] = RadiusApproval.objects.filter(
            approval_status='Approved'
        ).order_by('-approval_date')[:5]

        context['recent_sessions_approvals'] = SessionsApproval.objects.filter(
            approval_status='Approved'
        ).order_by('-approval_date')[:5]

        # Recent user activities
        context['recent_activities'] = UserActivityLog.objects.all().order_by('-timestamp')[:10]

        # ========== CHART DATA ==========
        # Status chart data
        context['status_labels'] = ['Draft', 'Radius Pending', 'Sessions Pending', 'Client Pending', 'CCO Review',
                                    'Completed', 'Rejected']
        context['status_data'] = [
            context['draft_count'],
            context['pending_radius'],
            context['pending_sessions'],
            context['pending_client'],
            context['pending_cco'],
            context['completed_count'],
            context['rejected_count']
        ]

        # Monthly trend - Last 12 months
        months = []
        facs_trend = []
        artiva_trend = []
        approval_trend = []

        for i in range(11, -1, -1):
            month_date = timezone.now() - timedelta(days=30 * i)
            month_name = month_date.strftime('%b %Y')
            months.append(month_name)

            facs_count = FACSLetters.objects.filter(
                created_at__year=month_date.year,
                created_at__month=month_date.month
            ).count()

            artiva_count = ArtivaLetters.objects.filter(
                created_at__year=month_date.year,
                created_at__month=month_date.month
            ).count()

            # Approvals in this month
            approvals_count = RadiusApproval.objects.filter(
                approval_date__year=month_date.year,
                approval_date__month=month_date.month,
                approval_status='Approved'
            ).count() + SessionsApproval.objects.filter(
                approval_date__year=month_date.year,
                approval_date__month=month_date.month,
                approval_status='Approved'
            ).count()

            facs_trend.append(facs_count)
            artiva_trend.append(artiva_count)
            approval_trend.append(approvals_count)

        context['monthly_labels'] = months
        context['facs_trend'] = facs_trend
        context['artiva_trend'] = artiva_trend
        context['approval_trend'] = approval_trend

        # Client approval status for FACS
        facs_letters = FACSLetters.objects.all()
        client_approval_stats = {
            'US Bank': {'total': 0, 'approved': 0},
            'US Bank Retail': {'total': 0, 'approved': 0},
            'Discover': {'total': 0, 'approved': 0},
            'Wells Fargo': {'total': 0, 'approved': 0},
            'Capital One': {'total': 0, 'approved': 0},
        }

        for letter in facs_letters:
            approvals = letter.get_client_approval_matrix()
            for client in client_approval_stats.keys():
                if client in approvals:
                    client_approval_stats[client]['total'] += 1
                    if approvals[client].get('status') == 'Approved':
                        client_approval_stats[client]['approved'] += 1

        context['client_approval_stats'] = client_approval_stats

        # ========== QUICK STATS ==========
        context['quick_stats'] = {
            'total_letters': context['total_letters'],
            'pending_approvals': context['pending_radius'] + context['pending_sessions'] + context['pending_client'] +
                                 context['pending_cco'],
            'completion_rate': (context['completed_count'] / context['total_letters'] * 100) if context[
                                                                                                    'total_letters'] > 0 else 0,
            'avg_processing_time': (context['avg_facs_completion_days'] + context['avg_artiva_completion_days']) / 2 if
            context['total_letters'] > 0 else 0,
        }

        # ========== CURRENT DATE ==========
        context['now'] = timezone.now()

        # ========== USER-SPECIFIC DATA ==========
        # User's pending tasks
        if user.role == 'CCO':
            context['my_pending_cco'] = FACSLetters.objects.filter(status='CCO_Review').count() + \
                                        ArtivaLetters.objects.filter(status='CCO_Review').count()
        elif user.role in ['Representative', 'InternalReviewer']:
            context['my_pending_radius'] = RadiusApproval.objects.filter(
                cco_or_representative=user,
                approval_status='Pending'
            ).count()
            context['my_pending_sessions'] = SessionsApproval.objects.filter(
                approval_status='Pending'
            ).count()
        elif user.role == 'ClientManager':
            context['my_pending_clients'] = FACSLetters.objects.filter(status='Client_Pending').count()

        # User's recent letters
        context['my_recent_facs'] = FACSLetters.objects.filter(created_by=user).order_by('-created_at')[:5]
        context['my_recent_artiva'] = ArtivaLetters.objects.filter(created_by=user).order_by('-created_at')[:5]

        # User's unread notifications
        context['unread_notifications'] = Notification.objects.filter(user=user, is_read=False).count()

        return context


class DashboardStatsView(LoginRequiredMixin, TemplateView):
    """Comprehensive dashboard statistics view"""
    template_name = 'dashboard/stats.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # ========== OVERALL STATISTICS ==========
        context['total_facs'] = FACSLetters.objects.count()
        context['total_artiva'] = ArtivaLetters.objects.count()
        context['total_letters'] = context['total_facs'] + context['total_artiva']
        context['total_users'] = User.objects.count()
        context['active_users'] = User.objects.filter(is_active=True).count()

        # ========== STATUS BREAKDOWN ==========
        statuses = ['Draft', 'Radius_Pending', 'Sessions_Pending', 'Client_Pending', 'CCO_Review', 'Completed',
                    'Rejected']
        context['status_breakdown'] = {}
        for status in statuses:
            context['status_breakdown'][status] = FACSLetters.objects.filter(status=status).count() + \
                                                  ArtivaLetters.objects.filter(status=status).count()

        # ========== SYSTEM BREAKDOWN ==========
        context['facs_breakdown'] = {}
        context['artiva_breakdown'] = {}

        for status in statuses:
            context['facs_breakdown'][status] = FACSLetters.objects.filter(status=status).count()
            context['artiva_breakdown'][status] = ArtivaLetters.objects.filter(status=status).count()

        # ========== USER ROLE BREAKDOWN ==========
        context['role_breakdown'] = {}
        for role, role_display in User.ROLE_CHOICES:
            context['role_breakdown'][role] = User.objects.filter(role=role).count()

        # ========== REGULATORY BODY DISTRIBUTION ==========
        regulatory_bodies = ['SEC', 'FINRA', 'CFPB', 'FDIC', 'OCC', 'CFTC', 'State', 'Other']
        context['regulatory_breakdown'] = {}
        for body in regulatory_bodies:
            count = FACSLetters.objects.filter(regulatory_body=body).count() + \
                    ArtivaLetters.objects.filter(regulatory_body=body).count()
            context['regulatory_breakdown'][body] = count

        # ========== TIMING DISTRIBUTION ==========
        timing_choices = ['Immediate', 'Urgent', 'Standard', 'Extended']
        context['timing_breakdown'] = {}
        for timing in timing_choices:
            count = FACSLetters.objects.filter(timing=timing).count() + \
                    ArtivaLetters.objects.filter(timing=timing).count()
            context['timing_breakdown'][timing] = count

        # ========== PRIORITY DISTRIBUTION ==========
        priority_choices = ['Low', 'Medium', 'High', 'Critical']
        context['priority_breakdown'] = {}
        for priority in priority_choices:
            count = FACSLetters.objects.filter(priority=priority).count() + \
                    ArtivaLetters.objects.filter(priority=priority).count()
            context['priority_breakdown'][priority] = count

        # ========== APPROVAL STATISTICS ==========
        context['total_radius_approvals'] = RadiusApproval.objects.count()
        context['approved_radius'] = RadiusApproval.objects.filter(approval_status='Approved').count()
        context['pending_radius_approvals'] = RadiusApproval.objects.filter(approval_status='Pending').count()

        context['total_sessions_approvals'] = SessionsApproval.objects.count()
        context['approved_sessions'] = SessionsApproval.objects.filter(approval_status='Approved').count()
        context['pending_sessions_approvals'] = SessionsApproval.objects.filter(approval_status='Pending').count()

        # ========== VERSION STATISTICS ==========
        context['total_versions'] = LetterVersion.objects.count()
        context['avg_versions_per_letter'] = LetterVersion.objects.count() / context['total_letters'] if context[
                                                                                                             'total_letters'] > 0 else 0

        # ========== DOCUMENT STATISTICS ==========
        context['total_documents'] = DocumentAttachment.objects.count()
        context['total_document_size'] = sum([doc.file_size for doc in DocumentAttachment.objects.all()]) / (
                    1024 * 1024)  # in MB

        # Add pending lists for the dashboard
        context['radius_pending_list'] = RadiusApproval.objects.filter(approval_status='Pending').select_related(
            'letter')
        context['sessions_pending_list'] = SessionsApproval.objects.filter(approval_status='Pending').select_related(
            'letter')
        context['client_pending_list'] = FACSLetters.objects.filter(status='Client_Pending')
        context['cco_pending_list'] = list(FACSLetters.objects.filter(status='CCO_Review')) + list(
            ArtivaLetters.objects.filter(status='CCO_Review'))

        return context


class AnalyticsView(LoginRequiredMixin, TemplateView):
    """Advanced analytics dashboard view"""
    template_name = 'dashboard/analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # ========== LETTER ANALYTICS ==========
        context['total_letters'] = FACSLetters.objects.count() + ArtivaLetters.objects.count()
        context['total_approvals'] = RadiusApproval.objects.count() + SessionsApproval.objects.count()

        # Daily creation trend (last 30 days)
        daily_data = []
        for i in range(29, -1, -1):
            date = timezone.now().date() - timedelta(days=i)
            facs_daily = FACSLetters.objects.filter(created_at__date=date).count()
            artiva_daily = ArtivaLetters.objects.filter(created_at__date=date).count()
            daily_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'facs': facs_daily,
                'artiva': artiva_daily,
                'total': facs_daily + artiva_daily
            })

        context['daily_trend'] = daily_data

        # Hourly activity pattern
        hourly_data = []
        for hour in range(24):
            facs_hourly = FACSLetters.objects.filter(created_at__hour=hour).count()
            artiva_hourly = ArtivaLetters.objects.filter(created_at__hour=hour).count()
            hourly_data.append({
                'hour': hour,
                'facs': facs_hourly,
                'artiva': artiva_hourly
            })

        context['hourly_pattern'] = hourly_data

        # User performance metrics
        user_performance = []
        for user in User.objects.filter(is_active=True):
            letters_created = user.created_facsletters.count() + user.created_artivaletters.count()
            approvals_given = RadiusApproval.objects.filter(cco_or_representative=user).count() + \
                              SessionsApproval.objects.filter(letter__created_by=user).count()

            user_performance.append({
                'user': user,
                'letters_created': letters_created,
                'approvals_given': approvals_given,
                'role': user.get_role_display()
            })

        context['user_performance'] = sorted(user_performance, key=lambda x: x['letters_created'], reverse=True)[:10]

        # Approval time analysis
        approval_times = []
        for approval in RadiusApproval.objects.filter(approval_status='Approved', approval_date__isnull=False):
            if hasattr(approval, 'created_at'):
                time_diff = (approval.approval_date - approval.created_at).total_seconds() / 3600
                approval_times.append(time_diff)

        context['avg_approval_time_hours'] = sum(approval_times) / len(approval_times) if approval_times else 0

        return context


class WidgetsView(LoginRequiredMixin, TemplateView):
    """Dashboard widgets view"""
    template_name = 'dashboard/widgets.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Widget data
        context['widget_stats'] = {
            'total_letters': FACSLetters.objects.count() + ArtivaLetters.objects.count(),
            'pending_approvals': RadiusApproval.objects.filter(approval_status='Pending').count() + \
                                 SessionsApproval.objects.filter(approval_status='Pending').count(),
            'completed_today': FACSLetters.objects.filter(completed_at__date=timezone.now().date()).count() + \
                               ArtivaLetters.objects.filter(completed_at__date=timezone.now().date()).count(),
            'active_users_today': UserActivityLog.objects.filter(timestamp__date=timezone.now().date()).values(
                'user').distinct().count(),
        }

        return context


class MyActivityView(LoginRequiredMixin, TemplateView):
    """User activity view"""
    template_name = 'dashboard/my_activity.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get user activities
        context['activities'] = UserActivityLog.objects.filter(
            user=user
        ).order_by('-timestamp')[:50]

        # Activity summary by type
        context['activity_summary'] = UserActivityLog.objects.filter(
            user=user
        ).values('action').annotate(count=Count('id')).order_by('-count')

        # Get user's letters
        context['my_facs'] = FACSLetters.objects.filter(created_by=user).order_by('-created_at')
        context['my_artiva'] = ArtivaLetters.objects.filter(created_by=user).order_by('-created_at')

        # Get user's approvals
        context['my_radius_approvals'] = RadiusApproval.objects.filter(cco_or_representative=user).order_by(
            '-created_at')
        context['my_sessions_approvals'] = SessionsApproval.objects.filter(letter__created_by=user).order_by(
            '-created_at')

        # Get user's tickets
        from apps.letters.models import Ticket
        from django.contrib.contenttypes.models import ContentType

        facs_ct = ContentType.objects.get_for_model(FACSLetters)
        artiva_ct = ContentType.objects.get_for_model(ArtivaLetters)

        context['my_tickets'] = Ticket.objects.filter(
            Q(content_type=facs_ct, letter__created_by=user) |
            Q(content_type=artiva_ct, letter__created_by=user)
        ).order_by('-created_at')

        # Login history
        context['login_history'] = LoginAudit.objects.filter(user=user).order_by('-login_time')[:20]

        return context


class DashboardNotificationsView(LoginRequiredMixin, TemplateView):
    """Dashboard notifications view"""
    template_name = 'dashboard/notifications.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get notifications
        notifications = Notification.objects.filter(
            user=self.request.user
        ).order_by('-created_at')

        context['notifications'] = notifications
        context['unread_count'] = notifications.filter(is_read=False).count()
        context['read_count'] = notifications.filter(is_read=True).count()

        # Mark all as read if requested
        if self.request.GET.get('mark_read') == 'all':
            notifications.filter(is_read=False).update(is_read=True, read_at=timezone.now())
            messages.success(self.request, 'All notifications marked as read.')

        return context


class QuickActionsView(LoginRequiredMixin, TemplateView):
    """Quick actions view"""
    template_name = 'dashboard/quick_actions.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Add quick actions based on user role
        context['quick_actions'] = []

        # Common actions for all users
        context['quick_actions'].extend([
            {'name': 'View All Letters', 'url': '/letters/', 'icon': 'fas fa-envelope', 'color': 'primary'},
            {'name': 'Search Letters', 'url': '/letters/search/', 'icon': 'fas fa-search', 'color': 'info'},
        ])

        # Role-specific actions
        if user.role == 'CCO':
            context['quick_actions'].extend([
                {'name': 'Create FACS Letter', 'url': '/letters/create/facs/', 'icon': 'fas fa-file-alt',
                 'color': 'success'},
                {'name': 'Create Artiva Letter', 'url': '/letters/create/artiva/', 'icon': 'fas fa-file-signature',
                 'color': 'success'},
                {'name': 'Manage Users', 'url': '/accounts/users/', 'icon': 'fas fa-users', 'color': 'warning'},
                {'name': 'View Reports', 'url': '/letters/reports/', 'icon': 'fas fa-chart-bar', 'color': 'info'},
                {'name': 'Audit Log', 'url': '/letters/audit/', 'icon': 'fas fa-history', 'color': 'secondary'},
                {'name': 'System Settings', 'url': '/admin/', 'icon': 'fas fa-cog', 'color': 'dark'},
            ])
        elif user.role == 'Representative':
            context['quick_actions'].extend([
                {'name': 'Create FACS Letter', 'url': '/letters/create/facs/', 'icon': 'fas fa-file-alt',
                 'color': 'success'},
                {'name': 'Create Artiva Letter', 'url': '/letters/create/artiva/', 'icon': 'fas fa-file-signature',
                 'color': 'success'},
                {'name': 'Radius Approvals', 'url': '/letters/radius/pending/', 'icon': 'fas fa-radar',
                 'color': 'warning'},
                {'name': 'Sessions Approvals', 'url': '/letters/sessions/pending/', 'icon': 'fas fa-calendar-check',
                 'color': 'warning'},
                {'name': 'My Drafts', 'url': '/letters/my-drafts/', 'icon': 'fas fa-pencil-alt', 'color': 'info'},
            ])
        elif user.role == 'InternalReviewer':
            context['quick_actions'].extend([
                {'name': 'Radius Approvals', 'url': '/letters/radius/pending/', 'icon': 'fas fa-radar',
                 'color': 'warning'},
                {'name': 'Sessions Approvals', 'url': '/letters/sessions/pending/', 'icon': 'fas fa-calendar-check',
                 'color': 'warning'},
                {'name': 'View All Letters', 'url': '/letters/', 'icon': 'fas fa-envelope', 'color': 'primary'},
            ])
        elif user.role == 'ClientManager':
            context['quick_actions'].extend([
                {'name': 'Client Approvals', 'url': '/letters/client/approvals/', 'icon': 'fas fa-building',
                 'color': 'warning'},
                {'name': 'View Assigned Letters', 'url': '/letters/', 'icon': 'fas fa-envelope', 'color': 'primary'},
                {'name': 'Client Reports', 'url': '/letters/reports/?type=client', 'icon': 'fas fa-chart-line',
                 'color': 'info'},
            ])
        else:  # Viewer
            context['quick_actions'].extend([
                {'name': 'View Letters', 'url': '/letters/', 'icon': 'fas fa-envelope', 'color': 'primary'},
                {'name': 'Completed Letters', 'url': '/letters/completed/', 'icon': 'fas fa-check-circle',
                 'color': 'success'},
                {'name': 'Reports', 'url': '/letters/reports/', 'icon': 'fas fa-chart-bar', 'color': 'info'},
            ])

        # Recent actions count
        context['recent_actions_count'] = UserActivityLog.objects.filter(
            user=user,
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).count()

        return context


class DashboardSearchView(LoginRequiredMixin, TemplateView):
    """Dashboard search view"""
    template_name = 'dashboard/search.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        query = self.request.GET.get('q', '')
        search_type = self.request.GET.get('type', 'all')

        context['query'] = query
        context['search_type'] = search_type

        if query:
            # Search in FACS letters
            if search_type in ['all', 'facs']:
                context['facs_results'] = FACSLetters.objects.filter(
                    Q(letter_code__icontains=query) |
                    Q(document_description__icontains=query) |
                    Q(letter_description__icontains=query) |
                    Q(communication_code__icontains=query) |
                    Q(source__icontains=query)
                )[:20]

            # Search in Artiva letters
            if search_type in ['all', 'artiva']:
                context['artiva_results'] = ArtivaLetters.objects.filter(
                    Q(letter_code__icontains=query) |
                    Q(document_description__icontains=query) |
                    Q(letter_description__icontains=query) |
                    Q(communication_code__icontains=query) |
                    Q(artiva_reference__icontains=query)
                )[:20]

            # Search in users
            if search_type in ['all', 'users']:
                context['user_results'] = User.objects.filter(
                    Q(username__icontains=query) |
                    Q(first_name__icontains=query) |
                    Q(last_name__icontains=query) |
                    Q(email__icontains=query)
                )[:10]

            # Total results count
            context['total_results'] = len(context.get('facs_results', [])) + \
                                       len(context.get('artiva_results', [])) + \
                                       len(context.get('user_results', []))

        return context