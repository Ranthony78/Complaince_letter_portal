# apps/documents/urls.py (Complete)
from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    # ==================== USER DOCUMENT VIEWING ====================
    # Document viewing and download
    path('<int:pk>/view/', views.document_view, name='view'),
    path('<int:pk>/download/', views.download_pdf, name='download'),

    # Document listing by type
    path('type/<str:document_type>/', views.document_list, name='list_by_type'),
    path('', views.document_list, name='list'),

    # Special views
    path('po-box-list/', views.po_box_list, name='po_box_list'),

    # ==================== ADMIN DOCUMENT MANAGEMENT ====================
    # Main management dashboard
    path('management/', views.document_management, name='document_management'),

    # CRUD operations
    path('management/create/', views.document_create, name='document_create'),
    path('management/<int:pk>/edit/', views.document_edit, name='document_edit'),
    path('management/<int:pk>/delete/', views.document_delete, name='document_delete'),
    path('management/<int:pk>/toggle/', views.document_toggle_status, name='document_toggle'),

    # Bulk operations
    path('management/bulk-upload/', views.document_bulk_upload, name='document_bulk_upload'),
]