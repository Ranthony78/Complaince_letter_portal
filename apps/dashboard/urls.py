# apps/dashboard/urls.py
from django.urls import path
from django.views.generic import RedirectView
from django.contrib.auth.decorators import login_required
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Dashboard home page
    path('', login_required(views.DashboardView.as_view()), name='index'),

    # Statistics and analytics
    path('stats/', login_required(views.DashboardStatsView.as_view()), name='stats'),
    path('analytics/', login_required(views.AnalyticsView.as_view()), name='analytics'),

    # Widgets and components
    path('widgets/', login_required(views.WidgetsView.as_view()), name='widgets'),

    # User activity
    path('my-activity/', login_required(views.MyActivityView.as_view()), name='my_activity'),

    # Notifications center
    path('notifications/', login_required(views.DashboardNotificationsView.as_view()), name='notifications'),

    # Quick actions
    path('quick-actions/', login_required(views.QuickActionsView.as_view()), name='quick_actions'),

    # Search
    path('search/', login_required(views.DashboardSearchView.as_view()), name='search'),
]