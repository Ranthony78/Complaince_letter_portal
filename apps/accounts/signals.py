# apps/accounts/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.utils import timezone
from .models import User, UserPreference, UserActivityLog, LoginAudit


@receiver(post_save, sender=User)
def create_user_preferences(sender, instance, created, **kwargs):
    """Create user preferences when a new user is created"""
    if created:
        try:
            UserPreference.objects.create(user=instance)

            # Log user creation - but only if not in a recursive loop
            UserActivityLog.objects.create(
                user=instance,
                action='create',
                model_name='User',
                object_id=instance.id,
                object_repr=str(instance),
                changes={'username': instance.username, 'email': instance.email}
            )
        except Exception:
            pass  # Avoid recursion issues during initial setup


@receiver(user_logged_in)
def user_logged_in_handler(sender, request, user, **kwargs):
    """Handle user login"""
    try:
        # Update last login time - use update_fields to avoid triggering signals
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        # Reset login attempts
        user.login_attempts = 0
        user.is_locked = False
        user.lock_reason = ""
        user.save(update_fields=['login_attempts', 'is_locked', 'lock_reason'])

        # Log activity - use direct create to avoid any recursion
        UserActivityLog.objects.create(
            user=user,
            action='login',
            model_name='User',
            object_id=user.id,
            object_repr=str(user),
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
    except Exception:
        pass


@receiver(user_logged_out)
def user_logged_out_handler(sender, request, user, **kwargs):
    """Handle user logout"""
    if user:
        try:
            UserActivityLog.objects.create(
                user=user,
                action='logout',
                model_name='User',
                object_id=user.id,
                object_repr=str(user),
                ip_address=request.META.get('REMOTE_ADDR', ''),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        except Exception:
            pass


@receiver(user_login_failed)
def user_login_failed_handler(sender, credentials, request, **kwargs):
    """Handle failed login attempt"""
    username = credentials.get('username')

    try:
        # Record failed login attempt
        LoginAudit.objects.create(
            username=username or 'unknown',
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            status='failed',
            failure_reason='Invalid credentials'
        )
    except Exception:
        pass

    # Increment login attempts for existing user
    if username:
        try:
            user = User.objects.get(username=username)
            user.login_attempts += 1
            if user.login_attempts >= 5:
                user.is_locked = True
                user.lock_reason = "Too many failed login attempts"
            user.save(update_fields=['login_attempts', 'is_locked', 'lock_reason'])
        except User.DoesNotExist:
            pass
