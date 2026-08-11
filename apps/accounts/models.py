# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser, Permission
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.conf import settings


class User(AbstractUser):
    """
    Enhanced User model with role-based permissions and additional fields
    """

    ROLE_CHOICES = (
        ('CCO', 'Chief Compliance Officer'),
        ('Representative', 'CCO Representative'),
        ('InternalReviewer', 'Internal Reviewer'),
        ('ClientManager', 'Client Manager'),
        ('Viewer', 'Viewer'),
    )

    DEPARTMENT_CHOICES = (
        ('Compliance', 'Compliance'),
        ('Legal', 'Legal'),
        ('Risk Management', 'Risk Management'),
        ('Operations', 'Operations'),
        ('Client Services', 'Client Services'),
        ('IT', 'Information Technology'),
        ('Other', 'Other'),
    )

    # Basic Information
    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default='Viewer',
        verbose_name=_('Role')
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in format: '+999999999'. Up to 15 digits allowed."
            )
        ],
        verbose_name=_('Phone Number')
    )

    department = models.CharField(
        max_length=100,
        blank=True,
        choices=DEPARTMENT_CHOICES,
        verbose_name=_('Department')
    )

    # Professional Information
    employee_id = models.CharField(
        max_length=50,
        blank=True,
        unique=True,
        verbose_name=_('Employee ID')
    )

    job_title = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Job Title')
    )

    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates',
        verbose_name=_('Manager')
    )

    # Contact Information
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)

    # Status and Activity
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    is_locked = models.BooleanField(default=False, verbose_name=_('Account Locked'))
    lock_reason = models.TextField(blank=True, verbose_name=_('Lock Reason'))

    # Timestamps - FIXED: Removed auto_now from last_activity
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    last_activity = models.DateTimeField(default=timezone.now, verbose_name=_('Last Activity'))
    last_password_change = models.DateTimeField(auto_now=True, verbose_name=_('Last Password Change'))

    # Security
    login_attempts = models.IntegerField(default=0, verbose_name=_('Login Attempts'))
    two_factor_enabled = models.BooleanField(default=False, verbose_name=_('2FA Enabled'))
    session_key = models.CharField(max_length=100, blank=True, verbose_name=_('Session Key'))

    # Client Management (for Client Managers)
    managed_clients = models.JSONField(default=list, blank=True, verbose_name=_('Managed Clients'))

    # Preferences
    notification_preferences = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Notification Preferences'),
        help_text="JSON field storing user notification preferences"
    )

    theme_preferences = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Theme Preferences')
    )

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-date_joined']
        permissions = [
            ("can_approve_radius", "Can approve Radius"),
            ("can_approve_sessions", "Can approve Sessions"),
            ("can_approve_client", "Can approve Client"),
            ("can_final_approve", "Can provide final approval"),
            ("can_delegate", "Can delegate tasks"),
            ("can_view_reports", "Can view reports"),
            ("can_manage_users", "Can manage users"),
            ("can_audit_logs", "Can view audit logs"),
            ("can_export_data", "Can export data"),
        ]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


    def save(self, *args, **kwargs):
        # Only auto-assign employee_id for new users (when creating)
        if not self.employee_id and not self.pk:
            year = timezone.now().year
            count = User.objects.filter(date_joined__year=year).count() + 1
            self.employee_id = f"EMP-{year}-{count:04d}"

        # IMPORTANT: Don't manually set last_activity here - let the field handle it
        # Don't do: self.last_activity = timezone.now()

        super().save(*args, **kwargs)

    def get_full_name(self):
        """Return the full name of the user."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    def get_role_display(self):
        """Get display name for role"""
        return dict(self.ROLE_CHOICES).get(self.role, self.role)

    def has_approval_permission(self, approval_type):
        """Check if user has specific approval permission"""
        if self.role == 'CCO':
            return True

        # Check specific permissions
        permission_map = {
            'radius': 'accounts.can_approve_radius',
            'sessions': 'accounts.can_approve_sessions',
            'client': 'accounts.can_approve_client',
            'final': 'accounts.can_final_approve',
            'delegate': 'accounts.can_delegate',
        }

        perm = permission_map.get(approval_type)
        if perm:
            return self.has_perm(perm)

        return False

    def can_manage_client(self, client_name):
        """Check if user can manage a specific client"""
        if self.role == 'CCO':
            return True
        if self.role == 'ClientManager' and client_name in self.managed_clients:
            return True
        return False

    def increment_login_attempts(self):
        """Increment login attempts and lock if threshold reached"""
        self.login_attempts += 1
        if self.login_attempts >= 5:
            self.is_locked = True
            self.lock_reason = "Too many failed login attempts"
        # FIXED: Only update specific fields to avoid recursion
        self.save(update_fields=['login_attempts', 'is_locked', 'lock_reason'])

    def reset_login_attempts(self):
        """Reset login attempts"""
        self.login_attempts = 0
        self.is_locked = False
        self.lock_reason = ""
        # FIXED: Only update specific fields to avoid recursion
        self.save(update_fields=['login_attempts', 'is_locked', 'lock_reason'])

    def update_last_activity(self):
        """Update last activity timestamp"""
        self.last_activity = timezone.now()
        # FIXED: Only update last_activity field
        self.save(update_fields=['last_activity'])

    def get_notification_preference(self, notification_type, default=True):
        """Get notification preference for specific type"""
        return self.notification_preferences.get(notification_type, default)

    def set_notification_preference(self, notification_type, value):
        """Set notification preference"""
        if not self.notification_preferences:
            self.notification_preferences = {}
        self.notification_preferences[notification_type] = value
        self.save(update_fields=['notification_preferences'])

    def get_pending_tasks_count(self):
        """Get count of pending tasks for this user"""
        try:
            from apps.letters.models import RadiusApproval, SessionsApproval, FACSLetters, ArtivaLetters
        except ImportError:
            return 0

        count = 0

        # Radius approvals
        if self.has_approval_permission('radius'):
            count += RadiusApproval.objects.filter(
                cco_or_representative=self,
                approval_status='Pending'
            ).count()

        # Sessions approvals
        if self.has_approval_permission('sessions'):
            count += SessionsApproval.objects.filter(
                approval_status='Pending'
            ).count()

        # Client approvals
        if self.role == 'ClientManager':
            count += FACSLetters.objects.filter(
                status='Client_Pending'
            ).count()

        # Final approvals for CCO
        if self.role == 'CCO':
            count += FACSLetters.objects.filter(status='CCO_Review').count()
            count += ArtivaLetters.objects.filter(status='CCO_Review').count()

        return count

    @property
    def created_letters(self):
        """Get all letters created by this user"""
        from apps.letters.models import FACSLetters, ArtivaLetters
        facs_letters = FACSLetters.objects.filter(created_by=self)
        artiva_letters = ArtivaLetters.objects.filter(created_by=self)

        # Combine and sort
        all_letters = list(facs_letters) + list(artiva_letters)
        all_letters.sort(key=lambda x: x.created_at, reverse=True)

        return all_letters


class Notification(models.Model):
    """
    Enhanced Notification model for user notifications
    """

    NOTIFICATION_TYPES = (
        ('approval_needed', 'Approval Needed'),
        ('approval_completed', 'Approval Completed'),
        ('revision_needed', 'Revision Needed'),
        ('delegated', 'Delegated'),
        ('completed', 'Completed'),
        ('reminder', 'Reminder'),
        ('system_alert', 'System Alert'),
        ('comment', 'Comment Added'),
        ('mention', 'You were mentioned'),
    )

    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('User')
    )

    type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        verbose_name=_('Notification Type')
    )

    title = models.CharField(
        max_length=200,
        verbose_name=_('Title')
    )

    message = models.TextField(
        verbose_name=_('Message')
    )

    link = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Link')
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name=_('Priority')
    )

    is_read = models.BooleanField(
        default=False,
        verbose_name=_('Is Read')
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Read At')
    )

    is_archived = models.BooleanField(
        default=False,
        verbose_name=_('Is Archived')
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Expires At')
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )

    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    def save(self, *args, **kwargs):
        # Auto-expire after 30 days if not set
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=30)
        super().save(*args, **kwargs)

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

    def is_expired(self):
        """Check if notification is expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    def get_icon(self):
        """Get icon class based on notification type"""
        icons = {
            'approval_needed': 'fas fa-clock text-warning',
            'approval_completed': 'fas fa-check-circle text-success',
            'revision_needed': 'fas fa-edit text-danger',
            'delegated': 'fas fa-user-check text-info',
            'completed': 'fas fa-check-circle text-success',
            'reminder': 'fas fa-bell text-warning',
            'system_alert': 'fas fa-exclamation-triangle text-danger',
            'comment': 'fas fa-comment text-info',
            'mention': 'fas fa-at text-primary',
        }
        return icons.get(self.type, 'fas fa-bell')


