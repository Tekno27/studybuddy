from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'studybuddy'

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='studybuddy/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('partners/', views.find_partners, name='find_partners'),
    path('partners/<int:profile_id>/request/', views.send_study_request, name='send_study_request'),
    path('requests/', views.requests_view, name='requests'),
    path('requests/<int:request_id>/<str:action>/', views.update_study_request, name='update_study_request'),
    path('connections/', views.connections, name='connections'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('partners/<int:profile_id>/profile/', views.partner_profile, name='partner_profile'),
    path('partners/<int:profile_id>/report/', views.report_student, name='report_student'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('groups/', views.groups_list, name='groups_list'),
    path('groups/create/', views.create_group, name='create_group'),
    path('groups/<int:group_id>/', views.group_detail, name='group_detail'),
    path('groups/<int:group_id>/join/', views.join_group, name='join_group'),
    path('groups/<int:group_id>/leave/', views.leave_group, name='leave_group'),
    path('groups/<int:group_id>/sessions/create/', views.create_session, name='create_session'),
    path('sessions/', views.sessions_list, name='sessions_list'),
]