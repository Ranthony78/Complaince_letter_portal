# apps/accounts/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView  # Add this import
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='accounts:login'), name='logout'),
    path('password-change/', login_required(views.ChangePasswordView.as_view()), name='change_password'),
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='accounts/password_reset_email.html',
        subject_template_name='accounts/password_reset_subject.txt'
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),

    # Profile Management
    path('profile/', login_required(views.ProfileView.as_view()), name='profile'),
    path('profile/update/', login_required(views.ProfileUpdateView.as_view()), name='profile_update'),
    path('profile/settings/', login_required(views.UserSettingsView.as_view()), name='user_settings'),
    path('profile/preferences/', login_required(views.UserPreferencesView.as_view()), name='user_preferences'),

    # Notifications
    path('notifications/', login_required(views.NotificationListView.as_view()), name='notifications'),
    path('notifications/<int:pk>/read/', login_required(views.mark_notification_read), name='notification_read'),
    path('notifications/read-all/', login_required(views.mark_all_notifications_read), name='notifications_read_all'),
    path('notifications/<int:pk>/delete/', login_required(views.delete_notification), name='notification_delete'),

    # User Management (CCO Only)
    path('users/', login_required(views.UserManagementView.as_view()), name='user_management'),
    path('users/create/', login_required(views.CreateUserView.as_view()), name='create_user'),
    path('users/<int:pk>/edit/', login_required(views.EditUserView.as_view()), name='edit_user'),
    path('users/<int:pk>/delete/', login_required(views.DeleteUserView.as_view()), name='delete_user'),
    path('users/<int:pk>/toggle-status/', login_required(views.toggle_user_status), name='toggle_user_status'),
    path('users/<int:pk>/reset-password/', login_required(views.reset_user_password), name='reset_user_password'),
    path('users/<int:pk>/impersonate/', login_required(views.impersonate_user), name='impersonate_user'),
    path('users/stop-impersonate/', login_required(views.stop_impersonate), name='stop_impersonate'),

    # Role Management (CCO Only)
    path('roles/', login_required(views.RoleManagementView.as_view()), name='role_management'),
    path('roles/create/', login_required(views.CreateRoleView.as_view()), name='create_role'),
    path('roles/<int:pk>/edit/', login_required(views.EditRoleView.as_view()), name='edit_role'),
    path('roles/<int:pk>/delete/', login_required(views.DeleteRoleView.as_view()), name='delete_role'),
    path('roles/permissions/', login_required(views.RolePermissionsView.as_view()), name='role_permissions'),

    # Role Permissions API Endpoints (CCO Only) - CRITICAL: These must be added!
    path('roles/<int:pk>/permissions/load/', login_required(views.load_role_permissions), name='load_role_permissions'),
    path('roles/permissions/save/', login_required(views.save_role_permissions), name='save_role_permissions'),
    path('roles/<int:pk>/permissions/reset/', login_required(views.reset_role_permissions),
         name='reset_role_permissions'),

    # Department Management (CCO Only)
    path('departments/', login_required(views.DepartmentManagementView.as_view()), name='department_management'),
    path('departments/create/', login_required(views.CreateDepartmentView.as_view()), name='create_department'),
    path('departments/<int:pk>/edit/', login_required(views.EditDepartmentView.as_view()), name='edit_department'),

    # Activity Logs
    path('activities/', login_required(views.ActivityLogView.as_view()), name='activity_logs'),
    path('login-history/', login_required(views.LoginHistoryView.as_view()), name='login_history'),

    # Reports
    path('reports/user-activity/', login_required(views.UserActivityReportView.as_view()), name='user_activity_report'),

    # Help & Support
    path('help/', login_required(views.HelpView.as_view()), name='help'),
    path('help/guide/', login_required(views.UserGuideView.as_view()), name='user_guide'),
]