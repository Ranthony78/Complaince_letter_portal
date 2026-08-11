# apps/letters/models.py
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.utils import timezone
from django.core.validators import FileExtensionValidator, MinLengthValidator
from django.core.exceptions import ValidationError
from simple_history.models import HistoricalRecords
import json
import os
from datetime import datetime

User = settings.AUTH_USER_MODEL


class BaseLetter(models.Model):
    """
    Abstract base model for all letters with common fields and functionality
    """

    SYSTEM_TYPES = (
        ('FACS', 'FACS System'),
        ('ARTIVA', 'Artiva System'),
    )

    CREATION_TYPES = (
        ('Creation', 'Creation'),
        ('Revision', 'Revision'),
    )

    COMMUNICATION_TYPES = (
        ('Letter', 'Letter'),
        ('Email', 'Email'),
        ('SMS', 'SMS'),
    )

    TIMING_CHOICES = (
        ('Immediate', 'Immediate (24 hours)'),
        ('Urgent', 'Urgent (2-3 days)'),
        ('Standard', 'Standard (5-7 days)'),
        ('Extended', 'Extended (2+ weeks)'),
    )

    STATUS_CHOICES = (
        ('Draft', 'Draft'),
        ('Internal_Work', 'Internal Work'),
        ('Radius_Pending', 'Radius Approval Pending'),
        ('Sessions_Pending', 'Sessions Approval Pending'),
        ('Client_Pending', 'Client Approval Pending'),
        ('CCO_Review', 'CCO Final Review'),
        ('Completed', 'Completed'),
        ('Rejected', 'Rejected'),
        ('Archived', 'Archived'),
    )

    PRIORITY_CHOICES = (
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Critical', 'Critical'),
    )

    # Basic Information
    letter_code = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Letter Code'
    )
    creation_type = models.CharField(
        max_length=20,
        choices=CREATION_TYPES,
        verbose_name='Creation/Revision'
    )
    creation_revision_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Creation/Revision Date'
    )
    communication_type = models.CharField(
        max_length=20,
        choices=COMMUNICATION_TYPES,
        verbose_name='Letter/Email/SMS'
    )
    communication_code = models.CharField(
        max_length=50,
        verbose_name='Letter Code'
    )

    # Timing
    timing = models.CharField(
        max_length=50,
        choices=TIMING_CHOICES,
        verbose_name='Timing'
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='',
        verbose_name='Priority'
    )

    # Document Details
    document_description = models.TextField(
        verbose_name='Document Description'
    )
    production_date = models.DateField(
        verbose_name='Production Date'
    )
    source = models.CharField(
        max_length=200,
        verbose_name='Source'
    )
    letter_description = models.TextField(
        verbose_name='Letter Description'
    )

    # System Fields
    system_type = models.CharField(
        max_length=20,
        choices=SYSTEM_TYPES,
        verbose_name='System Type'
    )
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='Draft',
        verbose_name='Status'
    )
    current_version = models.CharField(
        max_length=10,
        default='V.0',
        verbose_name='Current Version'
    )

    # User Relations - Using dynamic related names to avoid clashes
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='%(class)s_created_letters',
        verbose_name='Created By'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )
    delegated_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_delegated_letters',
        verbose_name='Delegated To'
    )

    # Dates
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Submitted At'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Completed At'
    )

    # Metadata
    comments = models.TextField(
        blank=True,
        verbose_name='Comments'
    )
    internal_notes = models.TextField(
        blank=True,
        verbose_name='Internal Notes'
    )

    # Audit
    history = HistoricalRecords(inherit=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['letter_code']),
            models.Index(fields=['status']),
            models.Index(fields=['system_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.letter_code} - {self.system_type}"

    def save(self, *args, **kwargs):
        # Update timestamps based on status changes
        if self.status == 'Submitted' and not self.submitted_at:
            self.submitted_at = timezone.now()
        elif self.status == 'Completed' and not self.completed_at:
            self.completed_at = timezone.now()

        super().save(*args, **kwargs)

    def get_approval_status(self):
        """Get approval status for this letter"""
        status = {
            'radius': None,
            'sessions': None,
            'client': None,
            'cco': None
        }

        try:
            if hasattr(self, 'radius_approval'):
                status['radius'] = {
                    'status': self.radius_approval.approval_status,
                    'date': self.radius_approval.approval_date,
                    'by': str(self.radius_approval.cco_or_representative) if self.radius_approval.cco_or_representative else None
                }
        except:
            pass

        try:
            if hasattr(self, 'sessions_approval'):
                status['sessions'] = {
                    'status': self.sessions_approval.approval_status,
                    'date': self.sessions_approval.approval_date,
                    'reference': self.sessions_approval.session_reference
                }
        except:
            pass

        return status

    def can_edit(self, user):
        """Check if user can edit this letter"""
        if user.role == 'CCO':
            return True
        if self.status == 'Draft' and self.created_by == user:
            return True
        if self.delegated_to == user and self.status in ['Draft', 'Internal_Work']:
            return True
        return False

    def can_approve(self, user, approval_type):
        """Check if user can approve this letter"""
        if user.role == 'CCO':
            return True

        if approval_type == 'radius' and user.has_perm('accounts.can_approve_radius'):
            return True
        if approval_type == 'sessions' and user.has_perm('accounts.can_approve_sessions'):
            return True
        if approval_type == 'client' and user.has_perm('accounts.can_approve_client'):
            return True

        return False


class FACSLetters(BaseLetter):
    """
    FACS System Letters with client approval matrix
    """

    # Override regulatory_body to use Yes/No instead of specific bodies
    regulatory = models.CharField(
        max_length=10,
        choices=[('Yes', 'Yes'), ('No', 'No')],
        default='',
        verbose_name='Regulatory'
    )

    # Override timing choices for FACS
    timing = models.CharField(
        max_length=50,
        choices=[
            ('Initial', 'Initial'),
            ('Subsequent', 'Subsequent'),
            ('Seasonal', 'Seasonal'),
        ],
        default='',
        verbose_name='Timing'
    )

    # Override source choices for FACS
    source = models.CharField(
        max_length=200,
        choices=[
            ('Internal', 'Internal'),
            ('LiveVox', 'LiveVox'),
            ('CompuMail', 'CompuMail'),
        ],
        default='',
        verbose_name='Source'
    )

    # Additional fields for FACS
    creation_revision_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Creation/Revision Date'
    )

    communication_subtype = models.CharField(
        max_length=20,
        choices=[
            ('Letter', 'Letter'),
            ('Email', 'Email'),
            ('SMS', 'SMS'),
        ],
        default='',
        verbose_name='Letter/Email/SMS'
    )

    # FACS-specific client approvals stored as JSON
    client_approvals = models.JSONField(
        default=dict,
        verbose_name='Client Approvals'
    )

    # Ticket information (if not using separate Ticket model)
    ticket_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Ticket #'
    )
    ticket_open_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Ticket Open Date'
    )
    ticket_completed_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Ticket Completed Date'
    )

    class Meta:
        verbose_name = 'FACS Letter'
        verbose_name_plural = 'FACS Letters'
        indexes = [
            models.Index(fields=['regulatory']),
            models.Index(fields=['timing']),
            models.Index(fields=['source']),
        ]

    def save(self, *args, **kwargs):
        self.system_type = 'FACS'
        if not self.letter_code:
            # Generate letter code: FACS-YYYY-MM-XXXX
            year = datetime.now().year
            month = datetime.now().month
            count = FACSLetters.objects.filter(
                created_at__year=year,
                created_at__month=month
            ).count() + 1
            self.letter_code = f"FACS-{year}-{month:02d}-{count:04d}"
        super().save(*args, **kwargs)

    def get_client_approval_matrix(self):
        """Return client approval matrix - ONLY for actually selected clients"""

        # If no client_approvals, return empty dict (no clients selected)
        if not self.client_approvals:
            return {}

        # Return only what's stored (no defaults)
        filtered_approvals = {}
        for client_name, approval_data in self.client_approvals.items():
            # Skip the custom client placeholder if not used
            if client_name == "Client Approval 6" and not approval_data.get('custom_name'):
                continue
            # Only include if the client has a status (was actually selected)
            if approval_data.get('status'):
                # Remove contact field if it exists
                if 'contact' in approval_data:
                    approval_data.pop('contact', None)
                filtered_approvals[client_name] = approval_data

        return filtered_approvals

    def update_client_approval(self, client_name, status, comments=None):
        """Update approval status for a specific client"""
        approvals = self.client_approvals if self.client_approvals else {}

        if client_name in approvals:
            approvals[client_name]['status'] = status
            if status == 'Approved':
                approvals[client_name]['date'] = timezone.now().isoformat()
            if comments:
                approvals[client_name]['comments'] = comments

            self.client_approvals = approvals
            self.save()
            return True
        return False

    def all_clients_approved(self):
        """Check if all selected clients are approved"""
        approvals = self.get_client_approval_matrix()
        for client, data in approvals.items():
            if data.get('status') != 'Approved':
                return False
        return True

    def get_pending_clients(self):
        """Get list of pending clients"""
        pending = []
        approvals = self.get_client_approval_matrix()
        for client, data in approvals.items():
            if data.get('status') != 'Approved':
                pending.append(client)
        return pending

    def get_approval_percentage(self):
        """Get percentage of completed client approvals"""
        approvals = self.get_client_approval_matrix()
        total = len(approvals)
        if total == 0:
            return 0

        approved = sum(1 for data in approvals.values() if data.get('status') == 'Approved')
        return (approved / total) * 100


