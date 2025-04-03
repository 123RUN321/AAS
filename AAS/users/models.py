from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator


class User(AbstractUser):
    # 基础信息 (保留原有字段)
    mobile = models.CharField(max_length=20, unique=True, blank=False)
    avatar = models.ImageField(upload_to='avatar/%Y%m%d/', blank=True)
    user_desc = models.TextField(max_length=500, blank=True)

    # 健康系统新增字段
    GENDER_CHOICES = (
        ('M', '男性'),
        ('F', '女性'),
        ('O', '其他'),
    )

    # 基本信息
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, verbose_name='性别')
    birth_date = models.DateField(null=True, blank=True, verbose_name='出生日期')
    height = models.FloatField(null=True, blank=True, verbose_name='身高(cm)',
                               validators=[MinValueValidator(50), MaxValueValidator(250)])
    weight = models.FloatField(null=True, blank=True, verbose_name='体重(kg)',
                               validators=[MinValueValidator(20), MaxValueValidator(200)])

    # 健康指标
    blood_type = models.CharField(max_length=3, blank=True, verbose_name='血型',
                                  choices=(('A', 'A型'), ('B', 'B型'), ('AB', 'AB型'), ('O', 'O型')))
    blood_pressure_high = models.IntegerField(null=True, blank=True, verbose_name='血压(高压)')
    blood_pressure_low = models.IntegerField(null=True, blank=True, verbose_name='血压(低压)')
    blood_sugar = models.FloatField(null=True, blank=True, verbose_name='血糖(mmol/L)')
    cholesterol = models.FloatField(null=True, blank=True, verbose_name='胆固醇(mmol/L)')

    # 健康习惯
    is_smoker = models.BooleanField(default=False, verbose_name='是否吸烟')
    is_drinker = models.BooleanField(default=False, verbose_name='是否饮酒')
    exercise_frequency = models.CharField(max_length=20, blank=True, verbose_name='锻炼频率',
                                          choices=(
                                              ('never', '从不'),
                                              ('rarely', '很少'),
                                              ('sometimes', '有时'),
                                              ('often', '经常'),
                                              ('daily', '每天')
                                          ))

    # 医疗信息
    allergies = models.TextField(blank=True, verbose_name='过敏史')
    medical_history = models.TextField(blank=True, verbose_name='病史')
    current_medications = models.TextField(blank=True, verbose_name='当前用药')

    # 紧急联系人
    emergency_contact_name = models.CharField(max_length=50, blank=True, verbose_name='紧急联系人姓名')
    emergency_contact_phone = models.CharField(max_length=20, blank=True, verbose_name='紧急联系人电话')
    emergency_contact_relation = models.CharField(max_length=20, blank=True, verbose_name='与紧急联系人关系')

    # 健康系统特定设置
    health_goal = models.TextField(blank=True, verbose_name='健康目标')
    doctor = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL,
                               verbose_name='主治医生', related_name='patients')

    USERNAME_FIELD = 'mobile'
    REQUIRED_FIELDS = ['username', 'email']

    class Meta:
        db_table = 'tb_user'
        verbose_name = '健康系统用户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.mobile

    # 计算BMI的方法
    @property
    def bmi(self):
        if self.height and self.weight:
            return round(self.weight / ((self.height / 100) ** 2), 2)
        return None

    # 年龄计算方法
    @property
    def age(self):
        if self.birth_date:
            import datetime
            today = datetime.date.today()
            return today.year - self.birth_date.year - (
                    (today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        return None