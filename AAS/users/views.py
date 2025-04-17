from django.contrib.auth import login, authenticate
from django.http import HttpResponseBadRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse

# Create your views here.
from django.views import View
from django_redis import get_redis_connection
from libs.captcha.captcha import captcha
import re
from users.models import User, Patient, Doctor, AdminProfile
from django.db import DatabaseError, transaction
from utils.response_code import RETCODE
from random import randint
from libs.yuntongxun.sms import CCP
import logging

logger=logging.getLogger('django')

#注册视图
ADMIN_KEY = "XK-28A7-B9F3-45C6-D1E0"

class RegisterView(View):
    """用户注册"""

    def get(self, request):
        """
        提供注册界面
        :param request: 请求对象
        :return: 注册界面
        """
        return render(request, 'register.html')

    def post(self, request):
        # 接收参数
        print("Received form data:", request.POST)
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        role = request.POST.get('role', 'patient')
        admin_key = request.POST.get('admin_key', '')
        print("Selected role:", role)
        # 判断参数是否齐全
        if not all([mobile, password, password2]):
            return HttpResponseBadRequest('缺少必传参数')
        # 如果是管理员注册，检查密匙
        if role == 'admin' and admin_key != ADMIN_KEY:
            return HttpResponseBadRequest('管理员密匙不正确')
        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('请输入正确的手机号码')
        # 判断密码是否是8-20个数字
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('请输入8-20位的密码')
        # 判断两次密码是否一致
        if password != password2:
            return HttpResponseBadRequest('两次输入的密码不一致')

        # 保存注册数据
        try:
            with transaction.atomic():  # 使用事务确保数据一致性
                # 创建用户
                user = User.objects.create_user(
                    username=mobile,
                    mobile=mobile,
                    password=password,
                    role=role
                )

                # 根据角色创建对应档案
                if role == 'patient':
                    Patient.objects.create(
                        user=user,
                        patient_id=f"PAT{mobile[-6:]}",
                    )
                elif role == 'doctor':
                    Doctor.objects.create(
                        user=user,
                        license_number=f"DOC{user.id:06d}",
                    )
                elif role == 'admin':
                    AdminProfile.objects.create(
                        user=user,
                        position="系统管理员",
                        department="系统管理部",
                        access_level="super"
                    )
        except DatabaseError:
            return HttpResponseBadRequest('注册失败')
        login(request, user)
        # 响应注册结果
        return redirect(reverse('users:login'))

    @classmethod
    def create_user(cls, mobile, password, username=None, role='patient', **extra_fields):
        if not mobile:
            raise ValueError('必须提供手机号')
        if not password:
            raise ValueError('必须提供密码')

        # 如果没有提供username，默认使用mobile
        username = username or mobile

        user = cls(
            username=username,
            mobile=mobile,
            role=role,
            **extra_fields
        )
        user.set_password(password)
        user.save()
        return user


class LoginView(View):

    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        # 接受参数
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        remember = request.POST.get('remember')

        # 校验参数
        # 判断参数是否齐全
        if not all([mobile, password]):
            return HttpResponseBadRequest('缺少必传参数')

        # 判断手机号是否正确
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('请输入正确的手机号')

        # 判断密码是否是8-20个数字
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('密码最少8位，最长20位')

        # 认证登录用户
        user = authenticate(mobile=mobile, password=password)

        if user is None:
            return HttpResponseBadRequest('用户名或密码错误')

        # 实现状态保持
        login(request, user)

        # 根据用户角色跳转到不同页面
        if user.role == 'admin':
            response = redirect(reverse('admin:index'))  # 管理员后台
        elif user.role == 'doctor':
            response = redirect(reverse('doctor:index'))  # 医生主页
        else:
            response = redirect(reverse('patient:index'))  # 患者主页

        # 设置状态保持的周期
        if remember != 'on':
            # 没有记住用户：浏览器会话结束就过期
            request.session.set_expiry(0)
            # 设置cookie
            response.set_cookie('is_login', True)
            response.set_cookie('username', user.username, max_age=30 * 24 * 3600)
        else:
            # 记住用户：None表示两周后过期
            request.session.set_expiry(None)
            # 设置cookie
            response.set_cookie('is_login', True, max_age=14 * 24 * 3600)
            response.set_cookie('username', user.username, max_age=30 * 24 * 3600)

        return response