class ArtivaLetters(BaseLetter):
    """
    Artiva System Letters
    """

    # Override regulatory to use Yes/No (same as FACS)
    regulatory = models.CharField(
        max_length=10,
        choices=[('Yes', 'Yes'), ('No', 'No')],
        default='',
        blank=True,
        verbose_name='Regulatory'
    )

    # Override timing choices for Artiva (same as FACS)
    timing = models.CharField(
        max_length=50,
        choices=[
            ('Initial', 'Initial'),
            ('Subsequent', 'Subsequent'),
            ('Seasonal', 'Seasonal'),
        ],
        default='',
        blank=True,
        verbose_name='Timing'
    )

    # Override source choices for Artiva (same as FACS)
    source = models.CharField(
        max_length=200,
        choices=[
            ('Internal', 'Internal'),
            ('LiveVox', 'LiveVox'),
            ('CompuMail', 'CompuMail'),
        ],
        default='',
        blank=True,
        verbose_name='Source'
    )

    # Additional fields for Artiva (same as FACS)
    creation_revision_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Creation/Revision Date'
    )

    communication_subtype = models.CharField(
        max_length=20,
        choices=[
            ('Letter', 'Letter'),
            ('Email', 'Email'),
            ('SMS', 'SMS'),
        ],
        default='',
        blank=True,
        verbose_name='Letter/Email/SMS'
    )

    # Ticket information (same as FACS)
    ticket_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Ticket #'
    )
    ticket_open_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Ticket Open Date'
    )
    ticket_completed_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Ticket Completed Date'
    )

    class Meta:
        verbose_name = 'Artiva Letter'
        verbose_name_plural = 'Artiva Letters'
        indexes = [
            models.Index(fields=['regulatory']),
            models.Index(fields=['timing']),
            models.Index(fields=['source']),
        ]

    def save(self, *args, **kwargs):
        self.system_type = 'ARTIVA'
        if not self.letter_code:
            year = datetime.now().year
            month = datetime.now().month
            count = ArtivaLetters.objects.filter(
                created_at__year=year,
                created_at__month=month
            ).count() + 1
            self.letter_code = f"ART-{year}-{month:02d}-{count:04d}"
        super().save(*args, **kwargs)


