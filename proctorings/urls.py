from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.index, name='index'),  # Default index page
    path('home/', views.home, name='home'),  # Protected home page
    path('login/', auth_views.LoginView.as_view(template_name='index.html'), name='login'),  # Use Django's login view
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),  # Add a logout view
]
