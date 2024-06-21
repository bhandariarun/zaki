from django.urls import path
from . import views
from .views import Logview

urlpatterns = [
    path('logs/', views.log_list, name='log_list'),
    path('logs/<int:pk>/', views.log_detail, name='log_detail'),
    path('log-counts/', views.log_count_list, name='log_count_list'),
    path('filter-logs/', views.filter_logs, name='filter-logs'),
    path("logs_views/", views.logs_views, name="logs_views"),
    path("log_api/", Logview.as_view(), name="log_api"),
    path('total-logs-count/', views.total_logs_count, name='total-logs-count'),
    path('recent-logs/', views.recent_logs, name='recent-logs'),
    path('logs/grouped/', views.logs_grouped_by_group_and_stream, name='logs_grouped_by_group_and_stream'),
    path('logs/log_count_interval/',views.log_count_interval,name='log_count_interval'),
    path('last_seven_days/',views.last_seven_days,name='last_seven_days'),
]
