# apps/documents/views.py (Complete)
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import HttpResponse, Http404, JsonResponse
from django.core.paginator import Paginator
from django.db import models
from django.urls import reverse
import json

from .models import Document, DocumentCategory, DocumentVersion
from .forms import DocumentForm


# ==================== ADMIN DOCUMENT MANAGEMENT ====================

@staff_member_required
def document_management(request):
    """Document Management Control Panel - For Admin Users"""
    # Get all documents with filters
    documents = Document.objects.all().order_by('-created_at')

    # Apply filters
    doc_type = request.GET.get('type')
    if doc_type:
        documents = documents.filter(document_type=doc_type)

    status = request.GET.get('status')
    if status == 'active':
        documents = documents.filter(is_active=True)
    elif status == 'inactive':
        documents = documents.filter(is_active=False)

    visibility = request.GET.get('visibility')
    if visibility == 'public':
        documents = documents.filter(is_public=True)
    elif visibility == 'private':
        documents = documents.filter(is_public=False)

    # Search
    search = request.GET.get('search')
    if search:
        documents = documents.filter(title__icontains=search)

    # Pagination
    paginator = Paginator(documents, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Statistics
    stats = {
        'total': Document.objects.count(),
        'active': Document.objects.filter(is_active=True).count(),
        'inactive': Document.objects.filter(is_active=False).count(),
        'public': Document.objects.filter(is_public=True).count(),
        'private': Document.objects.filter(is_public=False).count(),
        'by_type': {}
    }

    for doc_type, label in Document.DOCUMENT_TYPES:
        stats['by_type'][label] = Document.objects.filter(document_type=doc_type).count()

    # Get categories for filter
    categories = DocumentCategory.objects.filter(is_active=True)

    return render(request, 'documents/document_management.html', {
        'documents': page_obj,
        'stats': stats,
        'categories': categories,
        'document_types': Document.DOCUMENT_TYPES,
        'current_type': doc_type,
        'current_status': status,
        'current_visibility': visibility,
        'search': search,
        'page_obj': page_obj,
    })


@staff_member_required
def document_create(request):
    """Create a new document"""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        document_type = request.POST.get('document_type')
        version = request.POST.get('version', '1.0')
        is_public = request.POST.get('is_public') == 'on'
        is_active = request.POST.get('is_active') == 'on'
        pdf_file = request.FILES.get('pdf_file')
        external_url = request.POST.get('external_url')

        # Handle table data for PO Box/Client lists
        table_data = None
        if document_type in ['po_box', 'client_approval']:
            columns = request.POST.getlist('table_columns[]')
            rows_data = request.POST.get('table_rows')
            if columns and rows_data:
                rows = [row.split('|') for row in rows_data.split('\n') if row.strip()]
                table_data = {
                    'columns': columns,
                    'rows': rows
                }

        document = Document.objects.create(
            title=title,
            description=description,
            document_type=document_type,
            version=version,
            is_public=is_public,
            is_active=is_active,
            pdf_file=pdf_file,
            external_url=external_url,
            table_data=table_data,
            created_by=request.user
        )

        messages.success(request, f'Document "{title}" created successfully!')
        return redirect('documents:document_management')

    return render(request, 'documents/document_create.html', {
        'document_types': Document.DOCUMENT_TYPES
    })


@staff_member_required
def document_edit(request, pk):
    """Edit an existing document"""
    document = get_object_or_404(Document, pk=pk)

    if request.method == 'POST':
        document.title = request.POST.get('title')
        document.description = request.POST.get('description')
        document.document_type = request.POST.get('document_type')
        document.version = request.POST.get('version', '1.0')
        document.is_public = request.POST.get('is_public') == 'on'
        document.is_active = request.POST.get('is_active') == 'on'

        if request.FILES.get('pdf_file'):
            document.pdf_file = request.FILES.get('pdf_file')

        document.external_url = request.POST.get('external_url')
        document.save()

        messages.success(request, f'Document "{document.title}" updated successfully!')
        return redirect('documents:document_management')

    return render(request, 'documents/document_edit.html', {
        'document': document,
        'document_types': Document.DOCUMENT_TYPES
    })


@staff_member_required
def document_delete(request, pk):
    """Delete or archive a document"""
    document = get_object_or_404(Document, pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'archive':
            document.is_active = False
            document.save()
            messages.success(request, f'Document "{document.title}" archived successfully!')
        elif action == 'delete':
            document.delete()
            messages.success(request, f'Document "{document.title}" deleted permanently!')

        return redirect('documents:document_management')

    return render(request, 'documents/document_delete.html', {'document': document})


@staff_member_required
def document_toggle_status(request, pk):
    """Toggle document active status (AJAX)"""
    document = get_object_or_404(Document, pk=pk)
    document.is_active = not document.is_active
    document.save()

    return JsonResponse({
        'success': True,
        'is_active': document.is_active,
        'message': f'Document "{document.title}" is now {"active" if document.is_active else "archived"}'
    })


@staff_member_required
def document_bulk_upload(request):
    """Bulk upload multiple documents"""
    if request.method == 'POST':
        files = request.FILES.getlist('pdf_files')
        document_type = request.POST.get('document_type')
        is_public = request.POST.get('is_public') == 'on'

        uploaded = 0
        for file in files:
            title = file.name.replace('.pdf', '').replace('_', ' ')
            Document.objects.create(
                title=title,
                document_type=document_type,
                pdf_file=file,
                is_public=is_public,
                is_active=True,
                created_by=request.user
            )
            uploaded += 1

        messages.success(request, f'{uploaded} documents uploaded successfully!')
        return redirect('documents:document_management')

    return render(request, 'documents/document_bulk_upload.html', {
        'document_types': Document.DOCUMENT_TYPES
    })


# ==================== USER DOCUMENT VIEWING ====================

@login_required
def document_list(request, document_type=None):
    """List all documents of a specific type"""
    category = request.GET.get('category')

    documents = Document.objects.filter(is_active=True)

    if document_type:
        documents = documents.filter(document_type=document_type)

    if category:
        documents = documents.filter(category__slug=category)

    # Apply permission filtering
    if not request.user.is_staff:
        documents = documents.filter(
            models.Q(is_public=True) |
            models.Q(view_permissions=request.user)
        ).distinct()

    documents = documents.order_by('-is_latest', '-created_at')

    # Pagination
    paginator = Paginator(documents, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get document type display name
    doc_type_display = dict(Document.DOCUMENT_TYPES).get(document_type, 'Documents')

    return render(request, 'documents/document_list.html', {
        'documents': page_obj,
        'document_type': document_type,
        'doc_type_display': doc_type_display,
        'page_obj': page_obj,
    })


@login_required
def document_view(request, pk):
    """View a single document (PDF or table)"""
    document = get_object_or_404(Document, pk=pk)

    # Check permission
    if not document.is_active:
        raise Http404("Document not available.")

    if not document.is_public and not request.user.is_staff:
        if request.user not in document.view_permissions.all():
            if request.user.role not in ['CCO', 'Admin']:
                messages.error(request, "You don't have permission to view this document.")
                return redirect('dashboard:index')

    # Log view activity
    from apps.accounts.models import UserActivityLog
    UserActivityLog.log_activity(
        user=request.user,
        action='view',
        model_name='Document',
        object_id=document.id,
        object_repr=document.title,
        changes={'document_type': document.document_type}
    )

    # Handle external links
    if document.external_url:
        return redirect(document.external_url)

    # Handle PDF view
    if document.pdf_file:
        return render(request, 'documents/pdf_viewer.html', {
            'document': document,
            'pdf_url': document.pdf_file.url
        })

    # Handle table data (PO Box, Client lists)
    if document.table_data:
        table_data = document.table_data
        if isinstance(table_data, str):
            try:
                table_data = json.loads(table_data)
            except:
                table_data = {'columns': [], 'rows': []}

        # Special template for PO Box list
        if document.document_type == 'po_box':
            return render(request, 'documents/po_box_list.html', {
                'document': document,
                'table_data': table_data
            })

        return render(request, 'documents/table_view.html', {
            'document': document,
            'table_data': table_data
        })

    # Fallback to document_detail.html for any other document type
    return render(request, 'documents/document_detail.html', {'document': document})


@login_required
def download_pdf(request, pk):
    """Download PDF file"""
    document = get_object_or_404(Document, pk=pk)

    # Check permission
    if not document.is_public and not request.user.is_staff:
        if request.user not in document.view_permissions.all():
            messages.error(request, "You don't have permission to download this document.")
            return redirect('dashboard:index')

    if not document.pdf_file:
        raise Http404("No PDF file available.")

    # Log download activity
    from apps.accounts.models import UserActivityLog
    UserActivityLog.log_activity(
        user=request.user,
        action='download',
        model_name='Document',
        object_id=document.id,
        object_repr=document.title,
        changes={}
    )

    response = HttpResponse(document.pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{document.title}.pdf"'
    return response


@login_required
def po_box_list(request):
    """Display PO Box list in a formatted way"""
    document = Document.objects.filter(document_type='po_box', is_active=True).first()

    if not document:
        return render(request, 'documents/coming_soon.html', {
            'title': 'PO Box List - Coming Soon'
        })

    table_data = document.table_data
    if isinstance(table_data, str):
        import json
        table_data = json.loads(table_data)

    return render(request, 'documents/po_box_list.html', {
        'document': document,
        'po_boxes': table_data.get('rows', []),
        'columns': table_data.get('columns', [])
    })


# ==================== LEGACY/COMPATIBILITY VIEWS ====================

@staff_member_required
def document_manage(request):
    """Legacy admin view for managing documents (redirects to new management)"""
    return redirect('documents:document_management')


@staff_member_required
def document_toggle_visibility(request, pk):
    """Legacy toggle visibility (redirects to new toggle)"""
    return document_toggle_status(request, pk)