class UserSession(models.Model):
    """
    Track user sessions for security and monitoring
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name=_('User')
    )

    session_key = models.CharField(
        max_length=100,
        unique=True,
        null=True,  # Add this to allow null
        blank=True,  # Add this to allow blank
        verbose_name=_('Session Key')
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP Address')
    )

    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent')
    )

    device_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Device Type')
    )

    browser = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Browser')
    )

    operating_system = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Operating System')
    )

    login_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Login Time')
    )

    last_activity = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Last Activity')
    )

    logout_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Logout Time')
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )

    class Meta:
        verbose_name = _('User Session')
        verbose_name_plural = _('User Sessions')
        ordering = ['-login_time']

    def __str__(self):
        return f"{self.user.username} - {self.login_time}"

    def end_session(self):
        """End the session"""
        self.is_active = False
        self.logout_time = timezone.now()
        self.save()


class LoginAudit(models.Model):
    """
    Track all login attempts for security auditing
    """

    LOGIN_STATUS = (
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('locked', 'Account Locked'),
        ('expired', 'Session Expired'),
    )

    username = models.CharField(
        max_length=150,
        verbose_name=_('Username')
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='login_audits',
        verbose_name=_('User')
    )

    ip_address = models.GenericIPAddressField(
        verbose_name=_('IP Address')
    )

    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent')
    )

    status = models.CharField(
        max_length=20,
        choices=LOGIN_STATUS,
        verbose_name=_('Status')
    )

    failure_reason = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Failure Reason')
    )

    login_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Login Time')
    )

    class Meta:
        verbose_name = _('Login Audit')
        verbose_name_plural = _('Login Audits')
        ordering = ['-login_time']
        indexes = [
            models.Index(fields=['username', '-login_time']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.username} - {self.status} - {self.login_time}"


class UserActivityLog(models.Model):
    """
    Track user activities for audit purposes
    """

    ACTION_TYPES = (
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('delegate', 'Delegate'),
        ('upload', 'Upload'),
        ('download', 'Download'),
        ('login', 'Login'),
        ('logout', 'Logout'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activities',
        verbose_name=_('User')
    )

    action = models.CharField(
        max_length=50,
        choices=ACTION_TYPES,
        verbose_name=_('Action')
    )

    model_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Model Name')
    )

    object_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Object ID')
    )

    object_repr = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Object Representation')
    )

    changes = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Changes')
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP Address')
    )

    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent')
    )

    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Timestamp')
    )

    class Meta:
        verbose_name = _('User Activity Log')
        verbose_name_plural = _('User Activity Logs')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action']),
            models.Index(fields=['model_name']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.timestamp}"

    @classmethod
    def log_activity(cls, user, action, **kwargs):
        """Helper method to log user activity"""
        # Skip logging if no user provided
        if not user or not user.id:
            print(f"Warning: Cannot log activity - no user provided for action '{action}'")
            return None

        try:
            return cls.objects.create(
                user=user,
                action=action,
                model_name=kwargs.get('model_name', ''),
                object_id=kwargs.get('object_id', ''),
                object_repr=kwargs.get('object_repr', ''),
                changes=kwargs.get('changes', {}),
                ip_address=kwargs.get('ip_address', ''),
                user_agent=kwargs.get('user_agent', ''),
            )
        except Exception as e:
            print(f"Error logging activity: {e}")
            return None

class UserPreference(models.Model):
    """
    Store user preferences and settings
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='preferences',
        verbose_name=_('User')
    )

    # Dashboard preferences
    default_dashboard = models.CharField(
        max_length=100,
        default='main',
        verbose_name=_('Default Dashboard')
    )

    widget_layout = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Widget Layout')
    )

    # Email preferences
    email_notifications = models.BooleanField(
        default=True,
        verbose_name=_('Email Notifications')
    )

    email_digest_frequency = models.CharField(
        max_length=20,
        choices=[
            ('instant', 'Instant'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
        ],
        default='instant',
        verbose_name=_('Email Digest Frequency')
    )

    # Display preferences
    items_per_page = models.IntegerField(
        default=25,
        choices=[(10, 10), (25, 25), (50, 50), (100, 100)],
        verbose_name=_('Items Per Page')
    )

    date_format = models.CharField(
        max_length=20,
        default='Y-m-d',
        verbose_name=_('Date Format')
    )

    time_format = models.CharField(
        max_length=20,
        default='H:i',
        verbose_name=_('Time Format')
    )

    timezone = models.CharField(
        max_length=50,
        default='UTC',
        verbose_name=_('Timezone')
    )

    language = models.CharField(
        max_length=10,
        default='en',
        verbose_name=_('Language')
    )

    # Theme preferences
    theme = models.CharField(
        max_length=20,
        default='light',
        choices=[
            ('light', 'Light'),
            ('dark', 'Dark'),
            ('auto', 'Auto'),
        ],
        verbose_name=_('Theme')
    )

    sidebar_collapsed = models.BooleanField(
        default=False,
        verbose_name=_('Sidebar Collapsed')
    )

    # Notification preferences
    notification_sound = models.BooleanField(
        default=True,
        verbose_name=_('Notification Sound')
    )

    desktop_notifications = models.BooleanField(
        default=True,
        verbose_name=_('Desktop Notifications')
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )

    class Meta:
        verbose_name = _('User Preference')
        verbose_name_plural = _('User Preferences')

    def __str__(self):
        return f"Preferences for {self.user.username}"

    def get_widget_layout(self):
        """Get widget layout as list"""
        return self.widget_layout or []

    def set_widget_layout(self, layout):
        """Set widget layout"""
        self.widget_layout = layout
        self.save()


class Role(models.Model):
    """
    Custom role model for advanced role management
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Role Name')
    )

    display_name = models.CharField(
        max_length=100,
        verbose_name=_('Display Name')
    )

    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )

    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name='custom_roles',
        verbose_name=_('Permissions')
    )

    is_system_role = models.BooleanField(
        default=False,
        verbose_name=_('System Role'),
        help_text="System roles cannot be deleted"
    )

    hierarchy_level = models.IntegerField(
        default=0,
        verbose_name=_('Hierarchy Level'),
        help_text="Higher number means higher authority"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )

    class Meta:
        verbose_name = _('Role')
        verbose_name_plural = _('Roles')
        ordering = ['-hierarchy_level', 'name']

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        if not self.display_name:
            self.display_name = self.name
        super().save(*args, **kwargs)


class Department(models.Model):
    """
    Department model for organizational structure
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Department Name')
    )

    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_('Department Code')
    )

    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )

    head = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_departments',
        verbose_name=_('Department Head')
    )

    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_departments',
        verbose_name=_('Parent Department')
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )

    class Meta:
        verbose_name = _('Department')
        verbose_name_plural = _('Departments')
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_full_path(self):
        """Get full department hierarchy path"""
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.name}"
        return self.name