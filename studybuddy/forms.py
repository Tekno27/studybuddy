from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import (
    Course,
    Notification,
    Programme,
    Report,
    StudentProfile,
    StudyGroup,
    StudySession,
    University,
)


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'placeholder': 'e.g. Ama'}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'placeholder': 'e.g. Mensah'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'e.g. student@university.edu.gh'}))
    university = forms.ModelChoiceField(queryset=University.objects.all(), empty_label='Select your university')
    programme = forms.ModelChoiceField(queryset=Programme.objects.select_related('university'), empty_label='Select your programme')
    level = forms.IntegerField(min_value=1, max_value=999, widget=forms.NumberInput(attrs={'placeholder': 'e.g. 300'}))

    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        university = cleaned_data.get('university')
        programme = cleaned_data.get('programme')
        if university and programme and programme.university_id != university.id:
            self.add_error('programme', 'Choose a programme from the selected university.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            self.save_profile(user)
        return user

    def save_profile(self, user):
        return StudentProfile.objects.create(
            user=user,
            university=self.cleaned_data['university'],
            programme=self.cleaned_data['programme'],
            level=self.cleaned_data['level'],
            study_preference=StudentProfile.StudyPreference.BOTH,
        )


class ProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ['university', 'programme', 'level', 'courses', 'study_preference', 'availability', 'bio']
        widgets = {
            'courses': forms.CheckboxSelectMultiple,
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Tell potential study partners about your goals, study habits, and topics you are focusing on...'}),
            'availability': forms.TextInput(attrs={'placeholder': 'e.g. Weekday evenings, weekends in the library'}),
            'level': forms.NumberInput(attrs={'placeholder': 'e.g. 300'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['programme'].queryset = Programme.objects.select_related('university')
        self.fields['courses'].queryset = Course.objects.select_related('programme')

    def clean(self):
        cleaned_data = super().clean()
        university = cleaned_data.get('university')
        programme = cleaned_data.get('programme')
        courses = cleaned_data.get('courses')
        if university and programme and programme.university_id != university.id:
            self.add_error('programme', 'Choose a programme from the selected university.')
        if programme and courses and any(course.programme_id != programme.id for course in courses):
            self.add_error('courses', 'Choose courses from the selected programme.')
        return cleaned_data


class PartnerFilterForm(forms.Form):
    query = forms.CharField(
        required=False,
        label='Search',
        widget=forms.TextInput(attrs={'placeholder': 'Search by student name or course (e.g. Kwame, CSC301)...'}),
    )
    university = forms.ModelChoiceField(queryset=University.objects.all(), required=False, empty_label='All universities')
    programme = forms.ModelChoiceField(queryset=Programme.objects.select_related('university'), required=False, empty_label='All programmes')
    level = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=999,
        widget=forms.NumberInput(attrs={'placeholder': 'Level (e.g. 300)'}),
    )
    course = forms.ModelChoiceField(queryset=Course.objects.select_related('programme'), required=False, empty_label='All courses')
    study_preference = forms.ChoiceField(choices=[('', 'Any study style')] + list(StudentProfile.StudyPreference.choices), required=False)


class StudyRequestForm(forms.Form):
    message = forms.CharField(
        max_length=500,
        required=False,
        initial="I'd like to study together.",
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': "Add a friendly message..."}),
    )


class StudyGroupForm(forms.ModelForm):
    class Meta:
        model = StudyGroup
        fields = ['name', 'course', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g. CSC301 Midterm Study Circle'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'What is this study group about? When do you plan to meet? What are the goals?'}),
        }

    def __init__(self, *args, **kwargs):
        programme = kwargs.pop('programme', None)
        super().__init__(*args, **kwargs)
        if programme:
            self.fields['course'].queryset = Course.objects.filter(programme=programme)
        else:
            self.fields['course'].queryset = Course.objects.select_related('programme')
        self.fields['course'].empty_label = 'Select a course'


class StudySessionForm(forms.ModelForm):
    class Meta:
        model = StudySession
        fields = ['title', 'date', 'time', 'location', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Chapter 4 & 5 Problem Solving Session'}),
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
            'location': forms.TextInput(attrs={'placeholder': 'e.g. Balme Library Study Room 3 or https://meet.google.com/xyz'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Notes or topics to cover during this study session...'}),
        }


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['reason', 'details']
        widgets = {
            'reason': forms.TextInput(attrs={'placeholder': 'e.g. Inappropriate behavior, spam, harassment'}),
            'details': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Please provide details about what occurred so campus moderators can review...'}),
        }