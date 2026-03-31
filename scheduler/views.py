import json
from datetime import date, timedelta, datetime
from collections import defaultdict

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .forms import SignUpForm, LoginForm, EmployeeForm, ProfileForm, StyledPasswordChangeForm
from .models import Employee, ScheduleResult
from .services import generate_weekly_schedule, SHIFT_DISPLAY, DAY_NAMES

SHIFT_KO = {'morning': '오전', 'afternoon': '오후', 'night': '야간', 'off': '휴무'}


def landing(request):
    return render(request, 'scheduler/landing.html')


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.first_name = form.cleaned_data.get('first_name', '')
            user.email = form.cleaned_data.get('email', '')
            user.save()
            login(request, user)
            messages.success(request, f'환영합니다, {user.first_name or user.username}님!')
            return redirect('dashboard')
        messages.error(request, '입력 정보를 다시 확인해 주세요.')
    else:
        form = SignUpForm()
    return render(request, 'scheduler/signup.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    next_url = request.GET.get('next', 'dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, '다시 오셨군요!')
            return redirect(next_url)
        messages.error(request, '아이디 또는 비밀번호가 올바르지 않습니다.')
    else:
        form = LoginForm(request)
    return render(request, 'scheduler/login.html', {'form': form})


@login_required
def dashboard(request):
    employees = Employee.objects.filter(user=request.user)
    today = date.today()
    iso_year, iso_week, _ = today.isocalendar()
    current_week_value = f"{iso_year}-W{iso_week:02d}"
    monday = today - timedelta(days=today.weekday())
    week_label = f"{monday.strftime('%Y년 %m월 %d일')} 주"
    return render(request, 'scheduler/dashboard.html', {
        'employees': employees,
        'week_label': week_label,
        'current_week_value': current_week_value,
        'day_names': DAY_NAMES,
        'shift_display': SHIFT_DISPLAY,
    })


@login_required
@require_POST
def generate_schedule(request):
    employees_qs = Employee.objects.filter(user=request.user)
    if not employees_qs.exists():
        return JsonResponse({'success': False, 'error': '직원을 먼저 등록해 주세요.'}, status=400)
    if employees_qs.count() < 5:
        return JsonResponse({'success': False, 'error': '3교대 스케줄링에는 최소 5명의 직원이 필요합니다. (3교대 × 7일 = 21슬롯, 1인 최대 5일 근무)'}, status=400)

    employees = [{'name': e.name, 'off_days': e.off_days} for e in employees_qs]
    schedule_data = generate_weekly_schedule(employees)
    if schedule_data is None:
        return JsonResponse({'success': False, 'error': '스케줄 생성에 실패했습니다. 직원 수나 제약 조건을 확인해 주세요.'}, status=400)

    # 선택한 주 파싱 (예: "2026-W14") → 월요일 날짜 계산
    try:
        body = json.loads(request.body)
        week_str = body.get('week', '')
        monday = datetime.strptime(f"{week_str}-1", "%G-W%V-%u").date()
    except Exception:
        today = date.today()
        monday = today - timedelta(days=today.weekday())
    week_label = f"{monday.strftime('%Y년 %m월 %d일')} 주"
    result_obj = ScheduleResult.objects.create(
        user=request.user, week_label=week_label, schedule_data=schedule_data,
    )
    return JsonResponse({
        'success': True, 'schedule': schedule_data,
        'week_label': week_label, 'result_id': result_obj.pk,
        'day_names': DAY_NAMES, 'shift_display': SHIFT_DISPLAY,
    })


@login_required
def employee_list(request):
    employees = Employee.objects.filter(user=request.user)
    return render(request, 'scheduler/employees.html', {'employees': employees})


@login_required
def employee_create(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            emp = form.save(commit=False)
            emp.user = request.user
            emp.save()
            messages.success(request, f'{emp.name} 직원이 등록되었습니다.')
            return redirect('employee_list')
    else:
        form = EmployeeForm()
    return render(request, 'scheduler/employee_form.html', {'form': form, 'action': '직원 등록'})


@login_required
def employee_edit(request, pk):
    emp = get_object_or_404(Employee, pk=pk, user=request.user)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=emp)
        if form.is_valid():
            form.save()
            messages.success(request, f'{emp.name} 정보가 수정되었습니다.')
            return redirect('employee_list')
    else:
        form = EmployeeForm(instance=emp)
    return render(request, 'scheduler/employee_form.html', {'form': form, 'action': '직원 수정', 'emp': emp})


@login_required
@require_POST
def employee_delete(request, pk):
    emp = get_object_or_404(Employee, pk=pk, user=request.user)
    name = emp.name
    emp.delete()
    messages.success(request, f'{name} 직원이 삭제되었습니다.')
    return redirect('employee_list')


@login_required
def history(request):
    schedules = ScheduleResult.objects.filter(user=request.user)
    # 템플릿에서 동적 키 접근이 안 되므로 미리 list로 변환
    processed = []
    for s in schedules:
        rows = []
        for name, days in s.schedule_data.items():
            shifts = [days.get(str(d), 'off') for d in range(7)]
            rows.append({'name': name, 'shifts': shifts})
        processed.append({'obj': s, 'rows': rows})
    return render(request, 'scheduler/history.html', {
        'processed': processed,
        'day_names': DAY_NAMES,
        'shift_ko': SHIFT_KO,
    })


@login_required
def analytics(request):
    schedules = ScheduleResult.objects.filter(user=request.user)
    employee_count = Employee.objects.filter(user=request.user).count()
    schedule_count = schedules.count()

    # 교대별 누적 집계
    shift_totals = defaultdict(int)
    emp_shift = defaultdict(lambda: defaultdict(int))

    for s in schedules:
        for name, days in s.schedule_data.items():
            for shift in days.values():
                shift_totals[shift] += 1
                emp_shift[name][shift] += 1

    # Chart.js 용 JSON
    emp_names = list(emp_shift.keys())
    chart_data = {
        'labels': emp_names,
        'morning':   [emp_shift[n]['morning']   for n in emp_names],
        'afternoon': [emp_shift[n]['afternoon'] for n in emp_names],
        'night':     [emp_shift[n]['night']     for n in emp_names],
        'off':       [emp_shift[n]['off']       for n in emp_names],
    }

    st = dict(shift_totals)
    shift_total_all = sum(st.values()) or 1  # 0 나눗셈 방지

    return render(request, 'scheduler/analytics.html', {
        'schedule_count': schedule_count,
        'employee_count': employee_count,
        'shift_totals': st,
        'shift_total_all': shift_total_all,
        'chart_data_json': json.dumps(chart_data, ensure_ascii=False),
        'has_data': schedule_count > 0,
    })


@login_required
def settings_view(request):
    profile_form = ProfileForm(instance=request.user)
    password_form = StyledPasswordChangeForm(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'profile':
            profile_form = ProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, '프로필이 저장되었습니다.')
                return redirect('settings')
        elif action == 'password':
            password_form = StyledPasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, password_form.user)
                messages.success(request, '비밀번호가 변경되었습니다.')
                return redirect('settings')

    return render(request, 'scheduler/settings.html', {
        'profile_form': profile_form,
        'password_form': password_form,
    })
