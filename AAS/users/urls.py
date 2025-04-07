from django.urls import path
from django.contrib.auth.views import LogoutView
from users.views import RegisterView,ImageCodeView,SmsCodeView,LoginView,ForgetPasswordView

urlpatterns = [
    # 参数1：路由
    # 参数2：视图函数
    # 参数3：路由名，方便通过reverse来获取路由
    path('register/',RegisterView.as_view(),name='register'),

    path('imagecode/', ImageCodeView.as_view(), name='imagecode'),

    path('smscode/', ImageCodeView.as_view(), name='smscode'),

    path('login/', LoginView.as_view(),name='login'),
    path('logout/', LogoutView.as_view(next_page='users:login'), name='logout'),  # 修改这行
    path('forgetpassword/', ForgetPasswordView.as_view(),name='forgetpassword'),
]