class RadiusApproval(models.Model):
    """
    Radius Approval Model
    """

    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Returned', 'Returned for Changes'),
    )

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    letter = GenericForeignKey('content_type', 'object_id')

    cco_or_representative = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='radius_approvals',
        verbose_name='CCO or Representative',
        null = True,
        blank=True
    )
    approval_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending',
        verbose_name='Status'
    )
    approval_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Approval Date'
    )
    comments = models.TextField(
        blank=True,
        verbose_name='Comments'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )

    class Meta:
        unique_together = ['content_type', 'object_id']
        verbose_name = 'Radius Approval'
        verbose_name_plural = 'Radius Approvals'
        indexes = [
            models.Index(fields=['approval_status']),
            models.Index(fields=['approval_date']),
        ]

    def __str__(self):
        return f"Radius Approval for {self.letter} - {self.approval_status}"

    def approve(self, user, comments=''):
        """Approve the radius request"""
        self.approval_status = 'Approved'
        self.approval_date = timezone.now()
        if comments:
            self.comments = comments
        self.save()

        # Update letter status
        letter = self.letter
        if letter.status == 'Radius_Pending':
            # Check if sessions is also approved or needed
            if hasattr(letter, 'sessions_approval'):
                if letter.sessions_approval.approval_status == 'Approved':
                    letter.status = 'Client_Pending' if letter.system_type == 'FACS' else 'CCO_Review'
                else:
                    letter.status = 'Sessions_Pending'
            else:
                letter.status = 'Client_Pending' if letter.system_type == 'FACS' else 'CCO_Review'
            letter.save()

    def reject(self, user, comments=''):
        """Reject the radius request"""
        self.approval_status = 'Rejected'
        if comments:
            self.comments = comments
        self.save()

        # Update letter status
        letter = self.letter
        letter.status = 'Rejected'
        letter.save()


