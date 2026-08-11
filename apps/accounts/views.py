from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView, ListView, UpdateView, CreateView, DeleteView, DetailView
from django.views.generic.edit import FormView
from django.urls import reverse, reverse_lazy
from django.http import JsonResponse, HttpResponseRedirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.db.models import Q, Count, Avg, Sum
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
import json
from datetime import datetime, timedelta

from .models import User, Notification, UserActivityLog, LoginAudit, UserPreference, Role, Department, UserSession
from .forms import (
    UserLoginForm, UserCreationForm, UserUpdateForm,
    ChangePasswordForm, UserProfileForm, NotificationSettingsForm,
    UserPreferencesForm, RoleForm, DepartmentForm, UserSearchForm
)


class CustomLoginView(LoginView):
    """Custom login view with enhanced features"""
    template_name = 'accounts/login.html'
    authentication_form = UserLoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        """Handle successful login"""
        response = super().form_valid(form)
        user = form.get_user()

        # Handle remember me functionality
        if not form.cleaned_data.get('remember'):
            self.request.session.set_expiry(0)

        # Create user session record (with null session_key if not available)
        try:
            UserSession.objects.create(
                user=user,
                session_key=self.request.session.session_key or None,  # Allow None
                ip_address=self.get_client_ip(),
                user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                login_time=timezone.now(),
                is_active=True
            )
        except Exception as e:
            # Log error but don't fail login
            print(f"Error creating user session: {e}")

        # Reset login attempts
        user.login_attempts = 0
        user.is_locked = False
        user.lock_reason = ""
        user.save(update_fields=['login_attempts', 'is_locked', 'lock_reason'])

        messages.success(
            self.request,
            f'Welcome back, {user.get_full_name() or user.username}!'
        )

        return response

    def form_invalid(self, form):
        """Handle failed login"""
        messages.error(self.request, 'Invalid username or password. Please try again.')
        return super().form_invalid(form)

    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class ProfileView(LoginRequiredMixin, TemplateView):
    """User profile view"""
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get user statistics
        from apps.letters.models import FACSLetters, ArtivaLetters, RadiusApproval, SessionsApproval
        from django.contrib.contenttypes.models import ContentType

        # Count letters created by this user
        facs_count = FACSLetters.objects.filter(created_by=user).count()
        artiva_count = ArtivaLetters.objects.filter(created_by=user).count()
        letters_created = facs_count + artiva_count

        # Count Radius approvals given
        radius_approvals = RadiusApproval.objects.filter(cco_or_representative=user).count()

        # Count Sessions approvals - FIXED: Can't use letter__created_by with GenericForeignKey
        # Instead, get sessions approvals for letters created by this user
        sessions_approvals = 0
        facs_ct = ContentType.objects.get_for_model(FACSLetters)
        artiva_ct = ContentType.objects.get_for_model(ArtivaLetters)

        # Get FACS letters created by user
        facs_letters = FACSLetters.objects.filter(created_by=user).values_list('id', flat=True)
        # Get Artiva letters created by user
        artiva_letters = ArtivaLetters.objects.filter(created_by=user).values_list('id', flat=True)

        # Count sessions approvals for these letters
        sessions_approvals += SessionsApproval.objects.filter(
            content_type=facs_ct,
            object_id__in=facs_letters
        ).count()
        sessions_approvals += SessionsApproval.objects.filter(
            content_type=artiva_ct,
            object_id__in=artiva_letters
        ).count()

        approvals_given = radius_approvals + sessions_approvals

        # Get pending tasks count
        pending_tasks = user.get_pending_tasks_count()

        # Get notification counts
        total_notifications = Notification.objects.filter(user=user).count()
        unread_notifications = Notification.objects.filter(user=user, is_read=False).count()

        context['user'] = user
        context['stats'] = {
            'letters_created': letters_created,
            'approvals_given': approvals_given,
            'pending_tasks': pending_tasks,
            'total_notifications': total_notifications,
            'unread_notifications': unread_notifications,
        }

        # Get recent activity
        context['activities'] = UserActivityLog.objects.filter(
            user=user
        ).order_by('-timestamp')[:10]

        # Get recent letters
        facs_letters = FACSLetters.objects.filter(created_by=user).order_by('-created_at')[:5]
        artiva_letters = ArtivaLetters.objects.filter(created_by=user).order_by('-created_at')[:5]
        context['recent_letters'] = list(facs_letters) + list(artiva_letters)
        context['recent_letters'].sort(key=lambda x: x.created_at, reverse=True)

        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Update user profile"""
    model = User
    form_class = UserProfileForm
    template_name = 'accounts/profile_update.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)


class ChangePasswordView(LoginRequiredMixin, FormView):
    """Change user password"""
    template_name = 'accounts/change_password.html'
    form_class = ChangePasswordForm
    success_url = reverse_lazy('accounts:profile')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = self.request.user
        user.set_password(form.cleaned_data['new_password1'])
        user.save()
        update_session_auth_hash(self.request, user)

        # Log activity
        UserActivityLog.log_activity(
            user=user,
            action='update',
            model_name='User',
            object_id=user.id,
            object_repr=str(user),
            changes=['password_changed']
        )

        messages.success(self.request, 'Password changed successfully!')
        return super().form_valid(form)


class UserSettingsView(LoginRequiredMixin, TemplateView):
    """User settings view"""
    template_name = 'accounts/user_settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notification_settings_form'] = NotificationSettingsForm(instance=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        if 'notification_settings' in request.POST:
            form = NotificationSettingsForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, 'Notification settings updated!')
                return redirect('accounts:user_settings')

        return self.get(request, *args, **kwargs)


class UserPreferencesView(LoginRequiredMixin, UpdateView):
    """User preferences view"""
    model = UserPreference
    form_class = UserPreferencesForm
    template_name = 'accounts/user_preferences.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self, queryset=None):
        obj, created = UserPreference.objects.get_or_create(user=self.request.user)
        return obj

    def form_valid(self, form):
        messages.success(self.request, 'Preferences updated successfully!')
        return super().form_valid(form)


class NotificationListView(LoginRequiredMixin, ListView):
    """List user notifications"""
    model = Notification
    template_name = 'accounts/notifications.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user
        ).select_related('user')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unread_count'] = Notification.objects.filter(
            user=self.request.user, is_read=False
        ).count()
        return context


@login_required
def mark_notification_read(request, pk):
    """Mark a single notification as read"""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.mark_as_read()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})

    return redirect(request.META.get('HTTP_REFERER', 'accounts:notifications'))


@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(user=request.user, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})

    messages.success(request, 'All notifications marked as read.')
    return redirect('accounts:notifications')


@login_required
def delete_notification(request, pk):
    """Delete a notification"""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})

    return redirect('accounts:notifications')


# CCO Only Views
def cco_required(view_func):
    """Decorator to check if user is CCO"""

    def wrapped(request, *args, **kwargs):
        if request.user.role != 'CCO':
            raise PermissionDenied("You don't have permission to access this page.")
        return view_func(request, *args, **kwargs)

    return wrapped


class UserManagementView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """User management view for CCO"""
    template_name = 'accounts/user_management.html'

    def test_func(self):
        return self.request.user.role == 'CCO'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all users
        users = User.objects.all().order_by('-date_joined')

        # Filter by role if specified
        role_filter = self.request.GET.get('role')
        if role_filter:
            users = users.filter(role=role_filter)

        # Filter by status
        status_filter = self.request.GET.get('status')
        if status_filter == 'active':
            users = users.filter(is_active=True)
        elif status_filter == 'inactive':
            users = users.filter(is_active=False)

        # Search
        search_query = self.request.GET.get('search')
        if search_query:
            users = users.filter(
                Q(username__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )

        # Pagination
        paginator = Paginator(users, 20)
        page_number = self.request.GET.get('page')
        context['users'] = paginator.get_page(page_number)

        # Get statistics
        context['total_users'] = User.objects.count()
        context['active_users'] = User.objects.filter(is_active=True).count()
        context['cco_count'] = User.objects.filter(role='CCO').count()
        context['representative_count'] = User.objects.filter(role='Representative').count()
        context['reviewer_count'] = User.objects.filter(role='InternalReviewer').count()
        context['client_manager_count'] = User.objects.filter(role='ClientManager').count()

        # Get roles for filter
        context['roles'] = User.ROLE_CHOICES

        return context


class CreateUserView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create new user (CCO only)"""
    model = User
    form_class = UserCreationForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_management')

    def test_func(self):
        return self.request.user.role == 'CCO'

    def form_valid(self, form):
        user = form.save()

        # Log activity
        UserActivityLog.log_activity(
            user=self.request.user,
            action='create',
            model_name='User',
            object_id=user.id,
            object_repr=str(user),
            changes=form.changed_data,
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )

        # Create notification for new user
        Notification.objects.create(
            user=user,
            type='system_alert',
            title='Welcome to Letter Portal',
            message=f'Your account has been created by {self.request.user.get_full_name()}. Please log in and change your password.',
            link=reverse('accounts:change_password')
        )

        messages.success(self.request, f'User {user.username} created successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create New User'
        context['button_text'] = 'Create User'
        return context

    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class EditUserView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Edit user (CCO only)"""
    model = User
    form_class = UserUpdateForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_management')

    def test_func(self):
        return self.request.user.role == 'CCO'

    def form_valid(self, form):
        user = form.save()

        # Log activity
        UserActivityLog.log_activity(
            user=self.request.user,
            action='update',
            model_name='User',
            object_id=user.id,
            object_repr=str(user),
            changes=form.changed_data,
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )

        messages.success(self.request, f'User {user.username} updated successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit User'
        context['button_text'] = 'Update User'
        return context

    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class DeleteUserView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete user (CCO only)"""
    model = User
    template_name = 'accounts/user_confirm_delete.html'
    success_url = reverse_lazy('accounts:user_management')

    def test_func(self):
        return self.request.user.role == 'CCO'

    def delete(self, request, *args, **kwargs):
        user = self.get_object()

        # Prevent deleting self
        if user == request.user:
            messages.error(request, 'You cannot delete your own account.')
            return redirect('accounts:user_management')

        # Log activity
        UserActivityLog.log_activity(
            user=request.user,
            action='delete',
            model_name='User',
            object_id=user.id,
            object_repr=str(user),
            ip_address=self.get_client_ip(),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        messages.success(request, f'User {user.username} deleted successfully!')
        return super().delete(request, *args, **kwargs)

    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


@login_required
@cco_required
def toggle_user_status(request, pk):
    """Toggle user active status"""
    user = get_object_or_404(User, pk=pk)

    # Prevent deactivating self
    if user == request.user:
        return JsonResponse({'error': 'Cannot deactivate your own account'}, status=400)

    user.is_active = not user.is_active
    user.save()

    # Log activity
    UserActivityLog.log_activity(
        user=request.user,
        action='update',
        model_name='User',
        object_id=user.id,
        object_repr=str(user),
        changes=[f'status changed to {"active" if user.is_active else "inactive"}'],
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )

    return JsonResponse({
        'success': True,
        'is_active': user.is_active,
        'message': f'User {user.username} is now {"active" if user.is_active else "inactive"}'
    })


@login_required
@cco_required
def reset_user_password(request, pk):
    """Reset user password"""
    user = get_object_or_404(User, pk=pk)

    # Generate random password
    import random
    import string
    new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

    user.set_password(new_password)
    user.save()

    # Log activity
    UserActivityLog.log_activity(
        user=request.user,
        action='update',
        model_name='User',
        object_id=user.id,
        object_repr=str(user),
        changes=['password_reset'],
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )

    # Create notification
    Notification.objects.create(
        user=user,
        type='system_alert',
        title='Password Reset',
        message=f'Your password has been reset by {request.user.get_full_name()}. New password: {new_password}',
        priority='high'
    )

    messages.success(request, f'Password for {user.username} has been reset. New password: {new_password}')
    return redirect('accounts:user_management')


@login_required
@cco_required
def impersonate_user(request, pk):
    """Impersonate another user (CCO only)"""
    user_to_impersonate = get_object_or_404(User, pk=pk)

    # Store original user in session
    request.session['impersonate_original_user_id'] = request.user.id

    # Login as the other user
    login(request, user_to_impersonate)

    # Log activity
    UserActivityLog.log_activity(
        user=request.user,
        action='login',
        model_name='User',
        object_id=user_to_impersonate.id,
        object_repr=f'Impersonated {user_to_impersonate.username}',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )

    messages.warning(request, f'You are now impersonating {user_to_impersonate.get_full_name()}.')
    return redirect('dashboard:index')


@login_required
def stop_impersonate(request):
    """Stop impersonating and return to original user"""
    original_user_id = request.session.get('impersonate_original_user_id')

    if original_user_id:
        original_user = get_object_or_404(User, pk=original_user_id)
        login(request, original_user)
        del request.session['impersonate_original_user_id']

        messages.success(request, 'Returned to your original account.')

    return redirect('dashboard:index')


class RoleManagementView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Role management view (CCO only)"""
    model = Role
    template_name = 'accounts/role_management.html'
    context_object_name = 'roles'

    def test_func(self):
        return self.request.user.role == 'CCO'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_roles'] = Role.objects.count()
        return context


class CreateRoleView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create new role (CCO only)"""
    model = Role
    form_class = RoleForm
    template_name = 'accounts/role_form.html'
    success_url = reverse_lazy('accounts:role_management')

    def test_func(self):
        return self.request.user.role == 'CCO'

    def form_valid(self, form):
        role = form.save()

        # Log activity
        UserActivityLog.log_activity(
            user=self.request.user,
            action='create',
            model_name='Role',
            object_id=role.id,
            object_repr=role.name,
            changes=form.changed_data,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )

        messages.success(self.request, f'Role {role.display_name} created successfully!')
        return super().form_valid(form)


class EditRoleView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Edit role (CCO only)"""
    model = Role
    form_class = RoleForm
    template_name = 'accounts/role_form.html'
    success_url = reverse_lazy('accounts:role_management')

    def test_func(self):
        return self.request.user.role == 'CCO'

    def form_valid(self, form):
        role = form.save()

        # Log activity
        UserActivityLog.log_activity(
            user=self.request.user,
            action='update',
            model_name='Role',
            object_id=role.id,
            object_repr=role.name,
            changes=form.changed_data,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )

        messages.success(self.request, f'Role {role.display_name} updated successfully!')
        return super().form_valid(form)


class DeleteRoleView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete role (CCO only)"""
    model = Role
    template_name = 'accounts/role_confirm_delete.html'
    success_url = reverse_lazy('accounts:role_management')

    def test_func(self):
        return self.request.user.role == 'CCO'

    def delete(self, request, *args, **kwargs):
        role = self.get_object()

        if role.is_system_role:
            messages.error(request, 'Cannot delete system roles.')
            return redirect('accounts:role_management')

        # Log activity
        UserActivityLog.log_activity(
            user=request.user,
            action='delete',
            model_name='Role',
            object_id=role.id,
            object_repr=role.name,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        messages.success(request, f'Role {role.display_name} deleted successfully!')
        return super().delete(request, *args, **kwargs)


class RolePermissionsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Role permissions management (CCO only)"""
    template_name = 'accounts/role_permissions.html'

    def test_func(self):
        return self.request.user.role == 'CCO'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['roles'] = Role.objects.all()

        # Get all permissions grouped by app
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'codename')

        permissions_by_app = {}
        for perm in permissions:
            app_label = perm.content_type.app_label
            if app_label not in permissions_by_app:
                permissions_by_app[app_label] = []
            permissions_by_app[app_label].append(perm)

        context['permissions_by_app'] = permissions_by_app
        return context


class DepartmentManagementView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Department management view (CCO only)"""
    model = Department
    template_name = 'accounts/department_management.html'
    context_object_name = 'departments'

    def test_func(self):
        return self.request.user.role == 'CCO'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_departments'] = Department.objects.count()
        context['active_departments'] = Department.objects.filter(is_active=True).count()
        return context


class CreateDepartmentView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create new department (CCO only)"""
    model = Department
    form_class = DepartmentForm
    template_name = 'accounts/department_form.html'
    success_url = reverse_lazy('accounts:department_management')

    def test_func(self):
        return self.request.user.role == 'CCO'

    def form_valid(self, form):
        department = form.save()

        # Log activity
        UserActivityLog.log_activity(
            user=self.request.user,
            action='create',
            model_name='Department',
            object_id=department.id,
            object_repr=department.name,
            changes=form.changed_data,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )

        messages.success(self.request, f'Department {department.name} created successfully!')
        return super().form_valid(form)


class EditDepartmentView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Edit department (CCO only)"""
    model = Department
    form_class = DepartmentForm
    template_name = 'accounts/department_form.html'
    success_url = reverse_lazy('accounts:department_management')

    def test_func(self):
        return self.request.user.role == 'CCO'

    def form_valid(self, form):
        department = form.save()

        # Log activity
        UserActivityLog.log_activity(
            user=self.request.user,
            action='update',
            model_name='Department',
            object_id=department.id,
            object_repr=department.name,
            changes=form.changed_data,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )

        messages.success(self.request, f'Department {department.name} updated successfully!')
        return super().form_valid(form)


class ActivityLogView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """View user activity logs (CCO only)"""
    model = UserActivityLog
    template_name = 'accounts/activity_logs.html'
    context_object_name = 'activities'
    paginate_by = 50

    def test_func(self):
        return self.request.user.role == 'CCO'

    def get_queryset(self):
        queryset = UserActivityLog.objects.select_related('user').all()

        # Filter by user
        user_id = self.request.GET.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Filter by action
        action = self.request.GET.get('action')
        if action:
            queryset = queryset.filter(action=action)

        # Filter by date range
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(timestamp__gte=date_from)
        if date_to:
            queryset = queryset.filter(timestamp__lte=date_to)

        return queryset.order_by('-timestamp')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['users'] = User.objects.filter(is_active=True)
        context['action_choices'] = UserActivityLog.ACTION_TYPES
        return context


class LoginHistoryView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """View login history (CCO only)"""
    model = LoginAudit
    template_name = 'accounts/login_history.html'
    context_object_name = 'logins'
    paginate_by = 50

    def test_func(self):
        return self.request.user.role == 'CCO'

    def get_queryset(self):
        queryset = LoginAudit.objects.select_related('user').all()

        # Filter by user
        user_id = self.request.GET.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by('-login_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['users'] = User.objects.filter(is_active=True)
        context['status_choices'] = LoginAudit.LOGIN_STATUS

        # Statistics
        context['total_logins'] = LoginAudit.objects.count()
        context['successful_logins'] = LoginAudit.objects.filter(status='success').count()
        context['failed_logins'] = LoginAudit.objects.filter(status='failed').count()
        context['unique_users'] = LoginAudit.objects.values('user').distinct().count()

        return context


class UserActivityReportView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """User activity report (CCO only)"""
    template_name = 'accounts/user_activity_report.html'

    def test_func(self):
        return self.request.user.role == 'CCO'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get date range
        date_range = self.request.GET.get('date_range', '30')
        days = int(date_range)
        start_date = timezone.now() - timedelta(days=days)

        # Activity by user
        context['activity_by_user'] = UserActivityLog.objects.filter(
            timestamp__gte=start_date
        ).values('user__username', 'user__first_name', 'user__last_name').annotate(
            total=Count('id'),
            unique_actions=Count('action', distinct=True)
        ).order_by('-total')[:10]

        # Activity by action type
        context['activity_by_action'] = UserActivityLog.objects.filter(
            timestamp__gte=start_date
        ).values('action').annotate(
            count=Count('id')
        ).order_by('-count')

        # Daily activity trend
        daily_activity = UserActivityLog.objects.filter(
            timestamp__gte=start_date
        ).extra(
            {'date': "date(timestamp)"}
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        context['daily_activity'] = list(daily_activity)
        context['date_range'] = date_range

        return context


class HelpView(LoginRequiredMixin, TemplateView):
    """Help and support view"""
    template_name = 'accounts/help.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get help articles based on user role
        help_articles = {
            'CCO': [
                {'title': 'User Management', 'content': 'How to manage users, roles, and permissions...'},
                {'title': 'Approval Workflow', 'content': 'Understanding the complete approval workflow...'},
                {'title': 'System Configuration', 'content': 'How to configure system settings...'},
            ],
            'Representative': [
                {'title': 'Creating Letters', 'content': 'Step by step guide to creating letters...'},
                {'title': 'Approval Process', 'content': 'How to approve Radius and Sessions...'},
            ],
            'InternalReviewer': [
                {'title': 'Radius Approval', 'content': 'How to review and approve Radius requests...'},
                {'title': 'Sessions Approval', 'content': 'How to review and approve Sessions...'},
            ],
            'ClientManager': [
                {'title': 'Client Approvals', 'content': 'How to manage client approvals...'},
                {'title': 'Client Communication', 'content': 'Best practices for client communication...'},
            ],
            'Viewer': [
                {'title': 'Viewing Letters', 'content': 'How to search and view letters...'},
                {'title': 'Downloading Documents', 'content': 'How to download letter documents...'},
            ]
        }

        context['articles'] = help_articles.get(self.request.user.role, help_articles['Viewer'])
        context['faqs'] = [
            {'question': 'How do I reset my password?',
             'answer': 'Go to profile settings and click Change Password...'},
            {'question': 'How do I delegate a task?', 'answer': 'Only CCO can delegate tasks...'},
            {'question': 'How do I track letter status?', 'answer': 'View the letter details page...'},
        ]

        return context


class UserGuideView(LoginRequiredMixin, TemplateView):
    """User guide view"""
    template_name = 'accounts/user_guide.html'


@login_required
@require_GET
def load_role_permissions(request, pk):
    """Load permissions for a specific role (AJAX)"""
    if request.user.role != 'CCO':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        role = Role.objects.get(pk=pk)
        permissions = list(role.permissions.values_list('id', flat=True))
        return JsonResponse({'success': True, 'permissions': permissions})
    except Role.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Role not found'}, status=404)


@login_required
@csrf_exempt
@require_POST
def save_role_permissions(request):
    """Save permissions for a role (AJAX)"""
    if request.user.role != 'CCO':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        role_id = data.get('role_id')
        permission_ids = data.get('permissions', [])

        role = Role.objects.get(pk=role_id)
        permissions = Permission.objects.filter(id__in=permission_ids)
        role.permissions.set(permissions)

        return JsonResponse({'success': True})
    except Role.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Role not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def reset_role_permissions(request, pk):
    """Reset permissions to default for a role (AJAX)"""
    if request.user.role != 'CCO':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        role = Role.objects.get(pk=pk)

        # Define default permissions per role
        default_perms = {
            'CCO': ['can_approve_radius', 'can_approve_sessions', 'can_approve_client',
                    'can_final_approve', 'can_delegate', 'can_view_reports',
                    'can_manage_users', 'can_audit_logs', 'can_export_data'],
            'Representative': ['can_approve_radius', 'can_approve_sessions', 'can_delegate'],
            'InternalReviewer': ['can_approve_radius', 'can_approve_sessions'],
            'ClientManager': ['can_approve_client'],
            'Viewer': []
        }

        default_perm_names = default_perms.get(role.name, [])
        permissions = Permission.objects.filter(codename__in=default_perm_names)
        role.permissions.set(permissions)

        return JsonResponse({'success': True})
    except Role.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Role not found'}, status=404)