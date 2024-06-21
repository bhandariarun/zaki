
from django.contrib import admin
from django.urls import path, include , re_path
from . import views


urlpatterns = [
    re_path('login',views.login),
    re_path('signup',views.signup),
    re_path('testtoken',views.testtoken),
    re_path('update-user/', views.update_user, name='update_user'),
    re_path('logout',views.logout, name='logout'),
]