from django.contrib import admin
from .models import Employee, ScheduleResult


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'off_days')


@admin.register(ScheduleResult)
class ScheduleResultAdmin(admin.ModelAdmin):
    list_display = ('week_label', 'user', 'created_at')
    readonly_fields = ('created_at',)
