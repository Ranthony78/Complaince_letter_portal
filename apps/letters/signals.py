# apps/letters/signals.py
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from apps.accounts.models import Notification, UserActivityLog
from .models import FACSLetters, ArtivaLetters, LetterVersion, RadiusApproval, SessionsApproval


@receiver(post_save, sender=FACSLetters)
def facs_letter_saved(sender, instance, created, **kwargs):
    """Handle FACS letter save events"""
    if created:
        # Create notification for creator
        Notification.objects.create(
            user=instance.created_by,
            type='system_alert',
            title='FACS Letter Created',
            message=f'Your FACS letter {instance.letter_code} has been created successfully.',
            link=f'/letters/{instance.id}/facs/'
        )

        # Log activity
        UserActivityLog.log_activity(
            user=instance.created_by,
            action='create',
            model_name='FACSLetters',
            object_id=instance.id,
            object_repr=instance.letter_code,
            changes={'letter_code': instance.letter_code}
        )


@receiver(post_save, sender=ArtivaLetters)
def artiva_letter_saved(sender, instance, created, **kwargs):
    """Handle Artiva letter save events"""
    if created:
        # Create notification for creator
        Notification.objects.create(
            user=instance.created_by,
            type='system_alert',
            title='Artiva Letter Created',
            message=f'Your Artiva letter {instance.letter_code} has been created successfully.',
            link=f'/letters/{instance.id}/artiva/'
        )

        # Log activity
        UserActivityLog.log_activity(
            user=instance.created_by,
            action='create',
            model_name='ArtivaLetters',
            object_id=instance.id,
            object_repr=instance.letter_code,
            changes={'letter_code': instance.letter_code}
        )


@receiver(pre_save, sender=LetterVersion)
def letter_version_created(sender, instance, **kwargs):
    """Handle version creation"""
    if not instance.id:  # New version being created
        # Update letter's current version
        letter = instance.letter
        if letter:
            letter.current_version = instance.version_number
            letter.save()


@receiver(post_save, sender=RadiusApproval)
def radius_approval_updated(sender, instance, created, **kwargs):
    """Handle radius approval updates"""
    if not created and instance.approval_status == 'Approved':
        # Create notification for letter creator
        letter = instance.letter
        if letter:
            Notification.objects.create(
                user=letter.created_by,
                type='approval_completed',
                title='Radius Approval Completed',
                message=f'Radius approval for letter {letter.letter_code} has been approved.',
                link=f'/letters/{letter.id}/{letter.system_type.lower()}/'
            )

            # Log activity
            UserActivityLog.log_activity(
                user=instance.cco_or_representative,
                action='approve',
                model_name='RadiusApproval',
                object_id=instance.id,
                object_repr=str(instance),
                changes={'approval_status': 'Approved'}
            )


@receiver(post_save, sender=SessionsApproval)
def sessions_approval_updated(sender, instance, created, **kwargs):
    """Handle sessions approval updates"""
    if not created and instance.approval_status == 'Approved':
        # Create notification for letter creator
        letter = instance.letter
        if letter:
            Notification.objects.create(
                user=letter.created_by,
                type='approval_completed',
                title='Sessions Approval Completed',
                message=f'Sessions approval for letter {letter.letter_code} has been approved.',
                link=f'/letters/{letter.id}/{letter.system_type.lower()}/'
            )