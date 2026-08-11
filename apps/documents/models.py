# apps/documents/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
import json

User = get_user_model()


class DocumentCategory(models.Model):
    """Categories for organizing documents"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    icon = models.CharField(max_length=50, blank=True, help_text="FontAwesome icon class")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Document Category"
        verbose_name_plural = "Document Categories"

    def __str__(self):
        return self.name


class Document(models.Model):
    """Main document model for all files"""
    DOCUMENT_TYPES = [
        # Supporting Documents
        ('policy', 'Policies and Procedures'),
        ('flowchart', 'Flowcharts'),
        ('change_mgmt', 'Change Management'),
        ('po_box', 'PO Box List'),
        ('client_approval', 'Clients that Require Approval'),

        # Disclosures
        ('disclosure_en', 'Client Disclosure Documents - English'),
        ('disclosure_es', 'Client Disclosure Documents - Spanish'),
        ('master_disclosure', 'Master Disclosure Document'),

        # Letters
        ('letter_artiva', 'RevSpring - Artiva'),
        ('letter_facs', 'RevSpring - FACS'),
        ('letter_email', 'RevSpring - Emails'),
        ('compumail', 'CompuMail - Emails'),
        ('letter_spanish', 'Spanish Letters'),
        ('letter_manual', 'Manual Letters'),
        ('letter_amex', 'Amex Letters'),
        ('letter_sms', 'LiveVox - SMS'),

        # Business Rules
        ('business_layout', 'Layout-fields'),
        ('business_flags', 'Flags & Disclosures'),
        ('business_filters', 'FILTERS'),

        # Vendor Links (external)
        ('vendor_link', 'Vendor Link'),
    ]

    # Basic Info
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES, db_index=True)
    category = models.ForeignKey(DocumentCategory, on_delete=models.SET_NULL, null=True, blank=True)

    # File/Link
    pdf_file = models.FileField(
        upload_to='documents/%Y/%m/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])]
    )
    external_url = models.URLField(blank=True, help_text="For 3rd party vendor links")

    # Version Control
    version = models.CharField(max_length=20, default='1.0')
    is_latest = models.BooleanField(default=True)

    # Access Control
    is_active = models.BooleanField(default=True, help_text="Visible to users")
    is_public = models.BooleanField(default=False, help_text="Visible to all users without permission check")
    view_permissions = models.ManyToManyField(
        User,
        related_name='accessible_documents',
        blank=True,
        help_text="Users who can view this document (if not public)"
    )

    # For PO Box and Client lists (table data)
    table_data = models.JSONField(default=dict, blank=True, help_text="JSON data for table views")

    # Metadata
    display_order = models.IntegerField(default=0, help_text="Order in which to display")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_documents')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', '-created_at']
        indexes = [
            models.Index(fields=['document_type', 'is_active']),
            models.Index(fields=['is_public', 'is_active']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return self.title

    def has_pdf(self):
        return bool(self.pdf_file)

    def is_external_link(self):
        return bool(self.external_url)

    def has_table_data(self):
        return bool(self.table_data and (self.table_data.get('columns') or self.table_data.get('rows')))

    def get_table_columns(self):
        return self.table_data.get('columns', []) if self.table_data else []

    def get_table_rows(self):
        return self.table_data.get('rows', []) if self.table_data else []


class DocumentVersion(models.Model):
    """Track document version history"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='versions')
    version = models.CharField(max_length=20)
    pdf_file = models.FileField(upload_to='documents/versions/%Y/%m/')
    changelog = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Document Version"
        verbose_name_plural = "Document Versions"

    def __str__(self):
        return f"{self.document.title} - v{self.version}"


class DocumentViewLog(models.Model):
    """Track document views for analytics"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=[('view', 'View'), ('download', 'Download')])
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} viewed {self.document.title} at {self.created_at}"