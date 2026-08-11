from django.utils import timezone
from datetime import datetime


def make_aware_datetime(dt):
    """Convert naive datetime to timezone-aware datetime"""
    if dt and timezone.is_naive(dt):
        return timezone.make_aware(dt)
    return dt


def get_current_time():
    """Get current timezone-aware datetime"""
    return timezone.now()


def format_datetime_for_display(dt):
    """Format datetime for display in EST"""
    if dt:
        # Convert to local timezone for display
        local_dt = timezone.localtime(dt)
        return local_dt.strftime('%Y-%m-%d %H:%M:%S')
    return ''