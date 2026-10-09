from django.urls import path

from .controlador import LoginView, LogoutView

app_name = 'login'

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]

