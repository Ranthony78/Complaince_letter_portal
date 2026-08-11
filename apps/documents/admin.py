# apps/documents/admin.py (Enhanced)
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import DocumentCategory, Document, DocumentVersion
from .forms import DocumentForm, DocumentCategoryForm


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    form = DocumentCategoryForm
    list_display = ['name', 'slug', 'order', 'is_active', 'document_count']
    list_editable = ['order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']

    def document_count(self, obj):
        return obj.document_set.count()

    document_count.short_description = 'Documents'


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    form = DocumentForm
    list_display = ['title', 'document_type', 'version', 'is_active', 'is_public', 'created_at', 'action_buttons']
    list_filter = ['document_type', 'is_active', 'is_public', 'created_at']
    search_fields = ['title', 'description']
    filter_horizontal = ['view_permissions']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'document_type', 'category')
        }),
        ('File/Link', {
            'fields': ('pdf_file', 'external_url', 'version', 'is_latest')
        }),
        ('Access Control', {
            'fields': ('is_active', 'is_public', 'view_permissions')
        }),
        ('Table Data (for PO Box/Client Lists)', {
            'fields': ('table_data',),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def action_buttons(self, obj):
        buttons = []
        if obj.pdf_file:
            buttons.append(f'<a href="{obj.pdf_file.url}" target="_blank" class="button">View PDF</a>')
        buttons.append(f'<a href="{reverse("admin:documents_document_change", args=[obj.id])}" class="button">Edit</a>')
        return format_html(' '.join(buttons))

    action_buttons.short_description = 'Actions'

    actions = ['make_active', 'make_inactive', 'make_public', 'make_private']

    def make_active(self, request, queryset):
        queryset.update(is_active=True)

    make_active.short_description = "Mark selected documents as active"

    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)

    make_inactive.short_description = "Mark selected documents as inactive"

    def make_public(self, request, queryset):
        queryset.update(is_public=True)

    make_public.short_description = "Make selected documents public"

    def make_private(self, request, queryset):
        queryset.update(is_public=False)

    make_private.short_description = "Make selected documents private"


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ['document', 'version', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['document__title', 'changelog']
    readonly_fields = ['created_at']