# apps/accounts/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import User, UserPreference


class UserLoginForm(AuthenticationForm):
    """Custom login form with remember me functionality"""

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )
    remember = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Remember me'
    )

    class Meta:
        model = User
        fields = ['username', 'password', 'remember']

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            self.user_cache = authenticate(
                self.request, username=username, password=password
            )
            if self.user_cache is None:
                raise forms.ValidationError(
                    'Invalid username or password.',
                    code='invalid_login'
                )
            elif not self.user_cache.is_active:
                raise forms.ValidationError(
                    'This account is inactive.',
                    code='inactive'
                )
            elif self.user_cache.is_locked:
                raise forms.ValidationError(
                    'This account is locked due to too many failed login attempts. Please contact administrator.',
                    code='locked'
                )

        return self.cleaned_data


class UserCreationForm(forms.ModelForm):
    """Form for creating new users"""

    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Password must be at least 8 characters long.'
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Enter the same password as above.'
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'role', 'department', 'phone', 'job_title'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'job_title': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match.")

        if len(password1) < 8:
            raise ValidationError("Password must be at least 8 characters long.")

        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])

        if commit:
            user.save()

        return user


class UserUpdateForm(forms.ModelForm):
    """Form for updating user information"""

    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'phone',
            'department', 'job_title', 'role', 'is_active'
        ]
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'job_title': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('This email is already in use.')
        return email


class UserProfileForm(forms.ModelForm):
    """Form for user profile update"""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'department', 'job_title']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'job_title': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('This email is already in use.')
        return email


class ChangePasswordForm(PasswordChangeForm):
    """Custom password change form"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update({'class': 'form-control'})
        self.fields['new_password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['new_password2'].widget.attrs.update({'class': 'form-control'})


class UserPreferencesForm(forms.ModelForm):
    """Form for user preferences"""

    class Meta:
        model = UserPreference
        fields = [
            'items_per_page', 'date_format', 'timezone',
            'theme', 'email_notifications', 'email_digest_frequency'
        ]
        widgets = {
            'items_per_page': forms.Select(attrs={'class': 'form-select'}),
            'date_format': forms.Select(attrs={'class': 'form-select'}),
            'timezone': forms.Select(attrs={'class': 'form-select'}),
            'theme': forms.Select(attrs={'class': 'form-select'}),
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_digest_frequency': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set timezone choices
        import pytz
        timezones = [(tz, tz) for tz in pytz.common_timezones]
        self.fields['timezone'].choices = timezones


class NotificationSettingsForm(forms.ModelForm):
    """Form for notification settings"""

    class Meta:
        model = User
        fields = ['notification_preferences']
        widgets = {
            'notification_preferences': forms.HiddenInput()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add dynamic notification preference fields
        notification_types = [
            'approval_needed', 'approval_completed', 'revision_needed',
            'delegated', 'completed', 'reminder', 'system_alert'
        ]

        preferences = self.instance.notification_preferences or {}

        for nt in notification_types:
            self.fields[f'notify_{nt}'] = forms.BooleanField(
                label=nt.replace('_', ' ').title(),
                required=False,
                initial=preferences.get(nt, True),
                widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
            )

    def save(self, commit=True):
        preferences = {}

        for field_name, value in self.cleaned_data.items():
            if field_name.startswith('notify_'):
                notification_type = field_name.replace('notify_', '')
                preferences[notification_type] = value

        self.instance.notification_preferences = preferences

        if commit:
            self.instance.save()

        return self.instance


class RoleForm(forms.ModelForm):
    """Form for role management"""

    class Meta:
        from .models import Role
        model = Role
        fields = ['name', 'display_name', 'description', 'permissions', 'hierarchy_level']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'display_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'permissions': forms.SelectMultiple(attrs={'class': 'form-select select2'}),
            'hierarchy_level': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class DepartmentForm(forms.ModelForm):
    """Form for department management"""

    class Meta:
        from .models import Department
        model = Department
        fields = ['name', 'code', 'description', 'head', 'parent', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'head': forms.Select(attrs={'class': 'form-select select2'}),
            'parent': forms.Select(attrs={'class': 'form-select select2'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['head'].queryset = User.objects.filter(is_active=True)
        self.fields['head'].empty_label = 'Select department head'
        self.fields['parent'].empty_label = 'No parent department'


class UserSearchForm(forms.Form):
    """Form for searching users"""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by username, name or email...'
        })
    )
    role = forms.ChoiceField(
        required=False,
        choices=[('', 'All Roles')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    department = forms.ChoiceField(
        required=False,
        choices=[('', 'All Departments')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Status'),
            ('active', 'Active'),
            ('inactive', 'Inactive'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set role choices
        self.fields['role'].choices = [('', 'All Roles')] + list(User.ROLE_CHOICES)

        # Set department choices
        self.fields['department'].choices = [('', 'All Departments')] + list(User.DEPARTMENT_CHOICES)