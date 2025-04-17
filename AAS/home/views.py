
from django.shortcuts import render, get_object_or_404
from django.views import View
import uuid
import logging
import gc  # 添加垃圾回收模块
# 设置日志
logger = logging.getLogger(__name__)

from django.utils.decorators import method_decorator
import os
import nrrd
import numpy as np
from io import BytesIO
from PIL import Image
from django.contrib.auth.decorators import login_required
from .models import NRRDImage
import base64
import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def ai_chat_view(request):
    """渲染AI问答页面"""
    return render(request, 'ai_chat.html')

@csrf_exempt
def ai_chat(request):
    if request.method == 'POST':
        try:
            # 1. 解析请求数据
            try:
                data = json.loads(request.body.decode('utf-8'))
                user_message = data.get('message', '')
            except json.JSONDecodeError as e:
                return JsonResponse({'status': 'error', 'message': '无效的JSON格式'}, status=400)

            # 2. 验证消息内容
            if not user_message or not isinstance(user_message, str):
                return JsonResponse({'status': 'error', 'message': '消息不能为空'}, status=400)

            # 3. 调用DeepSeek API
            api_url = "https://api.deepseek.com/v1/chat/completions"  # 修复 URL
            headers = {
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个专业的医疗AI助手，专门回答关于主动脉疾病的问题。"},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.7,
                "max_tokens": 1024
            }

            logger.info(f"准备调用DeepSeek API，消息长度: {len(user_message)}")

            # 4. 添加超时和错误处理
            try:
                response = requests.post(
                    api_url,
                    headers=headers,
                    json=payload,
                    timeout=60  # 增加超时时间
                )
                response.raise_for_status()  # 检查HTTP错误
            except requests.exceptions.RequestException as e:
                logger.error(f"DeepSeek API请求失败: {str(e)}")
                return JsonResponse({'status': 'error', 'message': f'API请求失败: {str(e)}'}, status=500)

            # 5. 解析API响应
            try:
                response_data = response.json()
                ai_response = response_data['choices'][0]['message']['content']
                logger.info(f"成功获取AI响应，长度: {len(ai_response)}")

                return JsonResponse({
                    'status': 'success',
                    'response': ai_response
                })

            except (KeyError, ValueError) as e:
                logger.error(f"响应解析错误: {str(e)}，原始响应: {response.text}")
                return JsonResponse({'status': 'error', 'message': 'API响应格式错误'}, status=500)

        except Exception as e:
            logger.exception("服务器内部错误")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': '只接受POST请求'}, status=405)

@login_required
def nrrd_viewer(request):
    return render(request, 'nrrd_viewer.html')  # 直接引用，不带app名前缀


