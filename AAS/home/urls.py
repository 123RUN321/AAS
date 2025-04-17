from django.urls import path
from .views import IndexView, DiagnoseView, ProfileView
from . import views
urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('diagnose/', DiagnoseView.as_view(), name='diagnose'),
    path('upload/', views.upload_nrrd, name='upload_nrrd'),
    path('list/', views.list_nrrd_images, name='list_nrrd_images'),
    path('nrrd-viewer/', views.nrrd_viewer, name='nrrd_viewer'),
    path('ai_chat/', views.ai_chat_view, name='ai_chat'),
    path('api/ai-chat/', views.ai_chat, name='ai_chat_api'),  # AI问答API端点
]