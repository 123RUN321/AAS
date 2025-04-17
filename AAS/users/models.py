from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator


class User(AbstractUser):
    ROLE_CHOICES = (
        ('patient', '病人'),
        ('doctor', '医生'),
        ('admin', '管理员'),
    )

    # 基础字段
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='patient', verbose_name='角色')
    mobile = models.CharField(max_length=20, unique=True, blank=False, verbose_name='手机号')
    avatar = models.ImageField(upload_to='avatar/%Y%m%d/', blank=True, verbose_name='头像')
    user_desc = models.TextField(max_length=500, blank=True, verbose_name='个人描述')

    GENDER_CHOICES = (
        ('M', '男性'),
        ('F', '女性'),
        ('O', '其他'),
    )
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True, verbose_name='性别')
    birth_date = models.DateField(null=True, blank=True, verbose_name='出生日期')
    # 添加姓名字段
    first_name = models.CharField(max_length=30, blank=True, verbose_name='名')
    last_name = models.CharField(max_length=30, blank=True, verbose_name='姓')

    USERNAME_FIELD = 'mobile'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'tb_user'
        verbose_name = '系统用户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.get_role_display()}-{self.mobile}"

    @property
    def age(self):
        if self.birth_date:
            import datetime
            today = datetime.date.today()
            return today.year - self.birth_date.year - (
                    (today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        return None


class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile',
                                limit_choices_to={'role': 'patient'}, null=True, blank=True)

    # 身体指标
    height = models.FloatField(verbose_name='身高(cm)', validators=[MinValueValidator(50), MaxValueValidator(250)],
                               null=True, blank=True)
    weight = models.FloatField(verbose_name='体重(kg)', validators=[MinValueValidator(20), MaxValueValidator(200)],
                               null=True, blank=True)

    # 健康指标
    blood_type = models.CharField(max_length=3, verbose_name='血型',
                                  choices=(('A', 'A型'), ('B', 'B型'), ('AB', 'AB型'), ('O', 'O型')), null=True,
                                  blank=True)
    blood_pressure_high = models.IntegerField(verbose_name='血压(高压)', null=True, blank=True)
    blood_pressure_low = models.IntegerField(verbose_name='血压(低压)', null=True, blank=True)
    blood_sugar = models.FloatField(verbose_name='血糖(mmol/L)', null=True, blank=True)
    cholesterol = models.FloatField(verbose_name='胆固醇(mmol/L)', null=True, blank=True)

    # 健康习惯
    is_smoker = models.BooleanField(default=False, verbose_name='是否吸烟', null=True, blank=True)
    is_drinker = models.BooleanField(default=False, verbose_name='是否饮酒', null=True, blank=True)
    exercise_frequency = models.CharField(max_length=20, verbose_name='锻炼频率',
                                          choices=(
                                              ('never', '从不'),
                                              ('rarely', '很少'),
                                              ('sometimes', '有时'),
                                              ('often', '经常'),
                                              ('daily', '每天')
                                          ), null=True, blank=True)

    # 医疗信息
    allergies = models.TextField(verbose_name='过敏史', null=True, blank=True)
    medical_history = models.TextField(verbose_name='病史', null=True, blank=True)
    current_medications = models.TextField(verbose_name='当前用药', null=True, blank=True)

    # 紧急联系人
    emergency_contact_name = models.CharField(max_length=50, verbose_name='紧急联系人姓名', null=True, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, verbose_name='紧急联系人电话', null=True, blank=True)
    emergency_contact_relation = models.CharField(max_length=20, verbose_name='与紧急联系人关系', null=True, blank=True)

    # 系统相关
    patient_id = models.CharField(max_length=50, unique=True, verbose_name='病历号', null=True, blank=True)
    health_goal = models.TextField(verbose_name='健康目标', null=True, blank=True)
    assigned_doctor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                        related_name='assigned_patients', limit_choices_to={'role': 'doctor'},
                                        verbose_name='主治医生')

    class Meta:
        verbose_name = '病人信息'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user.mobile if self.user else '无用户关联'}的病人档案"

    @property
    def bmi(self):
        if self.height and self.weight:
            return round(self.weight / ((self.height / 100) ** 2), 2)
        return None


class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile',
                                limit_choices_to={'role': 'doctor'}, null=True, blank=True)

    # 专业信息
    title = models.CharField(max_length=50, verbose_name='职称', null=True, blank=True)
    department = models.CharField(max_length=100, verbose_name='科室', null=True, blank=True)
    specialty = models.TextField(verbose_name='专业特长', null=True, blank=True)
    license_number = models.CharField(max_length=50, unique=True, verbose_name='执业证书编号', null=True, blank=True)

    # 教育背景
    education = models.CharField(max_length=100, verbose_name='学历', null=True, blank=True)
    graduation_school = models.CharField(max_length=100, verbose_name='毕业院校', null=True, blank=True)

    # 工作信息
    work_experience = models.TextField(verbose_name='工作经历', null=True, blank=True)
    is_available = models.BooleanField(default=True, verbose_name='是否可接诊', null=True, blank=True)
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='咨询费', null=True, blank=True)

    # 工作时间
    work_schedule = models.JSONField(default=dict, verbose_name='工作时间表', null=True, blank=True)

    class Meta:
        verbose_name = '医生信息'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user.mobile if self.user else '无用户关联'}的医生档案"

    @property
    def patient_count(self):
        if self.assigned_patients:
            return self.assigned_patients.count()
        return 0


class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile',
                                limit_choices_to={'role': 'admin'})

    # 管理员特有字段
    position = models.CharField(max_length=50, verbose_name='职位')
    department = models.CharField(max_length=100, verbose_name='管理部门')
    access_level = models.CharField(max_length=20, verbose_name='访问级别',
                                    choices=(
                                        ('basic', '基础'),
                                        ('advanced', '高级'),
                                        ('super', '超级管理员')
                                    ))
    last_audit = models.DateTimeField(auto_now=True, verbose_name='最后审计时间')

    class Meta:
        verbose_name = '管理员信息'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user.mobile}的管理员档案"