class SessionsApproval(models.Model):
    """
    Sessions Approval Model
    """

    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Returned', 'Returned for Changes'),
    )

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    letter = GenericForeignKey('content_type', 'object_id')

    approval_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending',
        verbose_name='Status'
    )
    approval_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Approval Date'
    )
    session_reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Session Reference'
    )
    comments = models.TextField(
        blank=True,
        verbose_name='Comments'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )

    class Meta:
        unique_together = ['content_type', 'object_id']
        verbose_name = 'Sessions Approval'
        verbose_name_plural = 'Sessions Approvals'
        indexes = [
            models.Index(fields=['approval_status']),
            models.Index(fields=['approval_date']),
        ]

    def __str__(self):
        return f"Sessions Approval for {self.letter} - {self.approval_status}"

    def approve(self, session_reference='', comments=''):
        """Approve the sessions request"""
        self.approval_status = 'Approved'
        self.approval_date = timezone.now()
        if session_reference:
            self.session_reference = session_reference
        if comments:
            self.comments = comments
        self.save()

        # Update letter status
        letter = self.letter
        if letter.status == 'Sessions_Pending':
            # Check if radius is also approved
            if hasattr(letter, 'radius_approval'):
                if letter.radius_approval.approval_status == 'Approved':
                    letter.status = 'Client_Pending' if letter.system_type == 'FACS' else 'CCO_Review'
            else:
                letter.status = 'Client_Pending' if letter.system_type == 'FACS' else 'CCO_Review'
            letter.save()

    def reject(self, comments=''):
        """Reject the sessions request"""
        self.approval_status = 'Rejected'
        if comments:
            self.comments = comments
        self.save()

        # Update letter status
        letter = self.letter
        letter.status = 'Rejected'
        letter.save()


