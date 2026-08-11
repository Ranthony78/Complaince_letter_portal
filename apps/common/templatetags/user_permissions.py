# apps/common/templatetags/user_permissions.py
from django import template
from django.contrib.auth.models import Permission
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def has_permission(user, permission):
    """Check if user has a specific permission"""
    if not user or not user.is_authenticated:
        return False

    if user.role == 'CCO':
        return True

    return user.has_perm(permission)


@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.simple_tag
def get_role_badge_color(role):
    """Get badge color for role"""
    colors = {
        'CCO': 'danger',
        'Representative': 'warning',
        'InternalReviewer': 'info',
        'ClientManager': 'success',
        'Viewer': 'secondary'
    }
    return colors.get(role, 'secondary')


@register.filter
def role_has_access(user, required_roles):
    """Check if user role is in required roles list"""
    if not user or not user.is_authenticated:
        return False

    required_list = required_roles.split(',')
    return user.role in required_list


@register.filter
def get_full_name(user):
    """Get user's full name or username"""
    if not user:
        return ''
    return user.get_full_name() or user.username


@register.simple_tag
def get_status_badge(status):
    """Get status badge HTML"""
    status_colors = {
        'Draft': 'secondary',
        'Radius_Pending': 'warning',
        'Sessions_Pending': 'warning',
        'Client_Pending': 'info',
        'CCO_Review': 'primary',
        'Completed': 'success',
        'Rejected': 'danger',
        'Archived': 'secondary',
        'Internal_Work': 'info'
    }

    status_display = {
        'Draft': 'Draft',
        'Radius_Pending': 'Radius Pending',
        'Sessions_Pending': 'Sessions Pending',
        'Client_Pending': 'Client Pending',
        'CCO_Review': 'CCO Review',
        'Completed': 'Completed',
        'Rejected': 'Rejected',
        'Archived': 'Archived',
        'Internal_Work': 'Internal Work'
    }

    color = status_colors.get(status, 'secondary')
    display = status_display.get(status, status.replace('_', ' '))

    return mark_safe(f'<span class="status-badge status-{color}">{display}</span>')


@register.filter
def can_create_letter(user):
    """Check if user can create letters"""
    if not user or not user.is_authenticated:
        return False

    return user.role in ['CCO', 'Representative']


@register.filter
def can_approve_radius(user):
    """Check if user can approve radius"""
    if not user or not user.is_authenticated:
        return False

    return user.role == 'CCO' or user.has_perm('accounts.can_approve_radius')


@register.filter
def can_approve_sessions(user):
    """Check if user can approve sessions"""
    if not user or not user.is_authenticated:
        return False

    return user.role == 'CCO' or user.has_perm('accounts.can_approve_sessions')


@register.filter
def can_approve_client(user):
    """Check if user can approve client"""
    if not user or not user.is_authenticated:
        return False

    return user.role == 'CCO' or user.role == 'ClientManager'


@register.filter
def can_manage_users(user):
    """Check if user can manage users"""
    if not user or not user.is_authenticated:
        return False

    return user.role == 'CCO'


@register.filter
def can_view_reports(user):
    """Check if user can view reports"""
    if not user or not user.is_authenticated:
        return False

    return user.role in ['CCO', 'Representative', 'InternalReviewer']


@register.simple_tag
def get_user_avatar(user):
    """Get user avatar initials"""
    if not user:
        return '?'

    name = user.get_full_name() or user.username
    if name:
        return name[0].upper()
    return 'U'