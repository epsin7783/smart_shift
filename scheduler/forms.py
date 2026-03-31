from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Employee


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': '업무용 이메일'})
    )
    first_name = forms.CharField(
        max_length=30, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '담당자 이름'})
    )
    company = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '회사명 (선택)'})
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': '아이디'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': '비밀번호 (8자 이상)'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': '비밀번호 확인'})


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': '아이디'})
        self.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': '비밀번호'})


class EmployeeForm(forms.ModelForm):
    DAY_CHOICES = [
        ('0', '월'), ('1', '화'), ('2', '수'),
        ('3', '목'), ('4', '금'), ('5', '토'), ('6', '일'),
    ]
    off_days = forms.MultipleChoiceField(
        choices=DAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='휴무 요청 요일',
    )

    class Meta:
        model = Employee
        fields = ('name', 'off_days')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '직원 이름 (예: 김민준)'})
        }
        labels = {'name': '직원 이름'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 수정 시 기존 off_days(int 리스트)를 문자열 리스트로 변환해 초기값 세팅
        if self.instance.pk and self.instance.off_days:
            self.initial['off_days'] = [str(d) for d in self.instance.off_days]

    def clean_off_days(self):
        return [int(d) for d in self.cleaned_data.get('off_days', [])]


from django.contrib.auth.forms import PasswordChangeForm as DjPasswordChangeForm

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'email')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '이름'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': '이메일'}),
        }
        labels = {'first_name': '이름', 'email': '이메일'}


class StyledPasswordChangeForm(DjPasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({'class': 'form-control'})
