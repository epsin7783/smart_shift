"""
SmartShift 스케줄링 엔진
Google OR-Tools CP-SAT Solver를 사용한 제약조건 기반 3교대 자동 배치

제약조건:
  1. 하루에 직원 1명은 반드시 1개의 교대(또는 휴무)만 가진다.
  2. 하루에 각 교대(오전/오후/야간)에 최소 1명 이상 배치.
  3. 연속 야간 근무 2일 초과 불가 (근로기준법 준수).
  4. 야간 근무 다음 날 오전 근무 배치 금지 (인접 교대 보호).
  5. 주당 최대 근무일 5일 (2일 이상 휴무 보장).
  6. 직원의 휴무 요청 요일 반영 (소프트 제약 → 최대한 준수).
"""

from ortools.sat.python import cp_model

# 교대 상수
MORNING = 0
AFTERNOON = 1
NIGHT = 2
OFF = 3

SHIFT_LABELS = {
    MORNING: 'morning',
    AFTERNOON: 'afternoon',
    NIGHT: 'night',
    OFF: 'off',
}

SHIFT_DISPLAY = {
    'morning': '오전',
    'afternoon': '오후',
    'night': '야간',
    'off': '휴무',
}

DAY_NAMES = ['월', '화', '수', '목', '금', '토', '일']


def generate_weekly_schedule(employees: list[dict]) -> dict | None:
    """
    주어진 직원 목록으로 1주일 3교대 스케줄을 생성한다.

    Args:
        employees: [{"name": "김철수", "off_days": [0, 3]}, ...]
                   off_days: 0=월 ~ 6=일

    Returns:
        {"김철수": {"0": "morning", "1": "off", ...}, ...}
        해를 못 찾으면 None 반환
    """
    num_employees = len(employees)
    num_days = 7
    num_shifts = 4  # morning, afternoon, night, off

    model = cp_model.CpModel()

    # ── 변수 정의 ──────────────────────────────────────────────
    # shift_vars[e][d][s] = 1 이면 직원 e가 d일에 s 교대를 한다
    shift_vars = {}
    for e in range(num_employees):
        shift_vars[e] = {}
        for d in range(num_days):
            shift_vars[e][d] = {}
            for s in range(num_shifts):
                shift_vars[e][d][s] = model.new_bool_var(
                    f'shift_e{e}_d{d}_s{s}'
                )

    # ── 하드 제약조건 ──────────────────────────────────────────

    # [C1] 각 직원은 하루에 정확히 1개 교대(또는 휴무)
    for e in range(num_employees):
        for d in range(num_days):
            model.add_exactly_one(shift_vars[e][d][s] for s in range(num_shifts))

    # [C2] 각 교대(오전/오후/야간)에 하루 최소 1명 배치
    for d in range(num_days):
        for s in [MORNING, AFTERNOON, NIGHT]:
            model.add(
                sum(shift_vars[e][d][s] for e in range(num_employees)) >= 1
            )

    # [C3] 연속 야간 근무 최대 2일
    for e in range(num_employees):
        for d in range(num_days - 2):
            model.add(
                shift_vars[e][d][NIGHT]
                + shift_vars[e][d + 1][NIGHT]
                + shift_vars[e][d + 2][NIGHT]
                <= 2
            )

    # [C4] 야간 근무 다음 날 오전 근무 불가 (인접 교대 보호)
    for e in range(num_employees):
        for d in range(num_days - 1):
            model.add(
                shift_vars[e][d][NIGHT] + shift_vars[e][d + 1][MORNING] <= 1
            )

    # [C5] 주당 최대 근무 5일 (휴무 최소 2일)
    for e in range(num_employees):
        model.add(
            sum(shift_vars[e][d][OFF] for d in range(num_days)) >= 2
        )

    # ── 소프트 제약: 휴무 요청 반영 (패널티 최소화) ───────────
    penalty_terms = []
    for e_idx, emp in enumerate(employees):
        for off_day in emp.get('off_days', []):
            if 0 <= off_day < num_days:
                working_on_req = model.new_bool_var(f'work_req_e{e_idx}_d{off_day}')
                model.add(working_on_req + shift_vars[e_idx][off_day][OFF] == 1)
                penalty_terms.append(working_on_req)

    if penalty_terms:
        model.minimize(sum(penalty_terms))

    # ── 솔버 실행 ──────────────────────────────────────────────
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    status = solver.solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    # ── 결과 파싱 ──────────────────────────────────────────────
    result = {}
    for e_idx, emp in enumerate(employees):
        result[emp['name']] = {}
        for d in range(num_days):
            for s in range(num_shifts):
                if solver.value(shift_vars[e_idx][d][s]) == 1:
                    result[emp['name']][str(d)] = SHIFT_LABELS[s]
                    break

    return result


def get_default_employees() -> list[dict]:
    """데모용 기본 직원 5명 반환"""
    return [
        {'name': '김민준', 'off_days': [5, 6]},  # 토·일 휴무 요청
        {'name': '이서연', 'off_days': [0, 1]},  # 월·화 휴무 요청
        {'name': '박도윤', 'off_days': [2, 3]},  # 수·목 휴무 요청
        {'name': '최하은', 'off_days': [4, 5]},  # 금·토 휴무 요청
        {'name': '정시우', 'off_days': [6, 0]},  # 일·월 휴무 요청
    ]