class Ticket(models.Model):
    """
    Ticket Model for tracking support tickets
    """

    STATUS_CHOICES = (
        ('Open', 'Open'),
        ('In Progress', 'In Progress'),
        ('Pending', 'Pending'),
        ('Resolved', 'Resolved'),
        ('Closed', 'Closed'),
        ('Cancelled', 'Cancelled'),
    )

    PRIORITY_CHOICES = (
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Critical', 'Critical'),
    )

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    letter = GenericForeignKey('content_type', 'object_id')

    ticket_number = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Ticket Number'
    )
    open_date = models.DateTimeField(
        verbose_name='Open Date'
    )
    completed_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Completed Date'
    )
    status = models.CharField(
        max_length=50,
        default='Open',
        choices=STATUS_CHOICES,
        verbose_name='Status'
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='',
        verbose_name='Priority'
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        verbose_name='Assigned To'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Notes'
    )
    resolution_notes = models.TextField(
        blank=True,
        verbose_name='Resolution Notes'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )

    class Meta:
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ticket_number']),
            models.Index(fields=['status']),
            models.Index(fields=['open_date']),
        ]

    def __str__(self):
        return f"Ticket {self.ticket_number} - {self.status}"

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            # Generate ticket number
            year = datetime.now().year
            month = datetime.now().month
            count = Ticket.objects.filter(
                created_at__year=year,
                created_at__month=month
            ).count() + 1
            self.ticket_number = f"TKT-{year}-{month:02d}-{count:04d}"
        super().save(*args, **kwargs)

    def close_ticket(self, resolution_notes=''):
        """Close the ticket"""
        self.status = 'Closed'
        self.completed_date = timezone.now()
        if resolution_notes:
            self.resolution_notes = resolution_notes
        self.save()


class LetterVersion(models.Model):
    """
    Version Control Model for letter versions
    """

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    letter = GenericForeignKey('content_type', 'object_id')

    version_number = models.CharField(
        max_length=10,
        verbose_name='Version Number'
    )
    version_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Version Date'
    )
    version_author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='letter_versions',
        verbose_name='Version Author'
    )
    version_note = models.TextField(
        verbose_name='Version Notes'
    )
    version_data = models.JSONField(
        default=dict,
        verbose_name='Version Data'
    )
    changes_from_previous = models.TextField(
        blank=True,
        verbose_name='Changes from Previous'
    )
    revision_reason = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Revision Reason'
    )
    pdf_copy = models.FileField(
        upload_to='letter_versions/pdfs/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(['pdf'])],
        verbose_name='PDF Copy'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )

    class Meta:
        ordering = ['-version_number']
        unique_together = ['content_type', 'object_id', 'version_number']
        verbose_name = 'Letter Version'
        verbose_name_plural = 'Letter Versions'
        indexes = [
            models.Index(fields=['version_number']),
            models.Index(fields=['version_date']),
        ]

    def __str__(self):
        return f"{self.letter.letter_code} - {self.version_number}"

    def get_next_version_number(self):
        """Get the next version number"""
        current = int(self.version_number.replace('V.', ''))
        return f"V.{current + 1}"

    def create_next_version(self, author, note, data, reason=''):
        """Create the next version"""
        next_version = LetterVersion.objects.create(
            content_type=self.content_type,
            object_id=self.object_id,
            version_number=self.get_next_version_number(),
            version_author=author,
            version_note=note,
            version_data=data,
            changes_from_previous=self._compare_versions(self.version_data, data),
            revision_reason=reason
        )

        # Update letter's current version
        self.letter.current_version = next_version.version_number
        self.letter.save()

        return next_version

    def _compare_versions(self, old_data, new_data):
        """Compare two versions and return changes"""
        changes = []
        for key in new_data:
            if key in old_data and old_data[key] != new_data[key]:
                changes.append(f"{key}: {old_data[key]} → {new_data[key]}")
            elif key not in old_data:
                changes.append(f"{key}: Added")

        return '\n'.join(changes)