@login_required
@csrf_exempt
def upload_nrrd(request):
    if request.method == 'POST' and request.FILES.get('nrrd_file'):
        nrrd_file = request.FILES['nrrd_file']
        name = request.POST.get('name', os.path.splitext(nrrd_file.name)[0])

        # 创建临时文件路径
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads')
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, nrrd_file.name)

        try:
            # 保存上传文件到临时位置
            with open(temp_file_path, 'wb+') as destination:
                for chunk in nrrd_file.chunks():
                    destination.write(chunk)

            # 读取NRRD文件
            nrrd_data, nrrd_header = nrrd.read(temp_file_path)

            # 创建NRRDImage实例并保存
            nrrd_image = NRRDImage(
                user=request.user,
                image=nrrd_file,  # 原始文件保存到ImageField
                name=name
            )
            nrrd_image.save()

            # 生成三个正交切面的预览
            previews = {}
            if len(nrrd_data.shape) == 3:
                # 冠状面 (Coronal)
                slice_coronal = nrrd_data[:, :, nrrd_data.shape[2] // 2]
                previews['coronal'] = generate_slice_preview(slice_coronal)

                # 矢状面 (Sagittal)
                slice_sagittal = nrrd_data[:, nrrd_data.shape[1] // 2, :]
                previews['sagittal'] = generate_slice_preview(slice_sagittal)

                # 横断面 (Axial)
                slice_axial = nrrd_data[nrrd_data.shape[0] // 2, :, :]
                previews['axial'] = generate_slice_preview(slice_axial)
            elif len(nrrd_data.shape) == 2:
                # 如果是2D图像，直接生成预览
                previews['slice'] = generate_slice_preview(nrrd_data)

            return JsonResponse({
                'status': 'success',
                'id': nrrd_image.id,
                'name': nrrd_image.name,
                'preview_data': previews.get('axial', previews.get('slice')),  # 默认使用axial或slice预览
                'previews': previews,  # 所有切面预览
                'image_url': nrrd_image.image.url,  # 原始NRRD文件URL
                'is_3d': len(nrrd_data.shape) == 3,  # 是否是3D数据
                'dimensions': list(nrrd_data.shape)  # 图像维度
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f"处理NRRD文件时出错: {str(e)}"
            }, status=500)

        finally:
            # 清理临时文件
            try:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            except Exception as e:
                print(f"删除临时文件失败: {str(e)}")

    return JsonResponse({
        'status': 'error',
        'message': '无效请求: 需要POST方法和nrrd_file文件'
    }, status=400)


def generate_slice_preview(slice_data):
    """生成单一切片的预览图(Base64编码)"""
    # 归一化到0-255
    if np.max(slice_data) > np.min(slice_data):
        normalized = ((slice_data - np.min(slice_data)) /
                      (np.max(slice_data) - np.min(slice_data)) * 255).astype(np.uint8)
    else:
        normalized = np.zeros(slice_data.shape, dtype=np.uint8)

    # 创建PIL图像
    img = Image.fromarray(normalized)

    # 转换为PNG格式的base64编码
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode('utf-8')}"


@login_required
def list_nrrd_images(request):
    """获取当前用户的NRRD图像列表"""
    images = NRRDImage.objects.filter(user=request.user).values('id', 'name', 'image')

    image_list = []
    for img in images:
        image_list.append({
            'id': img['id'],
            'name': img['name'],
            'image_url': img['image'],  # 自动转换为完整URL
            # 注意：这里需要前端根据image_url自行获取预览，或者您可以添加预览字段到模型
        })

    return JsonResponse({'images': image_list})

@login_required
def list_nrrd_images(request):
    images = NRRDImage.objects.filter(user=request.user).values('id', 'name', 'image')
    image_list = []
    for img in images:
        image_list.append({
            'id': img['id'],
            'name': img['name'],
            'image_url': f"/media/{img['image']}"
        })
    return JsonResponse({'images': image_list})

# 登录验证装饰器
class LoginRequiredMixin:
    @method_decorator(login_required(login_url='/users/login/'))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

@method_decorator(csrf_exempt, name='dispatch')
class DiagnoseView(LoginRequiredMixin, View):
    PYTORCH_SERVER_URL = 'http://localhost:5000/predict'
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB限制

    def post(self, request):
        # 在开始处理前强制垃圾回收
        gc.collect()

        # 检查文件是否存在
        if 'file' not in request.FILES:
            logger.error("未收到上传文件")
            return JsonResponse({'error': '未收到文件', 'detail': '请选择.nrrd格式的文件上传'},
                                status=400, json_dumps_params={'ensure_ascii': False})

        uploaded_file = request.FILES['file']
        logger.info("收到诊断请求，文件名: %s, 大小: %s", uploaded_file.name, uploaded_file.size)

        # 检查文件大小
        if uploaded_file.size > self.MAX_FILE_SIZE:
            logger.error("文件大小超过限制: %s > %s", uploaded_file.size, self.MAX_FILE_SIZE)
            return JsonResponse({
                'error': '文件过大',
                'detail': f'文件大小不能超过{self.MAX_FILE_SIZE / 1024 / 1024}MB'
            }, status=413)

        # 检查文件扩展名
        if not uploaded_file.name.lower().endswith('.nrrd'):
            logger.error("文件格式不正确: %s", uploaded_file.name)
            return JsonResponse({
                'error': '文件格式错误',
                'detail': '请上传.nrrd格式的文件'
            }, status=400)

        # 创建临时目录
        temp_dir = os.path.join(settings.BASE_DIR, 'temp_uploads')
        os.makedirs(temp_dir, exist_ok=True)
        filename = f"{uuid.uuid4()}.nrrd"
        filepath = os.path.join(temp_dir, filename)

        try:
            # 1. 使用更安全的方式保存临时文件
            with open(filepath, 'wb+') as destination:
                for chunk in uploaded_file.chunks(chunk_size=2 * 1024 * 1024):  # 2MB chunks
                    destination.write(chunk)
                    destination.flush()  # 确保数据写入磁盘
                    os.fsync(destination.fileno())  # 强制同步到磁盘
            logger.info("文件临时保存成功: %s", filepath)

            # 2. 使用上下文管理器确保文件句柄正确关闭
            try:
                with open(filepath, 'rb') as f:
                    # 使用流式上传
                    response = requests.post(
                        self.PYTORCH_SERVER_URL,
                        files={'file': (filename, f)},
                        timeout=(30, 120),  # 延长超时时间
                        stream=True  # 启用流式传输
                    )
                    logger.info("PyTorch服务响应状态: %s", response.status_code)

                # 3. 处理响应
                if response.status_code != 200:
                    error_msg = response.text[:500]  # 限制错误消息长度
                    logger.error("模型服务错误: %s", error_msg)
                    return JsonResponse({
                        'error': '模型服务暂时不可用',
                        'detail': error_msg
                    }, status=503)

                # 立即解析并释放响应内存
                prediction = response.json()
                logger.info("预测结果: %s", prediction)
                del response  # 显式删除响应对象

                # 4. 构建返回结果
                result = {
                    'status': 'success',
                    'has_dissection': prediction.get('has_dissection', False),
                    'diagnosis': '检测到主动脉夹层' if prediction.get('has_dissection') else '未检测到主动脉夹层',
                    'confidence': prediction.get('confidence', 0),
                    'details': [
                        f"AI诊断置信度: {prediction.get('confidence', 0):.1f}%",
                        f"分类结果: {prediction.get('class_name', '未知')}"
                    ],
                    'recommendations': [
                        '立即就医' if prediction.get('has_dissection') else '定期复查',
                        '控制血压',
                        '避免剧烈运动' if prediction.get('has_dissection') else '适度运动'
                    ]
                }

                # 返回前再次强制垃圾回收
                gc.collect()

                return JsonResponse(result, json_dumps_params={'ensure_ascii': False})

            except requests.exceptions.Timeout:
                logger.error("连接PyTorch服务超时")
                return JsonResponse({
                    'error': '服务响应超时',
                    'detail': 'AI模型处理时间过长，请稍后重试'
                }, status=504)
            except requests.exceptions.RequestException as e:
                logger.error("PyTorch服务连接错误: %s", str(e))
                return JsonResponse({
                    'error': '无法连接AI服务',
                    'detail': str(e)
                }, status=502)

        except IOError as e:
            logger.error("文件操作错误: %s", str(e))
            return JsonResponse({
                'error': '文件处理失败',
                'detail': '服务器无法处理上传的文件'
            }, status=500)
        except MemoryError:
            logger.error("内存不足错误")
            # 紧急清理临时文件
            if 'filepath' in locals() and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass
            return JsonResponse({
                'error': '内存不足',
                'detail': '服务器无法处理这么大的文件，请尝试上传较小的文件'
            }, status=500)
        except Exception as e:
            logger.exception("服务器内部错误")
            return JsonResponse({
                'error': '服务器内部错误',
                'detail': str(e)
            }, status=500)
        finally:
            # 确保临时文件被删除
            if 'filepath' in locals() and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    logger.info("已清理临时文件: %s", filepath)
                except Exception as e:
                    logger.error("临时文件删除失败: %s", str(e))

            # 最终强制垃圾回收
            gc.collect()


class ProfileView(LoginRequiredMixin, View):
    def get(self, request):
        """展示用户资料"""
        user = request.user
        context = {
            'user': user,
            'bmi': user.bmi,
            'age': user.age,
            'gender_display': user.get_gender_display(),
            'blood_type_display': user.get_blood_type_display() if user.blood_type else None,
            'exercise_frequency_display': user.get_exercise_frequency_display() if user.exercise_frequency else None,
        }
        return render(request, 'profile.html', context=context)

    def post(self, request):
        """修改用户资料"""
        user = request.user
        data = request.POST

        # 基本信息
        user.username = data.get('username', user.username)
        user.user_desc = data.get('user_desc', user.user_desc)

        # 健康信息
        user.gender = data.get('gender', user.gender)
        user.birth_date = data.get('birth_date', user.birth_date)
        user.height = data.get('height', user.height)
        user.weight = data.get('weight', user.weight)

        # 健康指标
        user.blood_type = data.get('blood_type', user.blood_type)
        user.blood_pressure_high = data.get('blood_pressure_high', user.blood_pressure_high)
        user.blood_pressure_low = data.get('blood_pressure_low', user.blood_pressure_low)
        user.blood_sugar = data.get('blood_sugar', user.blood_sugar)
        user.cholesterol = data.get('cholesterol', user.cholesterol)

        # 健康习惯
        user.is_smoker = data.get('is_smoker') == 'on'
        user.is_drinker = data.get('is_drinker') == 'on'
        user.exercise_frequency = data.get('exercise_frequency', user.exercise_frequency)

        # 医疗信息
        user.allergies = data.get('allergies', user.allergies)
        user.medical_history = data.get('medical_history', user.medical_history)
        user.current_medications = data.get('current_medications', user.current_medications)

        # 紧急联系人
        user.emergency_contact_name = data.get('emergency_contact_name', user.emergency_contact_name)
        user.emergency_contact_phone = data.get('emergency_contact_phone', user.emergency_contact_phone)
        user.emergency_contact_relation = data.get('emergency_contact_relation', user.emergency_contact_relation)

        # 健康目标
        user.health_goal = data.get('health_goal', user.health_goal)

        try:
            user.save()
            return JsonResponse({'code': '200', 'errmsg': '修改成功'})
        except Exception as e:
            return JsonResponse({'code': '400', 'errmsg': str(e)})

class IndexView(View):
    def get(self, request):
        """提供首页界面"""
        return render(request, 'index.html')
