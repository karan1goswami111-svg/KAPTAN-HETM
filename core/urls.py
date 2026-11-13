from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('verify-reg-otp/', views.verify_reg_otp_view, name='verify_reg_otp'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
    path('google-auth-callback/', views.google_auth_callback_view, name='google_auth_callback'),
    path('set-google-name/', views.set_google_name_view, name='set_google_name'),
    
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile-settings/', views.profile_settings_view, name='profile_settings'),
    path('verify-profile-otp/', views.verify_profile_otp_view, name='verify_profile_otp'),
    path('logout/', views.logout_view, name='logout'),
    path('delete-account/', views.delete_account_view, name='delete_account'),
    path('fresh-start/', views.fresh_start_view, name='fresh_start'),
    
    path('add-personal-expense/', views.add_personal_expense_view, name='add_personal_expense'),
    path('delete-personal-expense/<int:exp_id>/', views.delete_personal_expense_view, name='delete_personal_expense'),
    path('dismiss-budget-warning/', views.dismiss_budget_warning_view, name='dismiss_budget_warning'),
    
    path('group/<int:group_id>/', views.group_detail_view, name='group_detail'),
    path('group/<int:group_id>/delete/', views.delete_group_view, name='delete_group'),
    path('group/<int:group_id>/settle/', views.settle_group_view, name='settle_group'),
    path('group/<int:group_id>/export-pdf/', views.export_group_pdf_view, name='export_group_pdf'),
    path('expense/<int:expense_id>/delete/', views.delete_expense_view, name='delete_expense'),
    path('group/<int:group_id>/member/<str:member_name>/delete/', views.delete_member_view, name='delete_member'),
    
    path('global-group-expenses/', views.global_group_expenses_view, name='global_group_expenses'),
    path('info/', views.info_view, name='info'),
]