class DocumentAttachment(models.Model):
    """
    Document Attachment Model
    """

    DOCUMENT_TYPES = (
        ('Original', 'Original Document'),
        ('Revision', 'Revision Document'),
        ('Supporting', 'Supporting Document'),
        ('Client Response', 'Client Response'),
        ('Approval Proof', 'Approval Proof'),
        ('Final', 'Final Approved Version'),
        ('Legal', 'Legal Document'),
        ('Other', 'Other'),
    )

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    letter = GenericForeignKey('content_type', 'object_id')

    version = models.ForeignKey(
        LetterVersion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='attachments',
        verbose_name='Version'
    )
    file = models.FileField(
        upload_to='letters/documents/%Y/%m/',
        validators=[
            FileExtensionValidator(['pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'png'])
        ],
        verbose_name='File'
    )
    file_name = models.CharField(
        max_length=255,
        verbose_name='File Name'
    )
    file_size = models.PositiveIntegerField(
        default=0,
        verbose_name='File Size (bytes)'
    )
    file_type = models.CharField(
        max_length=50,
        verbose_name='File Type'
    )
    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPES,
        verbose_name='Document Type'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description'
    )
    upload_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Upload Date'
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_documents',
        verbose_name='Uploaded By'
    )
    is_current = models.BooleanField(
        default=False,
        verbose_name='Is Current Version'
    )
    download_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Download Count'
    )

    class Meta:
        verbose_name = 'Document Attachment'
        verbose_name_plural = 'Document Attachments'
        ordering = ['-upload_date']
        indexes = [
            models.Index(fields=['document_type']),
            models.Index(fields=['upload_date']),
            models.Index(fields=['is_current']),
        ]

    def __str__(self):
        return self.file_name

    def save(self, *args, **kwargs):
        # Set file name if not set
        if not self.file_name and self.file:
            self.file_name = self.file.name.split('/')[-1]

        # Set file size if not set
        if self.file and not self.file_size:
            self.file_size = self.file.size

        # Set file type
        if self.file:
            ext = os.path.splitext(self.file.name)[1].lower()
            self.file_type = ext[1:] if ext else 'unknown'

        super().save(*args, **kwargs)

    def increment_download_count(self):
        """Increment download count"""
        self.download_count += 1
        self.save(update_fields=['download_count'])


class Comment(models.Model):
    """
    Comments model for discussions on letters
    """

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    letter = GenericForeignKey('content_type', 'object_id')

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Author'
    )
    text = models.TextField(
        verbose_name='Comment'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='Parent Comment'
    )
    is_internal = models.BooleanField(
        default=False,
        verbose_name='Internal Comment',
        help_text='Visible only to internal users'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )

    class Meta:
        verbose_name = 'Comment'
        verbose_name_plural = 'Comments'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['author']),
        ]

    def __str__(self):
        return f"Comment by {self.author} on {self.letter}"

    def get_replies(self):
        """Get all replies to this comment"""
        return self.replies.all()


class AuditLog(models.Model):
    """
    Audit Log for letter activities
    """

    ACTION_CHOICES = (
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('delegate', 'Delegate'),
        ('upload', 'Upload'),
        ('download', 'Download'),
        ('version_create', 'Version Created'),
        ('status_change', 'Status Changed'),
    )

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    letter = GenericForeignKey('content_type', 'object_id')

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='letter_audit_logs',
        verbose_name='User'
    )
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        verbose_name='Action'
    )
    changes = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Changes'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP Address'
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name='User Agent'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Timestamp'
    )

    class Meta:
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user} - {self.action} - {self.letter} - {self.timestamp}"

    @classmethod
    def log_action(cls, user, letter, action, changes=None, request=None):
        """Helper method to log an action"""
        ip_address = None
        user_agent = None

        if request:
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT')

        return cls.objects.create(
            user=user,
            letter=letter,
            action=action,
            changes=changes or {},
            ip_address=ip_address,
            user_agent=user_agent
        )