class ForgetPasswordView(View):

    def get(self, request):
        return render(request, 'forget_password.html')

    def post(self, request):
        # 接收参数
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        image_code = request.POST.get('image_code')
        uuid = request.POST.get('uuid')

        # 判断参数是否齐全
        if not all([mobile, password, password2, image_code, uuid]):
            return HttpResponseBadRequest('缺少必传参数')

        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('请输入正确的手机号码')

        # 判断密码是否是8-20个数字
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('请输入8-20位的密码')

        # 判断两次密码是否一致
        if password != password2:
            return HttpResponseBadRequest('两次输入的密码不一致')

        # 验证图片验证码
        redis_conn = get_redis_connection('default')
        image_code_server = redis_conn.get('img:%s' % uuid)
        if image_code_server is None:
            return HttpResponseBadRequest('图片验证码已过期')
        if image_code.lower() != image_code_server.decode().lower():
            return HttpResponseBadRequest('图片验证码错误')

        # 根据手机号查询数据
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            # 如果该手机号不存在，则注册个新用户
            try:
                User.objects.create_user(username=mobile, mobile=mobile, password=password)
            except Exception:
                return HttpResponseBadRequest('修改失败，请稍后再试')
        else:
            # 修改用户密码
            user.set_password(password)
            user.save()

        # 跳转到登录页面
        response = redirect(reverse('users:login'))

        return response
class ImageCodeView(View):

    def get(self,request):
        #获取前端传递过来的参数
        uuid=request.GET.get('uuid')
        #判断参数是否为None
        if uuid is None:
            return HttpResponseBadRequest('请求参数错误')
        # 获取验证码内容和验证码图片二进制数据
        text, image = captcha.generate_captcha()
        # 将图片验内容保存到redis中，并设置过期时间
        redis_conn = get_redis_connection('default')
        redis_conn.setex('img:%s' % uuid, 300, text)
        # 返回响应，将生成的图片以content_type为image/jpeg的形式返回给请求
        return HttpResponse(image, content_type='image/jpeg')

class SmsCodeView(View):

    def get(self,request):
        # 接收参数
        image_code_client = request.GET.get('image_code')
        uuid = request.GET.get('uuid')
        mobile=request.GET.get('mobile')

        # 校验参数
        if not all([image_code_client, uuid,mobile]):
            return JsonResponse({'code': RETCODE.NECESSARYPARAMERR, 'errmsg': '缺少必传参数'})

        # 创建连接到redis的对象
        redis_conn = get_redis_connection('default')
        # 提取图形验证码
        image_code_server = redis_conn.get('img:%s' % uuid)
        if image_code_server is None:
            # 图形验证码过期或者不存在
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图形验证码失效'})
        # 删除图形验证码，避免恶意测试图形验证码
        try:
            redis_conn.delete('img:%s' % uuid)
        except Exception as e:
            logger.error(e)
        # 对比图形验证码
        image_code_server = image_code_server.decode()  # bytes转字符串
        if image_code_client.lower() != image_code_server.lower():  # 转小写后比较
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '输入图形验证码有误'})

        # 生成短信验证码：生成6位数验证码
        sms_code = '%06d' % randint(0, 999999)
        #将验证码输出在控制台，以方便调试
        logger.info(sms_code)
        # 保存短信验证码到redis中，并设置有效期
        redis_conn.setex('sms:%s' % mobile, 300, sms_code)
        # 发送短信验证码
        CCP().send_template_sms(mobile, [sms_code, 5],1)

        # 响应结果
        return JsonResponse({'code': RETCODE.OK, 'errmsg': '发送短信成功'})

