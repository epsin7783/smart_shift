from django.db import models
from django.contrib.auth.models import User


class Employee(models.Model):
    """직원 정보 모델"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='employees')
    name = models.CharField(max_length=50, verbose_name='이름')
    off_days = models.JSONField(default=list, verbose_name='휴무 요청 요일')
    # off_days 예: [0, 3]  → 월요일, 목요일 휴무

    class Meta:
        verbose_name = '직원'
        verbose_name_plural = '직원 목록'

    def __str__(self):
        return self.name


class ScheduleResult(models.Model):
    """생성된 스케줄 저장 모델"""
    SHIFT_CHOICES = [
        ('morning', '오전 (07:00-15:00)'),
        ('afternoon', '오후 (15:00-23:00)'),
        ('night', '야간 (23:00-07:00)'),
        ('off', '휴무'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='schedules')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    week_label = models.CharField(max_length=50, verbose_name='주차 라벨')
    schedule_data = models.JSONField(verbose_name='스케줄 데이터 (JSON)')
    # schedule_data 구조:
    # {
    #   "직원이름": {"0": "morning", "1": "off", "2": "afternoon", ...}
    # }

    class Meta:
        verbose_name = '스케줄 결과'
        verbose_name_plural = '스케줄 결과 목록'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.week_label} ({self.created_at:%Y-%m-%d %H:%M})"
