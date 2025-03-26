from django import forms
from django.forms import ChoiceField

from student_management_app.models import Courses, SessionYearModel, Subjects, Students, CourseSession, CustomUser

class ChoiceNoValidation(ChoiceField):
    def validate(self, value):
        pass

class DateInput(forms.DateInput):
    input_type = "date"

class AddStudentForm(forms.Form):
    email = forms.EmailField(label="Email", max_length=50, widget=forms.EmailInput(attrs={"class":"form-control", "autocomplete":"off", "required": True}))
    first_name = forms.CharField(label="First Name", max_length=50, widget=forms.TextInput(attrs={"class":"form-control", "required": True}))
    last_name = forms.CharField(label="Last Name", max_length=50, widget=forms.TextInput(attrs={"class":"form-control", "required": True}))
    address = forms.CharField(label="Address", max_length=50, widget=forms.TextInput(attrs={"class":"form-control", "required": True}))
    registration_number = forms.CharField(label="Registration Number", max_length=50, required=False, widget=forms.TextInput(attrs={"class":"form-control", "autocomplete":"off"}))
    parents_email = forms.EmailField(label="Parents Email", max_length=50, required=False, widget=forms.EmailInput(attrs={"class":"form-control", "autocomplete":"off"}))
    profile_pic = forms.FileField(label="Profile Picture", required=False, widget=forms.FileInput(attrs={"class":"form-control"}))
    gender = forms.ChoiceField(label="Gender", choices=[("Male","Male"),("Female","Female")], widget=forms.Select(attrs={"class":"form-control", "required": True}))
    course = forms.ModelChoiceField(label="Course", queryset=Courses.objects.all(), empty_label="Select Course", widget=forms.Select(attrs={"class":"form-control", "required": True}))
    session_year_id = forms.ModelChoiceField(label="Session Year", queryset=SessionYearModel.objects.all(), empty_label="Select Session Year", widget=forms.Select(attrs={"class":"form-control", "required": True}))

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists")
        return email
    
    def clean_registration_number(self):
        registration_number = self.cleaned_data.get('registration_number')
        if registration_number and Students.objects.filter(registration_number=registration_number).exists():
            raise forms.ValidationError("Registration number already exists")
        return registration_number

    def clean(self):
        cleaned_data = super().clean()
        course = cleaned_data.get('course')
        session_year_id = cleaned_data.get('session_year_id')

        if not course:
            self.add_error('course', 'Please select a course')
        
        if not session_year_id:
            self.add_error('session_year_id', 'Please select a session year')

        return cleaned_data

class EditStudentForm(forms.Form):
    email = forms.EmailField(label="Email", max_length=50, widget=forms.EmailInput(attrs={"class":"form-control"}))
    first_name = forms.CharField(label="First Name", max_length=50, widget=forms.TextInput(attrs={"class":"form-control"}))
    last_name = forms.CharField(label="Last Name", max_length=50, widget=forms.TextInput(attrs={"class":"form-control"}))
    username = forms.CharField(label="Username", max_length=50, widget=forms.TextInput(attrs={"class":"form-control"}))
    address = forms.CharField(label="Address", max_length=50, widget=forms.TextInput(attrs={"class":"form-control"}))
    registration_number = forms.CharField(label="Registration Number", max_length=50, widget=forms.TextInput(attrs={"class":"form-control"}))
    parents_email = forms.EmailField(label="Parents Email", max_length=50, widget=forms.EmailInput(attrs={"class":"form-control"}))

    # For Displaying Courses
    try:
        courses = Courses.objects.all()
        course_list = []
        for course in courses:
            single_course = (course.id, course.course_name)
            course_list.append(single_course)
    except:
        course_list = []

    # For Displaying Session Years
    try:
        sessions = SessionYearModel.objects.all()
        session_list = []
        for ses in sessions:
            single_session = (ses.id, str(ses.start_year)+" TO "+str(ses.end_year))
            session_list.append(single_session)
    except:
        session_list = []

    gender_choices = [
        ('Male', 'Male'),
        ('Female', 'Female')
    ]

    course = forms.ChoiceField(label="Course", choices=course_list, widget=forms.Select(attrs={"class":"form-control"}))
    gender = forms.ChoiceField(label="Gender", choices=gender_choices, widget=forms.Select(attrs={"class":"form-control"}))
    session_year_id = forms.ChoiceField(label="Session Year", choices=session_list, widget=forms.Select(attrs={"class":"form-control"}))

class EditResultForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.staff_id=kwargs.pop("staff_id")
        super(EditResultForm,self).__init__(*args,**kwargs)
        subject_list=[]
        try:
            subjects=Subjects.objects.filter(staff_id=self.staff_id)
            for subject in subjects:
                subject_single=(subject.id,subject.subject_name)
                subject_list.append(subject_single)
        except:
            subject_list=[]
        self.fields['subject_id'].choices=subject_list

    session_list=[]
    try:
        sessions=SessionYearModel.objects.all()
        for session in sessions:
            session_single=(session.id,str(session.start_year)+" TO "+str(session.end_year))
            session_list.append(session_single)
    except:
        session_list=[]

    subject_id=forms.ChoiceField(label="Subject",widget=forms.Select(attrs={"class":"form-control"}))
    session_ids=forms.ChoiceField(label="Session Year",choices=session_list,widget=forms.Select(attrs={"class":"form-control"}))
    student_ids=ChoiceNoValidation(label="Student",widget=forms.Select(attrs={"class":"form-control"}))
    assignment_marks=forms.CharField(label="Assignment Marks",widget=forms.TextInput(attrs={"class":"form-control"}))
    exam_marks=forms.CharField(label="Exam Marks",widget=forms.TextInput(attrs={"class":"form-control"}))

class AddStaffForm(forms.Form):
    email = forms.EmailField(label="Email", max_length=50, widget=forms.EmailInput(attrs={"class":"form-control"}))
    first_name = forms.CharField(label="First Name", max_length=50, widget=forms.TextInput(attrs={"class":"form-control"}))
    last_name = forms.CharField(label="Last Name", max_length=50, widget=forms.TextInput(attrs={"class":"form-control"}))
    address = forms.CharField(label="Address", max_length=50, widget=forms.TextInput(attrs={"class":"form-control"}))
    employee_id = forms.CharField(label="Employee ID", max_length=50, widget=forms.TextInput(attrs={"class":"form-control"}))
    gender = forms.ChoiceField(label="Gender", choices=[("","Select Gender"),("Male","Male"),("Female","Female")], widget=forms.Select(attrs={"class":"form-control"}))

class BulkUploadStudentForm(forms.Form):
    file = forms.FileField(label="Upload File", widget=forms.FileInput(attrs={
        "class": "form-control", 
        "accept": ".xlsx,.xls",
        "title": "Upload Excel file"
    }))
    session_year_id = forms.ChoiceField(label="Session Year", choices=[], widget=forms.Select(attrs={
        "class": "form-control",
        "title": "Select Session Year"
    }))
    course = forms.ChoiceField(label="Course", choices=[], widget=forms.Select(attrs={
        "class": "form-control",
        "title": "Select Course"
    }))

    def __init__(self, *args, **kwargs):
        super(BulkUploadStudentForm, self).__init__(*args, **kwargs)
        try:
            self.fields['session_year_id'].choices = [("", "Select Session Year")] + [(session.id, str(session.start_year)+" TO "+str(session.end_year)) 
                                                    for session in SessionYearModel.objects.all()]
            self.fields['course'].choices = [("", "Select Course")] + [(course.id, course.course_name) 
                                           for course in Courses.objects.all()]
        except:
            self.fields['session_year_id'].choices = [("", "Select Session Year")]
            self.fields['course'].choices = [("", "Select Course")]

class BulkUploadStaffForm(forms.Form):
    file = forms.FileField(label="Upload File", widget=forms.FileInput(attrs={
        "class": "form-control", 
        "accept": ".xlsx,.xls",
        "title": "Upload Excel file"
    }))

