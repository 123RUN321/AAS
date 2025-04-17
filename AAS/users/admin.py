from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from .models import User, Patient, Doctor, AdminProfile


# 自定义批量删除Action
def batch_delete(modeladmin, request, queryset):
    # 执行批量删除
    count = queryset.count()
    queryset.delete()
    # 显示删除成功的消息
    modeladmin.message_user(request, f"成功删除 {count} 条记录")


batch_delete.short_description = "批量删除所选记录"


# 自定义UserAdmin
class CustomUserAdmin(UserAdmin):
    # 添加role字段到管理界面
    fieldsets = UserAdmin.fieldsets + (
        ('自定义字段', {'fields': ('role', 'mobile', 'avatar', 'user_desc', 'gender', 'birth_date')}),
    )
    list_display = ('username', 'email', 'mobile', 'role', 'is_staff', 'actions_column')
    list_filter = ('role', 'is_staff', 'is_superuser')
    search_fields = ('username', 'mobile', 'email')
    actions = [batch_delete]

    def actions_column(self, obj):
        return format_html(
            '<a class="button" href="{}">编辑</a>&nbsp;'
            '<a class="button" href="{}" style="color:red">删除</a>',
            reverse('admin:%s_%s_change' % (obj._meta.app_label, obj._meta.model_name), args=[obj.id]),
            reverse('admin:%s_%s_delete' % (obj._meta.app_label, obj._meta.model_name), args=[obj.id])
        )

    actions_column.short_description = '操作'
    actions_column.allow_tags = True


# Patient模型Admin配置
class PatientAdmin(admin.ModelAdmin):
    list_display = ('patient_id', 'user', 'blood_type', 'assigned_doctor', 'actions_column')
    list_filter = ('blood_type', 'assigned_doctor')
    search_fields = ('patient_id', 'user__mobile', 'user__username')
    raw_id_fields = ('user', 'assigned_doctor')
    actions = [batch_delete]

    def actions_column(self, obj):
        return format_html(
            '<a class="button" href="{}">编辑</a>&nbsp;'
            '<a class="button" href="{}" style="color:red">删除</a>',
            reverse('admin:%s_%s_change' % (obj._meta.app_label, obj._meta.model_name), args=[obj.id]),
            reverse('admin:%s_%s_delete' % (obj._meta.app_label, obj._meta.model_name), args=[obj.id])
        )

    actions_column.short_description = '操作'
    actions_column.allow_tags = True


# Doctor模型Admin配置
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('license_number', 'user', 'title', 'department', 'is_available', 'actions_column')
    list_filter = ('department', 'title', 'is_available')
    search_fields = ('license_number', 'user__mobile', 'user__username')
    raw_id_fields = ('user',)
    actions = [batch_delete]

    def actions_column(self, obj):
        return format_html(
            '<a class="button" href="{}">编辑</a>&nbsp;'
            '<a class="button" href="{}" style="color:red">删除</a>',
            reverse('admin:%s_%s_change' % (obj._meta.app_label, obj._meta.model_name), args=[obj.id]),
            reverse('admin:%s_%s_delete' % (obj._meta.app_label, obj._meta.model_name), args=[obj.id])
        )

    actions_column.short_description = '操作'
    actions_column.allow_tags = True


# AdminProfile模型Admin配置
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'position', 'department', 'access_level', 'actions_column')
    list_filter = ('department', 'access_level')
    search_fields = ('user__mobile', 'user__username', 'position')
    raw_id_fields = ('user',)
    actions = [batch_delete]

    def actions_column(self, obj):
        return format_html(
            '<a class="button" href="{}">编辑</a>&nbsp;'
            '<a class="button" href="{}" style="color:red">删除</a>',
            reverse('admin:%s_%s_change' % (obj._meta.app_label, obj._meta.model_name), args=[obj.id]),
            reverse('admin:%s_%s_delete' % (obj._meta.app_label, obj._meta.model_name), args=[obj.id])
        )

    actions_column.short_description = '操作'
    actions_column.allow_tags = True


# 注册User模型
admin.site.register(User, CustomUserAdmin)
admin.site.register(Patient, PatientAdmin)
admin.site.register(Doctor, DoctorAdmin)
admin.site.register(AdminProfile, AdminProfileAdmin)