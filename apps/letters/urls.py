# apps/letters/urls.py
from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views

app_name = 'letters'

urlpatterns = [
    # Letter listing and search
    path('', login_required(views.LetterListView.as_view()), name='list'),
    path('my-drafts/', login_required(views.MyDraftsView.as_view()), name='my_drafts'),
    path('search/', login_required(views.LetterSearchView.as_view()), name='search'),

    # Create letters
    path('create/facs/', login_required(views.CreateFACSLetterView.as_view()), name='create_facs'),
    path('create/artiva/', login_required(views.CreateArtivaLetterView.as_view()), name='create_artiva'),

    # Letter detail views
    path('<int:pk>/', login_required(views.LetterDetailView.as_view()), name='detail'),
    path('<int:pk>/facs/', login_required(views.FACSLetterDetailView.as_view()), name='facs_detail'),
    path('<int:pk>/artiva/', login_required(views.ArtivaLetterDetailView.as_view()), name='artiva_detail'),

    # Letter edit and update
    path('<int:pk>/edit/', login_required(views.LetterEditView.as_view()), name='edit'),
    path('<int:pk>/edit/facs/', login_required(views.FACSEditView.as_view()), name='edit_facs'),
    path('<int:pk>/edit/artiva/', login_required(views.ArtivaEditView.as_view()), name='edit_artiva'),
    path('<int:pk>/update-status/', login_required(views.update_letter_status), name='update_status'),
    path('<int:pk>/submit/', login_required(views.submit_for_review), name='submit_for_review'),

    # Approval URLs
    path('pending/', login_required(views.PendingApprovalsView.as_view()), name='pending_approvals'),
    path('radius/pending/', login_required(views.RadiusPendingView.as_view()), name='radius_pending'),
    path('sessions/pending/', login_required(views.SessionsPendingView.as_view()), name='sessions_pending'),
    path('client/pending/', login_required(views.ClientPendingView.as_view()), name='client_approvals'),

    # Approval actions
    path('<int:pk>/radius/approve/', login_required(views.radius_approve), name='radius_approve'),
    path('<int:pk>/sessions/approve/', login_required(views.sessions_approve), name='sessions_approve'),
    path('<int:pk>/client/approve/', login_required(views.client_approve), name='client_approve'),
    path('<int:pk>/cco/final/', login_required(views.cco_final_approve), name='cco_final_approve'),

    # CCO Approval Management
    path('<int:pk>/approval-management/', login_required(views.cco_approval_management), name='cco_approval_management'),
    path('<int:pk>/update-radius-approval/', login_required(views.update_radius_approval), name='update_radius_approval'),
    path('<int:pk>/update-sessions-approval/', login_required(views.update_sessions_approval), name='update_sessions_approval'),

    # Version control
    path('<int:pk>/versions/', login_required(views.version_history), name='version_history'),
    path('<int:pk>/version/<str:version>/download/', login_required(views.download_version), name='download_version'),
    path('<int:pk>/compare/', login_required(views.compare_versions), name='compare_versions'),
    path('<int:pk>/create-version/', login_required(views.create_new_version), name='create_version'),

    # Document management
    path('<int:pk>/documents/', login_required(views.document_list), name='document_list'),
    path('<int:pk>/documents/upload/', login_required(views.upload_document), name='upload_document'),
    path('documents/<int:doc_id>/download/', login_required(views.download_document), name='download_document'),
    path('documents/<int:doc_id>/delete/', login_required(views.delete_document), name='delete_document'),
    path('documents/<int:doc_id>/update/', views.update_document, name='update_document'),

    # Ticket management
    path('<int:pk>/ticket/', login_required(views.ticket_detail), name='ticket_detail'),
    path('<int:pk>/ticket/create/', login_required(views.create_ticket), name='create_ticket'),
    path('ticket/<int:ticket_id>/update/', login_required(views.update_ticket), name='update_ticket'),

    # Reports
    path('reports/', login_required(views.ReportsView.as_view()), name='reports'),
    path('reports/generate/', login_required(views.generate_report), name='generate_report'),
    path('reports/export/', login_required(views.export_data), name='export_data'),

    # Audit log
    path('audit/', login_required(views.AuditLogView.as_view()), name='audit_log'),

    # Completed letters
    path('completed/', login_required(views.CompletedLettersView.as_view()), name='completed_list'),

    # Delegated letters
    path('delegated/', login_required(views.DelegatedLettersView.as_view()), name='delegated_letters'),

    # Bulk actions (CCO only)
    path('bulk-approve/', login_required(views.bulk_approve), name='bulk_approve'),
    path('bulk-delete/', login_required(views.bulk_delete), name='bulk_delete'),
]