# Standard library imports
import json
import pandas as pd
import os
import shutil
import csv
import requests
from datetime import datetime, date
import threading
import time
import xlwt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
import datetime
import random
import logging
from django.utils.crypto import get_random_string
import pytz
import tempfile
from django.core.files.uploadedfile import UploadedFile
import traceback

# Django imports
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, FileResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db import transaction
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.db import IntegrityError
from django.core.mail import EmailMultiAlternatives
import mimetypes
import io
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required

# Local imports
from student_management_app.forms import AddStudentForm, EditStudentForm, AddStaffForm, BulkUploadStudentForm
from student_management_app.models import (
    CustomUser, Staffs, Courses, Subjects, Students, SessionYearModel,
    FeedBackStudent, FeedBackStaffs, Attendance, AttendanceReport, 
    NotificationStudent, NotificationStaffs, Class, StudentClass, CourseSession, 
    ClassSubject, DeletedCourseID, DeletedSubjectID, DeletedStaffID, 
    DeletedStudentID, DeletedClassID, SystemSettings, AttendanceEditRequest, UserActivity,
    ErrorLog
)
from student_management_app.email_utils import send_activation_email
from .export_utils import export_to_excel, export_to_pdf

def generate_random_password(length=8):
    """Generate a random password of specified length with letters, digits and special characters"""
    import random
    import string
    
    # Define character sets
    letters = string.ascii_letters
    digits = string.digits
    special_chars = '!@#$%^&*()-_=+'
    
    # Create password with at least one of each type
    password = [
        random.choice(letters),
        random.choice(digits),
        random.choice(special_chars)
    ]
    
    # Fill the rest with random characters from all sets
    all_chars = letters + digits + special_chars
    password.extend(random.choice(all_chars) for _ in range(length - 3))
    
    # Shuffle the password characters
    random.shuffle(password)
    
    # Convert list to string
    return ''.join(password)

def generate_username_from_email(email):
    """Generate a username from an email address"""
    username = email.split('@')[0]
    
    # Check if username already exists
    if CustomUser.objects.filter(username=username).exists():
        # Add random numbers until a unique username is found
        while True:
            random_suffix = str(random.randint(1, 9999))
            new_username = f"{username}{random_suffix}"
            if not CustomUser.objects.filter(username=new_username).exists():
                return new_username
    
    return username

def send_delayed_activation_email(user, activation_token, delay_minutes=5):
    """Send activation email after specified delay in minutes"""
    def delayed_send():
        # Sleep for the specified time
        time.sleep(delay_minutes * 60)
        # Send the email
        send_activation_email(user, activation_token)
        print(f"Activation email sent to {user.email} after {delay_minutes} minutes delay")
    
    # Start the email sending in a separate thread
    thread = threading.Thread(target=delayed_send)
    thread.daemon = True
    thread.start()
    
    return True

def admin_home(request):
    """
    View function for the admin home page.
    Initializes system settings and displays dashboard statistics.
    """
    # Initialize system settings if they don't exist
    default_settings = {
        'enable_admin_signup': 'False',
        'enable_staff_signup': 'False',
        'enable_student_signup': 'False'
    }
    
    # Create default settings if they don't exist
    for key, value in default_settings.items():
        SystemSettings.objects.get_or_create(
            setting_key=key,
            defaults={
                'setting_value': value,
                'description': f"Enable {key.replace('enable_', '').replace('_', ' ')} feature"
            }
        )
    
    # Ensure all signup options are turned off by default
    for key in default_settings.keys():
        setting = SystemSettings.objects.get(setting_key=key)
        if setting.setting_value != 'False':
            setting.setting_value = 'False'
            setting.save()
    
    # Get basic counts
    student_count1 = Students.objects.all().count()
    staff_count = Staffs.objects.all().count()
    subject_count = Subjects.objects.all().count()
    course_count = Courses.objects.all().count()

    # Get course statistics
    course_all = Courses.objects.all()
    course_name_list = []
    subject_count_list = []
    student_count_list_in_course = []
    
    for course in course_all:
        course_sessions = CourseSession.objects.filter(course=course)
        subjects = Subjects.objects.filter(course_session__in=course_sessions).count()
        classes = Class.objects.filter(course_session__in=course_sessions)
        student_count = StudentClass.objects.filter(class_id__in=classes).count()
        
        course_name_list.append(course.course_name)
        subject_count_list.append(subjects)
        student_count_list_in_course.append(student_count)

    # Get subject statistics
    subjects_all = Subjects.objects.all()
    subject_list = []
    student_count_list_in_subject = []
    
    for subject in subjects_all:
        class_subjects = ClassSubject.objects.filter(subject=subject)
        student_count = StudentClass.objects.filter(
            class_id__in=[cs.class_id.id for cs in class_subjects]
        ).count()
        subject_list.append(subject.subject_name)
        student_count_list_in_subject.append(student_count)

    # Get staff attendance statistics
    staffs = Staffs.objects.all()
    attendance_present_list_staff = []
    staff_name_list = []
    
    for staff in staffs:
        class_subjects = ClassSubject.objects.filter(staff=staff)
        attendance = Attendance.objects.filter(class_subject__in=class_subjects).count()
        attendance_present_list_staff.append(attendance)
        staff_name_list.append(staff.admin.username)

    # Get student attendance statistics
    students_all = Students.objects.all()
    attendance_present_list_student = []
    attendance_absent_list_student = []
    student_name_list = []
    
    for student in students_all:
        attendance = AttendanceReport.objects.filter(student_id=student.id, status=True).count()
        absent = AttendanceReport.objects.filter(student_id=student.id, status=False).count()
        attendance_present_list_student.append(attendance)
        attendance_absent_list_student.append(absent)
        student_name_list.append(student.admin.username)

    # Prepare context
    context = {
        "student_count": student_count1,
        "staff_count": staff_count,
        "subject_count": subject_count,
        "course_count": course_count,
        "course_name_list": course_name_list,
        "subject_count_list": subject_count_list,
        "student_count_list_in_course": student_count_list_in_course,
        "student_count_list_in_subject": student_count_list_in_subject,
        "subject_list": subject_list,
        "staff_name_list": staff_name_list,
        "attendance_present_list_staff": attendance_present_list_staff,
        "student_name_list": student_name_list,
        "attendance_present_list_student": attendance_present_list_student,
        "attendance_absent_list_student": attendance_absent_list_student,
        # URL variables for sidebar
        "admin_home": reverse('admin_home'),
        "add_course_url": reverse('add_course'),
        "manage_course_url": reverse('manage_course'),
        "add_course_session_url": reverse('add_course_session'),
        "manage_course_session_url": reverse('manage_course_session'),
        "add_subject_url": reverse('add_subject'),
        "manage_subject_url": reverse('manage_subject'),
        "manage_class_url": reverse('manage_class'),
        "add_staff_url": reverse('add_staff'),
        "manage_staff_url": reverse('manage_staff'),
        "bulk_upload_staff_url": reverse('bulk_upload_staff'),
        "add_student_url": reverse('add_student'),
        "manage_student_url": reverse('manage_student'),
        "bulk_upload_student_url": reverse('bulk_upload_student'),
        "admin_view_attendance_url": reverse('admin_view_attendance'),
        "student_feedback_message_url": reverse('student_feedback_message'),
        "staff_feedback_message_url": reverse('staff_feedback_message'),
    }

    return render(request, "hod_template/home_content.html", context)

def add_staff(request):
    """
    View function to display the staff addition form.
    """
    return render(request, "hod_template/add_staff_template.html")

def add_staff_save(request):
    """
    View function to handle staff addition form submission.
    Creates a new staff member with the provided details.
    """
    if request.method != "POST":
        return HttpResponse("Method Not Allowed")
    else:
        form = AddStaffForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            email = form.cleaned_data["email"]
            address = form.cleaned_data["address"]
            employee_id = form.cleaned_data["employee_id"]
            
            try:
                # Check if email already exists
                if CustomUser.objects.filter(email=email).exists():
                    messages.error(request, "Email already exists")
                    return HttpResponseRedirect(reverse("add_staff"))
                
                # Generate username from email
                username = generate_username_from_email(email)
                
                # Generate a random password
                from student_management_app.utils import generate_random_password
                password = generate_random_password()
                
                # Check if there are any deleted IDs available
                deleted_id = DeletedStaffID.objects.first()
                
                with transaction.atomic():
                    # Create the user first
                    user = CustomUser.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        last_name=last_name,
                        first_name=first_name,
                        user_type=2,
                        is_active=True,  # User is active immediately
                        skip_profile_creation=True  # Skip automatic profile creation
                    )
                    
                    # Create the staff profile
                    if deleted_id:
                        # Create staff with the deleted ID
                        staff = Staffs.objects.create(
                            id=deleted_id.deleted_id,
                            admin=user,
                            address=address,
                            employee_id=employee_id
                        )
                        # Remove the used ID from deleted IDs
                        deleted_id.delete()
                    else:
                        # Create staff with auto-incrementing ID
                        staff = Staffs.objects.create(
                            admin=user,
                            address=address,
                            employee_id=employee_id
                        )
                    
                    # Send credentials email
                    from student_management_app.utils import send_account_credentials_email
                    send_account_credentials_email(user, password, request)
                    
                messages.success(request, "Successfully Added Staff. Account credentials have been sent to the email.")
                return HttpResponseRedirect(reverse("add_staff"))
            except Exception as e:
                messages.error(request, f"Failed To Add Staff: {str(e)}")
                return HttpResponseRedirect(reverse("add_staff"))
        else:
            messages.error(request, "Please Fill Form Properly")
            return HttpResponseRedirect(reverse("add_staff"))

def add_course(request):
    """
    View function to display the course addition form.
    """
    return render(request, "hod_template/add_course_template.html")

def add_course_save(request):
    """
    View function to handle course addition form submission.
    Creates a new course with the provided details.
    """
    if request.method != "POST":
        return HttpResponse("Method Not Allowed")
    else:
        course_name = request.POST.get("course")
        try:
            # Check if there are any deleted IDs available
            deleted_id = DeletedCourseID.objects.first()
            
            if deleted_id:
                # Create course with the deleted ID
                course = Courses(id=deleted_id.deleted_id, course_name=course_name)
                course.save()
                # Remove the used ID from deleted IDs
                deleted_id.delete()
            else:
                # Create course with auto-incrementing ID
                course = Courses(course_name=course_name)
                course.save()
                
            messages.success(request, "Successfully Added Course")
            return HttpResponseRedirect(reverse("manage_course"))
        except Exception as e:
            messages.error(request, f"Failed To Add Course: {str(e)}")
            return HttpResponseRedirect(reverse("manage_course"))

def add_student(request):
    """
    View function to display the student addition form.
    """
    form = AddStudentForm()
    courses = Courses.objects.all()
    session_years = SessionYearModel.objects.all()
    context = {
        "form": form,
        "courses": courses,
        "session_years": session_years
    }
    return render(request, "hod_template/add_student_template.html", context)

def add_student_save(request):
    if request.method != "POST":
        return HttpResponseRedirect(reverse("add_student"))
    else:
        form = AddStudentForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                first_name = form.cleaned_data["first_name"]
                last_name = form.cleaned_data["last_name"]
                email = form.cleaned_data["email"]
                address = form.cleaned_data["address"]
                session_year = form.cleaned_data["session_year_id"]
                course = form.cleaned_data["course"]
                gender = form.cleaned_data["gender"]
                registration_number = form.cleaned_data.get("registration_number", "")
                parents_email = form.cleaned_data.get("parents_email", "")
                profile_pic = request.FILES.get("profile_pic")

                # Generate username from email
                username = generate_username_from_email(email)
                
                # Generate a secure random password
                from student_management_app.utils import generate_random_password
                password = generate_random_password()

                # Check if there's a deleted ID we can reuse
                deleted_id = DeletedStudentID.objects.all().first()

                # Use transaction to ensure both user and student are created or neither
                with transaction.atomic():
                    # Create the user with skip_profile_creation=True to prevent automatic profile creation
                    user = CustomUser.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name,
                        user_type=3,  # Student type
                        is_active=True,  # Set account as active by default
                        email_verified=True,  # Mark email as verified since admin is creating it
                        skip_profile_creation=True  # Skip automatic profile creation
                    )

                    # Create the student profile, reusing deleted ID if available
                    if deleted_id:
                        # Create student with the deleted ID
                        student = Students.objects.create(
                            id=deleted_id.deleted_id,
                            admin=user,
                            course_id=course,
                            session_year_id=session_year,
                            address=address,
                            gender=gender,
                            registration_number=registration_number,
                            parents_email=parents_email
                        )
                        # Remove the used ID from deleted IDs
                        deleted_id.delete()
                    else:
                        # Create student with auto-incrementing ID
                        student = Students.objects.create(
                            admin=user,
                            course_id=course,
                            session_year_id=session_year,
                            address=address,
                            gender=gender,
                            registration_number=registration_number,
                            parents_email=parents_email
                        )

                    # Handle profile picture if provided
                    if profile_pic:
                        student.profile_pic = profile_pic
                        student.save()
                    
                    # Send account credentials email to the student
                    try:
                        from student_management_app.utils import send_account_credentials_email
                        email_sent = send_account_credentials_email(user, password, request)
                        if not email_sent:
                            print(f"Failed to send credentials email to {user.email} - returned False")
                    except Exception as email_error:
                        print(f"Error sending credentials email to {user.email}: {str(email_error)}")
                        # Continue with account creation even if email fails

                messages.success(request, "Successfully Added Student. Account credentials have been sent to the email.")
                return HttpResponseRedirect(reverse("add_student"))
            except Exception as e:
                messages.error(request, f"Failed to Add Student: {str(e)}")
                return HttpResponseRedirect(reverse("add_student"))
        else:
            messages.error(request, "Please Fill Form Properly")
            return HttpResponseRedirect(reverse("add_student"))

def add_course_session(request):
    """
    View function to display the course session addition form.
    """
    courses = Courses.objects.all()
    sessions = SessionYearModel.objects.all()
    return render(request, "hod_template/add_course_session_template.html", {
        "courses": courses,
        "sessions": sessions
    })

def add_course_session_save(request):
    """
    View function to handle course session addition form submission.
    Creates a new course session with the provided details.
    """
    if request.method != "POST":
        return HttpResponse("Method Not Allowed")
    else:
        course_id = request.POST.get("course")
        session_id = request.POST.get("session")
        try:
            course = Courses.objects.get(id=course_id)
            session = SessionYearModel.objects.get(id=session_id)
            course_session = CourseSession(
                course=course,
                session_year=session
            )
            course_session.save()
            messages.success(request, "Successfully Added Course Session")
            return HttpResponseRedirect(reverse("add_course_session"))
        except Exception as e:
            messages.error(request, f"Failed To Add Course Session: {str(e)}")
            return HttpResponseRedirect(reverse("add_course_session"))

def manage_course_session(request):
    """
    View function to display the course session management page.
    """
    sessions = SessionYearModel.objects.all()
    return render(request, "hod_template/manage_course_session_template.html", {
        "sessions": sessions
    })

def add_subject(request):
    """
    View function to display the subject addition form.
    """
    courses = Courses.objects.all()
    sessions = SessionYearModel.objects.all()
    context = {
        "courses": courses,
        "sessions": sessions
    }
    return render(request, "hod_template/add_subject_template.html", context)

@csrf_exempt
def get_courses_by_session(request):
    """
    View function to handle AJAX request for getting courses by session.
    """
    if request.method != "POST":
        return HttpResponse("Method Not Allowed")
    else:
        session_id = request.POST.get("session_id")
        try:
            # Get all course sessions for this session year
            session = SessionYearModel.objects.get(id=session_id)
            course_sessions = CourseSession.objects.filter(session_year=session)
            
            # Get unique courses from these sessions
            courses = []
            seen_course_ids = set()
            
            for cs in course_sessions:
                if cs.course.id not in seen_course_ids:
                    courses.append({
                        'id': cs.course.id,
                        'course_name': cs.course.course_name
                    })
                    seen_course_ids.add(cs.course.id)
            
            return JsonResponse({
                "courses": courses,
                "session_name": f"{session.start_year} - {session.end_year}"
            })
        except SessionYearModel.DoesNotExist:
            return JsonResponse({"error": "Session not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

def add_subject_save(request):
    """
    View function to handle subject addition form submission.
    Creates a new subject with the provided details for each selected course-session combination.
    """
    if request.method != "POST":
        return HttpResponse("Method Not Allowed")
    else:
        subject_name = request.POST.get("subject_name")
        course_ids = request.POST.getlist("course[]")
        session_ids = request.POST.getlist("session[]")
        
        # Check if we have valid data
        if not subject_name or not course_ids or not session_ids:
            messages.error(request, "Please provide all required fields")
            return HttpResponseRedirect(reverse("add_subject"))
        
        # Check if course_ids and session_ids have the same length
        if len(course_ids) != len(session_ids):
            messages.error(request, "Invalid course-session data")
            return HttpResponseRedirect(reverse("add_subject"))
        
        successful_adds = 0
        failed_adds = 0
        
        # Process each course-session combination
        for i in range(len(course_ids)):
            course_id = course_ids[i]
            session_id = session_ids[i]
            
            # Skip empty entries
            if not course_id or not session_id:
                continue
                
            try:
                # Get the course and session
                course = Courses.objects.get(id=course_id)
                session = SessionYearModel.objects.get(id=session_id)
                
                # Get or create the course session
                course_session, created = CourseSession.objects.get_or_create(
                    course=course,
                    session_year=session
                )
                
                # Check if the subject already exists for this course session
                if Subjects.objects.filter(subject_name=subject_name, course_session=course_session).exists():
                    failed_adds += 1
                    continue
                
                # Check if there are any deleted IDs available
                deleted_id = DeletedSubjectID.objects.first()
                
                if deleted_id:
                    # Create subject with the deleted ID
                    subject = Subjects(id=deleted_id.deleted_id, subject_name=subject_name,
                                    course_session=course_session)
                    subject.save()
                    # Remove the used ID from deleted IDs
                    deleted_id.delete()
                else:
                    # Create subject with auto-incrementing ID
                    subject = Subjects(subject_name=subject_name,
                                    course_session=course_session)
                    subject.save()
                
                successful_adds += 1
            except Exception as e:
                failed_adds += 1
                continue
        
        if successful_adds > 0:
            if failed_adds > 0:
                messages.warning(request, f"Subject added to {successful_adds} course-session combinations. Failed to add to {failed_adds} combinations.")
            else:
                messages.success(request, f"Subject successfully added to {successful_adds} course-session combinations.")
        else:
            messages.error(request, "Failed to add subject to any course-session combination")
            
        return HttpResponseRedirect(reverse("add_subject"))

def manage_subject(request):
    """
    View function to display the subject management page.
    """
    subjects = Subjects.objects.all().order_by('subject_name', 'course_session__session_year')
    
    # Group subjects by name for easier viewing
    subjects_by_name = {}
    for subject in subjects:
        if subject.subject_name not in subjects_by_name:
            subjects_by_name[subject.subject_name] = []
        subjects_by_name[subject.subject_name].append(subject)
    
    # Convert to list of groups for template
    subject_groups = []
    for subject_name, subject_list in subjects_by_name.items():
        subject_groups.append({
            'name': subject_name,
            'count': len(subject_list),
            'subjects': subject_list
        })
    
    return render(request, "hod_template/manage_subject_template.html", {
        "subjects": subjects,
        "subject_groups": subject_groups
    })

def manage_staff(request):
    """
    View function to display the staff management page.
    """
    staffs = Staffs.objects.all()
    return render(request, "hod_template/manage_staff_template.html", {"staffs": staffs})

def manage_student(request):
    """
    View function to display the student management page.
    """
    search_query = request.GET.get('search', '')  # Get the search query from the request
    students = Students.objects.all()

    if search_query:
        # Split the search query to handle first name + last name search
        name_parts = search_query.split()
        
        # Start with an empty Q object
        from django.db.models import Q
        query = Q()
        
        # If we have two or more parts, try first name + last name combination
        if len(name_parts) >= 2:
            query |= Q(admin__first_name__icontains=name_parts[0], admin__last_name__icontains=name_parts[1])
        
        # Add individual field searches
        query |= Q(admin__first_name__icontains=search_query)  # First name
        query |= Q(admin__last_name__icontains=search_query)   # Last name
        query |= Q(registration_number__icontains=search_query)  # Registration number
        
        # Apply the combined filter
        students = students.filter(query).distinct()

    sessions = SessionYearModel.objects.all()
    
    context = {
        'students': students,
        'sessions': sessions,
        'search_query': search_query
    }
    return render(request, "hod_template/manage_student_template.html", context)

def manage_course(request):
    """
    View function to display the course management page.
    """
    courses = Courses.objects.all()
    return render(request, "hod_template/manage_course_template.html", {"courses": courses})

def edit_staff(request, staff_id):
    """
    View function to display the staff editing form.
    """
    staff = Staffs.objects.get(admin=staff_id)
    return render(request, "hod_template/edit_staff_template.html", {"staff": staff, "id": staff_id})

def edit_staff_save(request):
    """
    View function to handle staff editing form submission.
    Updates the staff details with the provided information.
    """
    if request.method != "POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        staff_id = request.POST.get("staff_id")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        username = request.POST.get("username")
        address = request.POST.get("address")
        employee_id = request.POST.get("employee_id")

        try:
            user = CustomUser.objects.get(id=staff_id)
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.username = username
            user.save()

            staff_model = Staffs.objects.get(admin=staff_id)
            staff_model.address = address
            staff_model.employee_id = employee_id
            staff_model.save()
            messages.success(request, "Successfully Edited Staff")
            return HttpResponseRedirect(reverse("edit_staff", kwargs={"staff_id": staff_id}))
        except:
            messages.error(request, "Failed to Edit Staff")
            return HttpResponseRedirect(reverse("edit_staff", kwargs={"staff_id": staff_id}))

def edit_student(request, student_id):
    """
    View function to display the student editing form.
    """
    request.session['student_id'] = student_id
    student = Students.objects.get(admin=student_id)
    form = EditStudentForm()
    
    # Populate form with existing data
    form.fields['email'].initial = student.admin.email
    form.fields['first_name'].initial = student.admin.first_name
    form.fields['last_name'].initial = student.admin.last_name
    form.fields['username'].initial = student.admin.username
    form.fields['address'].initial = student.address
    form.fields['course'].initial = student.course_id.id
    form.fields['gender'].initial = student.gender
    form.fields['session_year_id'].initial = student.session_year_id.id
    form.fields['registration_number'].initial = student.registration_number
    form.fields['parents_email'].initial = student.parents_email
    
    return render(request, "hod_template/edit_student_template.html", {
        "form": form,
        "id": student_id,
        "username": student.admin.username
    })

def edit_student_save(request):
    """
    View function to handle student editing form submission.
    Updates the student details with the provided information.
    """
    if request.method != "POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        student_id = request.session.get("student_id")
        if student_id == None:
            return HttpResponseRedirect(reverse("manage_student"))

        form = EditStudentForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Update CustomUser fields
                user = CustomUser.objects.get(id=student_id)
                user.first_name = form.cleaned_data["first_name"]
                user.last_name = form.cleaned_data["last_name"]
                user.email = form.cleaned_data["email"]
                user.username = form.cleaned_data["username"]
                user.save()

                # Update Student fields
                student = Students.objects.get(admin=student_id)
                student.address = form.cleaned_data["address"]
                student.gender = form.cleaned_data["gender"]
                
                # Get Course instance
                course = Courses.objects.get(id=form.cleaned_data["course"])
                student.course_id = course
                
                # Get SessionYear instance
                session_year = SessionYearModel.objects.get(id=form.cleaned_data["session_year_id"])
                student.session_year_id = session_year
                
                student.registration_number = form.cleaned_data["registration_number"]
                student.parents_email = form.cleaned_data["parents_email"]

                if 'profile_pic' in request.FILES:
                    profile_pic = request.FILES['profile_pic']
                    fs = FileSystemStorage()
                    filename = fs.save(profile_pic.name, profile_pic)
                    student.profile_pic = fs.url(filename)

                student.save()
                del request.session['student_id']
                messages.success(request, "Successfully Edited Student")
                return HttpResponseRedirect(reverse("edit_student", kwargs={"student_id": student_id}))
            except Exception as e:
                messages.error(request, f"Failed to Edit Student: {str(e)}")
                return HttpResponseRedirect(reverse("edit_student", kwargs={"student_id": student_id}))
        else:
            messages.error(request, "Invalid Form Data")
            return HttpResponseRedirect(reverse("edit_student", kwargs={"student_id": student_id}))

def edit_subject(request, subject_id):
    """
    View function to display the subject editing form.
    """
    subject = Subjects.objects.get(id=subject_id)
    courses = Courses.objects.all()
    sessions = SessionYearModel.objects.all()
    
    return render(request, "hod_template/edit_subject_template.html", {
        "subject": subject,
        "courses": courses,
        "sessions": sessions,
        "id": subject_id
    })

def edit_subject_save(request):
    """
    View function to handle subject editing form submission.
    Updates the subject details with the provided information.
    """
    if request.method != "POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        subject_id = request.POST.get("subject_id")
        subject_name = request.POST.get("subject_name")
        course_id = request.POST.get("course")
        session_id = request.POST.get("session")

        try:
            subject = Subjects.objects.get(id=subject_id)
            subject.subject_name = subject_name
            
            # Get the course session
            course = Courses.objects.get(id=course_id)
            session = SessionYearModel.objects.get(id=session_id)
            
            # Get or create the course session
            course_session, created = CourseSession.objects.get_or_create(
                course=course, 
                session_year=session
            )
            
            subject.course_session = course_session
            subject.save()

            messages.success(request, "Subject updated successfully!")
            return HttpResponseRedirect(reverse("manage_subject"))
        except Exception as e:
            messages.error(request, f"Failed to update subject: {str(e)}")
            return HttpResponseRedirect(reverse("edit_subject", kwargs={"subject_id": subject_id}))

def edit_course(request, course_id):
    """
    View function to display the course editing form.
    """
    course = Courses.objects.get(id=course_id)
    return render(request, "hod_template/edit_course_template.html", {"course": course, "id": course_id})

def edit_course_save(request):
    """
    View function to handle course editing form submission.
    Updates the course details with the provided information.
    """
    if request.method != "POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        course_id = request.POST.get("course_id")
        course_name = request.POST.get("course")

        try:
            course = Courses.objects.get(id=course_id)
            course.course_name = course_name
            course.save()
            messages.success(request, "Successfully Edited Course")
            return HttpResponseRedirect(reverse("manage_course"))
        except:
            messages.error(request, "Failed to Edit Course")
            return HttpResponseRedirect(reverse("manage_course"))

def delete_course(request, course_id):
    """
    View function to handle course deletion.
    Deletes the specified course and its associated data.
    """
    try:
        course = Courses.objects.get(id=course_id)
        # Store the deleted ID
        DeletedCourseID.objects.create(deleted_id=course_id)
        course.delete()
        messages.success(request, "Successfully Deleted Course")
    except Exception as e:
        messages.error(request, f"Failed to Delete Course: {str(e)}")
    return HttpResponseRedirect(reverse("manage_course"))

def add_session(request):
    """
    View function to display the session addition form.
    """
    return render(request, "hod_template/add_session_template.html")

def manage_session(request):
    """
    View function to display the session management page.
    """
    sessions = SessionYearModel.objects.all()
    context = {
        "sessions": sessions
    }
    return render(request, "hod_template/manage_session_template.html", context)

def edit_session(request, session_id):
    """
    View function to display the session editing form.
    """
    session = get_object_or_404(SessionYearModel, id=session_id)
    context = {
        "session": session
    }
    return render(request, "hod_template/edit_session_template.html", context)

def edit_session_save(request):
    """
    View function to handle session editing form submission.
    Updates the session details with the provided information.
    """
    if request.method != "POST":
        messages.error(request, "Invalid Method!")
        return redirect('manage_session')
    else:
        session_id = request.POST.get('session_id')
        session_start = request.POST.get('session_start')
        session_end = request.POST.get('session_end')

        try:
            session = SessionYearModel.objects.get(id=session_id)
            session.start_year = session_start
            session.end_year = session_end
            session.save()

            messages.success(request, "Session Updated Successfully.")
            return redirect('/manage_session')
        except Exception as e:
            messages.error(request, f"Failed to Update Session: {str(e)}")
            return redirect('/edit_session/' + session_id)

def delete_session(request, session_id):
    """
    View function to handle session deletion.
    Deletes the specified session and its associated data.
    """
    try:
        session = SessionYearModel.objects.get(id=session_id)
        session.delete()
        messages.success(request, "Session Deleted Successfully.")
        return redirect('manage_course_session')
    except Exception as e:
        messages.error(request, f"Failed to Delete Session: {str(e)}")
        return redirect('manage_course_session')

@csrf_exempt
def check_email_exist(request):
    """
    View function to handle AJAX request for checking email existence.
    """
    email = request.POST.get("email")
    user_obj = CustomUser.objects.filter(email=email).exists()
    if user_obj:
        return HttpResponse(True)
    else:
        return HttpResponse(False)

@csrf_exempt
def check_username_exist(request):
    """
    View function to handle AJAX request for checking username existence.
    """
    username = request.POST.get("username")
    user_obj = CustomUser.objects.filter(username=username).exists()
    if user_obj:
        return HttpResponse(True)
    else:
        return HttpResponse(False)

def staff_feedback_message(request):
    """
    View function to display the staff feedback messages.
    """
    feedbacks = FeedBackStaffs.objects.all()
    return render(request, "hod_template/staff_feedback_template.html", {"feedbacks": feedbacks})

def student_feedback_message(request):
    """
    View function to display the student feedback messages.
    """
    feedbacks = FeedBackStudent.objects.all()
    return render(request, "hod_template/student_feedback_template.html", {"feedbacks": feedbacks})

@csrf_exempt
def student_feedback_message_replied(request):
    """
    View function to handle AJAX request for replying to student feedback messages.
    """
    feedback_id = request.POST.get("id")
    feedback_message = request.POST.get("message")

    try:
        feedback = FeedBackStudent.objects.get(id=feedback_id)
        feedback.feedback_reply = feedback_message
        feedback.save()
        return HttpResponse("True")
    except:
        return HttpResponse("False")

@csrf_exempt
def staff_feedback_message_replied(request):
    """
    View function to handle AJAX request for replying to staff feedback messages.
    """
    feedback_id = request.POST.get("id")
    feedback_message = request.POST.get("message")

    try:
        feedback = FeedBackStaffs.objects.get(id=feedback_id)
        feedback.feedback_reply = feedback_message
        feedback.save()
        return HttpResponse("True")
    except:
        return HttpResponse("False")

def admin_view_attendance(request):
    if request.method == 'POST':
        session_id = request.POST.get('session_id')
        class_id = request.POST.get('class_id')
        subject_id = request.POST.get('subject_id')

        try:
            # Get the class subject
            class_subject = ClassSubject.objects.get(
                class_id=class_id,
                subject_id=subject_id
            )

            # Get attendance records
            attendance_records = Attendance.objects.filter(class_subject=class_subject)
            total_classes = attendance_records.count()

            # Get students in this class
            students = StudentClass.objects.filter(class_id=class_id)
            attendance_data = []

            # Get session, class and subject objects for display
            session = SessionYearModel.objects.get(id=session_id)
            class_obj = Class.objects.get(id=class_id)
            subject = Subjects.objects.get(id=subject_id)

            for student_class in students:
                student = student_class.student
                present_count = AttendanceReport.objects.filter(
                    student=student,
                    attendance__class_subject=class_subject,
                    status=True
                ).count()

                absent_count = total_classes - present_count
                attendance_percentage = (present_count / total_classes * 100) if total_classes > 0 else 0

                attendance_data.append({
                    'student_name': f"{student.admin.first_name} {student.admin.last_name}",
                    'registration_number': student.registration_number,
                    'total_classes': total_classes,
                    'classes_attended': present_count,
                    'classes_absent': absent_count,
                    'attendance_percentage': round(attendance_percentage, 2)
                })

            # Get faculty name
            faculty_name = "Not Assigned"
            if class_subject.staff:
                faculty_name = f"{class_subject.staff.admin.first_name} {class_subject.staff.admin.last_name}"

            context = {
                'attendance_data': attendance_data,
                'session': session,
                'class_obj': class_obj,
                'subject': subject,
                'faculty_name': faculty_name,
                'total_classes': total_classes,
                'sessions': SessionYearModel.objects.all(),
                'classes': Class.objects.all(),
                'subjects': Subjects.objects.all()
            }

            return render(request, 'hod_template/admin_view_attendance.html', context)

        except Exception as e:
            messages.error(request, f"Error fetching attendance data: {str(e)}")
            return redirect('admin_view_attendance')

    # For GET request, show the form
    context = {
        'sessions': SessionYearModel.objects.all(),
        'classes': Class.objects.all(),
        'subjects': Subjects.objects.all()
    }
    return render(request, 'hod_template/admin_view_attendance.html', context)

def export_attendance_excel(request):
    """
    View function to export attendance records for a specific class, subject, and session to an Excel file.
    """
    import xlwt
    from django.http import HttpResponse
    from datetime import datetime

    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        subject_id = request.POST.get('subject_id')
        session_id = request.POST.get('session_id')
        date = request.POST.get('date')

        try:
            class_obj = Class.objects.get(id=class_id)
            subject = Subjects.objects.get(id=subject_id)
            session = SessionYearModel.objects.get(id=session_id)
            class_subject = ClassSubject.objects.get(class_id=class_obj, subject=subject)
            students = StudentClass.objects.filter(class_id=class_obj)

            attendance = Attendance.objects.filter(
                class_subject=class_subject,
                session_year=session,
                date=date
            ).first()

            if not attendance:
                return HttpResponse("No attendance records found for the selected date.")

            # Create workbook and worksheet
            wb = xlwt.Workbook(encoding='utf-8')
            ws = wb.add_sheet('Attendance')

            # Add headers
            row_num = 0
            columns = ['Student Name', 'Registration Number', 'Status', 'Date']

            for col_num in range(len(columns)):
                ws.write(row_num, col_num, columns[col_num])

            # Add data
            attendance_reports = AttendanceReport.objects.filter(attendance=attendance)
            for attendance_report in attendance_reports:
                row_num += 1
                row = [
                    f"{attendance_report.student.admin.first_name} {attendance_report.student.admin.last_name}",
                    attendance_report.student.registration_number,
                    'Present' if attendance_report.status else 'Absent',
                    date
                ]
                for col_num in range(len(row)):
                    ws.write(row_num, col_num, row[col_num])

            # Set column widths
            for col_num in range(len(columns)):
                ws.col(col_num).width = 256 * 20

            # Create response
            response = HttpResponse(content_type='application/ms-excel')
            response['Content-Disposition'] = f'attachment; filename="attendance_{date}.xls"'
            wb.save(response)
            return response

        except Exception as e:
            return HttpResponse(f"Error: {str(e)}")

    return HttpResponse("Invalid request method")

def bulk_upload_staff(request):
    """
    View function to display the staff bulk upload form.
    """
    return render(request, "hod_template/bulk_upload_staff_template.html")

def bulk_upload_staff_save(request):
    """
    View function to handle staff bulk upload form submission.
    Creates multiple staff members from an uploaded Excel file.
    """
    if request.method != "POST":
        return HttpResponse("Method Not Allowed")
    
    if 'staff_file' not in request.FILES:
        messages.error(request, "Please upload a file")
        return HttpResponseRedirect(reverse("bulk_upload_staff"))
    
    file = request.FILES['staff_file']
    if not file.name.endswith(('.xlsx', '.xls')):
        messages.error(request, "Please upload an Excel file (.xlsx or .xls)")
        return HttpResponseRedirect(reverse("bulk_upload_staff"))
    
    try:
        # Read Excel file
        df = pd.read_excel(file)
        
        # Validate required columns
        required_columns = ['first_name', 'last_name', 'email', 'address', 'employee_id']
        if not all(col in df.columns for col in required_columns):
            messages.error(request, "Excel file must contain all required columns")
            return HttpResponseRedirect(reverse("bulk_upload_staff"))
        
        # Validate data before processing
        error_messages = []
        for index, row in df.iterrows():
            if pd.isna(row['email']) or pd.isna(row['first_name']) or pd.isna(row['last_name']) or pd.isna(row['employee_id']):
                error_messages.append(f"Row {index + 2}: All required fields must be filled")
                continue
                
            if CustomUser.objects.filter(email=row['email']).exists():
                error_messages.append(f"Row {index + 2}: Email {row['email']} already exists")
                continue
                
            if Staffs.objects.filter(employee_id=row['employee_id']).exists():
                error_messages.append(f"Row {index + 2}: Employee ID {row['employee_id']} already exists")
                continue
        
        if error_messages:
            messages.error(request, "Validation failed. Found the following errors:\n" + "\n".join(error_messages))
            return HttpResponseRedirect(reverse("bulk_upload_staff"))
        
        # Process in batches of 100
        BATCH_SIZE = 100
        total_records = len(df)
        success_count = 0
        error_count = 0
        users_to_activate = []  # Store users for delayed email sending
        
        for start_idx in range(0, total_records, BATCH_SIZE):
            end_idx = min(start_idx + BATCH_SIZE, total_records)
            batch_df = df.iloc[start_idx:end_idx]
            
            for _, row in batch_df.iterrows():
                try:
                    # Generate username from email
                    username = generate_username_from_email(row['email'])
                    
                    # Generate activation token
                    activation_token = get_random_string(32)
                    
                    with transaction.atomic():
                        user = CustomUser.objects.create_user(
                            username=username,
                            password=generate_random_password(),  # Generate random password
                            email=row['email'],
                            last_name=row['last_name'],
                            first_name=row['first_name'],
                            user_type=2,
                            is_active=False,
                            activation_token=activation_token,
                            activation_token_created=timezone.now()
                        )
                        
                        staff = user.staffs
                        staff.address = row['address']
                        staff.employee_id = row['employee_id']
                        staff.save()
                        
                        # Store user for delayed email sending
                        users_to_activate.append((user, activation_token))
                        
                        success_count += 1
                except Exception as e:
                    error_count += 1
                    print(f"Error creating staff {row['email']}: {str(e)}")
            
            # Log progress
            progress = min(100, int((end_idx / total_records) * 100))
            print(f"Progress: {progress}% ({end_idx}/{total_records} records processed)")
        
        # Send activation emails after 30 seconds delay
        def delayed_email_sending():
            time.sleep(30)  # Wait for 30 seconds
            for user, activation_token in users_to_activate:
                try:
                    send_activation_email(user, activation_token)
                    print(f"Activation email sent to {user.email}")
                except Exception as e:
                    print(f"Error sending activation email to {user.email}: {str(e)}")
        
        # Start the email sending in a separate thread
        email_thread = threading.Thread(target=delayed_email_sending)
        email_thread.daemon = True
        email_thread.start()
        
        messages.success(request, f"Successfully added {success_count} staff members. {error_count} failed. Activation emails will be sent after 30 seconds.")
        return HttpResponseRedirect(reverse("bulk_upload_staff"))
        
    except Exception as e:
        messages.error(request, f"Failed to process file: {str(e)}")
        return HttpResponseRedirect(reverse("bulk_upload_staff"))

def bulk_upload_student(request):
    """
    View function to display the student bulk upload form.
    """
    form = BulkUploadStudentForm()
    return render(request, "hod_template/bulk_upload_student_template.html", {'form': form})

def bulk_upload_student_save(request):
    """
    View function to handle student bulk upload form submission.
    Creates multiple students from an uploaded Excel file.
    """
    if request.method != "POST":
        return HttpResponse("Method Not Allowed")
    
    # Check if this is a confirmation submission
    confirmed = request.POST.get('confirmed') == 'yes'
    
    # Get form values
    course_id = request.POST.get('course')
    session_year_id = request.POST.get('session_year_id')
    update_existing = request.POST.get('update_existing') == 'yes'
    
    if not course_id or not session_year_id:
        messages.error(request, "Please select both course and session year")
        return HttpResponseRedirect(reverse("bulk_upload_student"))
    
    # Check if we need to process from a stored file after confirmation
    if confirmed and 'temp_file_path' in request.session:
        # Use the stored file path and parameters
        file_path = request.session.get('temp_file_path')
        course_id = request.session.get('course_id')
        session_year_id = request.session.get('session_year_id')
        update_existing = request.session.get('update_existing')
        
        # Clean up the session
        for key in ['temp_file_path', 'course_id', 'session_year_id', 'update_existing']:
            if key in request.session:
                del request.session[key]
        
        try:
            file = open(file_path, 'rb')
        except FileNotFoundError:
            messages.error(request, "The uploaded file is no longer available. Please upload again.")
            return HttpResponseRedirect(reverse("bulk_upload_student"))
    elif 'file' not in request.FILES:
        messages.error(request, "Please upload a file")
        return HttpResponseRedirect(reverse("bulk_upload_student"))
    else:
        file = request.FILES['file']
        if not file.name.endswith(('.xlsx', '.xls')):
            messages.error(request, "Please upload an Excel file (.xlsx or .xls)")
            return HttpResponseRedirect(reverse("bulk_upload_student"))
    
    try:
        # Read Excel file
        df = pd.read_excel(file)
        
        # Validate required columns
        required_columns = ['first_name', 'last_name', 'email', 'address', 
                          'gender', 'registration_number', 'parents_email']
        if not all(col in df.columns for col in required_columns):
            messages.error(request, "Excel file must contain all required columns")
            return HttpResponseRedirect(reverse("bulk_upload_student"))
        
        # Get the course and session year objects
        course = Courses.objects.get(id=course_id)
        session_year = SessionYearModel.objects.get(id=session_year_id)
        
        # Check for duplicate registration numbers within the Excel file itself
        registration_counts = df['registration_number'].value_counts()
        duplicate_reg_numbers = registration_counts[registration_counts > 1].index.tolist()
        
        if duplicate_reg_numbers:
            messages.error(request, f"The following registration numbers appear multiple times in your file: {', '.join(duplicate_reg_numbers)}. Please ensure each registration number is unique.")
            return HttpResponseRedirect(reverse("bulk_upload_student"))
        
        # Check for duplicate emails within the Excel file itself
        email_counts = df['email'].value_counts()
        duplicate_emails = email_counts[email_counts > 1].index.tolist()
        
        if duplicate_emails:
            messages.error(request, f"The following emails appear multiple times in your file: {', '.join(duplicate_emails)}. Please ensure each email is unique.")
            return HttpResponseRedirect(reverse("bulk_upload_student"))
        
        # Clean and standardize data
        # Convert gender to title case and strip spaces
        df['gender'] = df['gender'].apply(lambda x: str(x).strip().title() if not pd.isna(x) else x)
        # Strip whitespace from registration numbers and other text fields
        for col in ['first_name', 'last_name', 'email', 'address', 'registration_number', 'parents_email']:
            df[col] = df[col].apply(lambda x: str(x).strip() if not pd.isna(x) else x)
        
        # Pre-validate data and mark rows as valid or invalid
        validation_errors = []
        existing_users_count = 0
        
        # Create a new column to track if a row is valid
        df['is_valid'] = True
        
        for index, row in df.iterrows():
            row_num = index + 2  # +2 because Excel is 1-indexed and we have a header row
            
            # Check for missing required fields
            if pd.isna(row['email']) or pd.isna(row['first_name']) or pd.isna(row['last_name']) or pd.isna(row['registration_number']):
                validation_errors.append(f"Row {row_num}: All required fields must be filled")
                df.at[index, 'is_valid'] = False
                continue
                
            # Check for invalid gender
            if row['gender'] not in ['Male', 'Female']:
                validation_errors.append(f"Row {row_num}: Invalid gender value. Must be 'Male' or 'Female'")
                df.at[index, 'is_valid'] = False
                continue
            
            # If not updating existing, check for duplicates in database
            if not update_existing:    
                # Check if email exists
                if CustomUser.objects.filter(email=row['email']).exists():
                    validation_errors.append(f"Row {row_num}: Email {row['email']} already exists")
                    df.at[index, 'is_valid'] = False
                    continue
                    
                # Check if registration number exists
                if Students.objects.filter(registration_number=row['registration_number']).exists():
                    validation_errors.append(f"Row {row_num}: Registration number {row['registration_number']} already exists")
                    df.at[index, 'is_valid'] = False
                    continue
            else:
                # Count existing users that will be modified
                if CustomUser.objects.filter(email=row['email']).exists():
                    existing_users_count += 1
                
                # If updating existing, check if registration number exists for a different email
                existing_user = CustomUser.objects.filter(email=row['email']).first()
                existing_student_with_reg = Students.objects.filter(registration_number=row['registration_number']).first()
                
                if existing_student_with_reg and (not existing_user or existing_student_with_reg.admin_id != existing_user.id):
                    validation_errors.append(f"Row {row_num}: Registration number {row['registration_number']} is assigned to a different student")
                    df.at[index, 'is_valid'] = False
                    continue
        
        # Report validation errors but continue with valid records
        if validation_errors:
            warning_message = "Validation found errors in some records. These records will be skipped:\n" + "\n".join(validation_errors)
            messages.warning(request, warning_message)
        
        # Filter the DataFrame to only include valid rows
        valid_df = df[df['is_valid'] == True].copy()
        invalid_count = len(df) - len(valid_df)
        
        if len(valid_df) == 0:
            messages.error(request, "No valid records found to process. Please check your data and try again.")
            return HttpResponseRedirect(reverse("bulk_upload_student"))
            
        # If there are existing users to update, ask for confirmation if not already confirmed
        if existing_users_count > 0 and update_existing and not confirmed:
            # Store the file temporarily with only valid records
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
                valid_df.drop(columns=['is_valid']).to_excel(temp_file.name, index=False)
                temp_file_path = temp_file.name
                
            # Store in session
            request.session['temp_file_path'] = temp_file_path
            request.session['course_id'] = course_id
            request.session['session_year_id'] = session_year_id
            request.session['update_existing'] = update_existing
            
            # Redirect to confirmation page
            messages.warning(request, f"Found {existing_users_count} existing students that will be modified. Please confirm the update.")
            # Use a query parameter to indicate this is for confirmation
            return HttpResponseRedirect(reverse("bulk_upload_student") + f"?confirm=true&existing_count={existing_users_count}")
        
        # Process in batches of 100
        BATCH_SIZE = 100
        total_records = len(valid_df)
        success_count = 0
        update_count = 0
        error_count = 0
        users_to_email = []  # Store users for delayed email sending
        error_details = []  # Store detailed error messages
        
        # Get a set of all existing registration numbers to check against
        existing_registration_numbers = set(Students.objects.values_list('registration_number', flat=True))
        
        for start_idx in range(0, total_records, BATCH_SIZE):
            end_idx = min(start_idx + BATCH_SIZE, total_records)
            batch_df = valid_df.iloc[start_idx:end_idx]
            
            for _, row in batch_df.iterrows():
                try:
                    # Check if user already exists
                    existing_user = CustomUser.objects.filter(email=row['email']).first()
                    
                    # Double-check registration number uniqueness
                    if not update_existing and row['registration_number'] in existing_registration_numbers:
                        error_count += 1
                        error_details.append(f"Registration number {row['registration_number']} already exists (for email {row['email']})")
                        continue
                    
                    if existing_user and update_existing:
                        # Update existing user
                        with transaction.atomic():
                            existing_user.first_name = row['first_name']
                            existing_user.last_name = row['last_name']
                            existing_user.save()
                            
                            # Generate a new password for the existing user
                            password = generate_random_password()
                            existing_user.set_password(password)
                            existing_user.save()
                            
                            # Update student profile
                            try:
                                student = Students.objects.get(admin=existing_user)
                                student.address = row['address']
                                student.session_year_id = session_year
                                student.course_id = course
                                student.gender = row['gender']
                                student.registration_number = row['registration_number']
                                student.parents_email = row['parents_email']
                                student.save()
                                update_count += 1
                                
                                # Store user and password for email sending
                                users_to_email.append((existing_user, password))
                                
                                # Log the update
                                print(f"Updated existing student: {existing_user.email}")
                            except Students.DoesNotExist:
                                # Student record doesn't exist but user does - create it
                                student = Students.objects.create(
                                    admin=existing_user,
                                    address=row['address'],
                                    session_year_id=session_year,
                                    course_id=course,
                                    gender=row['gender'],
                                    registration_number=row['registration_number'],
                                    parents_email=row['parents_email']
                                )
                                success_count += 1
                                
                                # Store user and password for email sending
                                users_to_email.append((existing_user, password))
                    elif not existing_user:
                        # Create new user
                        # Generate username from email
                        username = generate_username_from_email(row['email'])
                        
                        # Generate a random password
                        password = generate_random_password()
                        
                        # Generate activation token
                        activation_token = get_random_string(32)
                        
                        # Check if there's a deleted ID we can reuse
                        deleted_id = DeletedStudentID.objects.all().first()
                        
                        with transaction.atomic():
                            user = CustomUser.objects.create_user(
                                username=username,
                                password=password,
                                email=row['email'],
                                last_name=row['last_name'],
                                first_name=row['first_name'],
                                user_type=3,
                                is_active=True,  # Set to active immediately
                                activation_token=activation_token,
                                activation_token_created=timezone.now(),
                                skip_profile_creation=True  # Skip automatic profile creation
                            )
                            
                            # Create student profile with reused ID if available
                            if deleted_id:
                                # Create student with the deleted ID
                                student = Students.objects.create(
                                    id=deleted_id.deleted_id,
                                    admin=user,
                                    address=row['address'],
                                    session_year_id=session_year,
                                    course_id=course,
                                    gender=row['gender'],
                                    registration_number=row['registration_number'],
                                    parents_email=row['parents_email']
                                )
                                # Remove the used ID from deleted IDs
                                deleted_id.delete()
                            else:
                                # Create student with auto-incrementing ID
                                student = Students.objects.create(
                                    admin=user,
                                    address=row['address'],
                                    session_year_id=session_year,
                                    course_id=course,
                                    gender=row['gender'],
                                    registration_number=row['registration_number'],
                                    parents_email=row['parents_email']
                                )
                            
                            # Store user and password for delayed email sending
                            users_to_email.append((user, password))
                            
                            # Add to set of existing registration numbers to prevent duplicates in this batch
                            existing_registration_numbers.add(row['registration_number'])
                            
                            success_count += 1
                    else:
                        # User exists but we're not updating - this should not happen due to pre-validation
                        print(f"Skipping existing user: {row['email']}")
                        continue
                except Exception as e:
                    error_count += 1
                    # Detailed error logging
                    error_message = f"Error processing student {row['email']}: {str(e)}"
                    error_details.append(error_message)
                    print(error_message)
                    # Log traceback for detailed debugging
                    import traceback
                    print(f"Traceback: {traceback.format_exc()}")
                    # Try to identify what specific field might be causing issues
                    for field in ['first_name', 'last_name', 'email', 'address', 'gender', 'registration_number', 'parents_email']:
                        try:
                            value = row[field]
                            print(f"Field {field} = {value}")
                        except Exception as field_error:
                            print(f"Error accessing field {field}: {str(field_error)}")
            
            # Log progress
            progress = min(100, int((end_idx / total_records) * 100))
            print(f"Progress: {progress}% ({end_idx}/{total_records} records processed)")
        
        # Clean up temporary file if it exists
        if confirmed and 'temp_file_path' in request.session:
            try:
                import os
                os.unlink(file_path)
            except:
                pass
        
        # Send account credentials emails after 10 seconds delay (for all processed users)
        if users_to_email:
            def delayed_email_sending():
                time.sleep(10)  # Wait for 10 seconds
                email_success_count = 0
                email_fail_count = 0
                
                for user, password in users_to_email:
                    try:
                        result = send_account_credentials_email(user, password, request)
                        if result:
                            print(f"Account credentials email sent successfully to {user.email}")
                            email_success_count += 1
                        else:
                            print(f"Failed to send account credentials email to {user.email} - returned False")
                            email_fail_count += 1
                    except Exception as e:
                        print(f"Error sending account credentials email to {user.email}: {str(e)}")
                        email_fail_count += 1
                
                print(f"Email sending complete. Success: {email_success_count}, Failed: {email_fail_count}")
            
            # Start the email sending in a separate thread
            email_thread = threading.Thread(target=delayed_email_sending)
            email_thread.daemon = True
            email_thread.start()
        
        status_message = f"Successfully processed {success_count + update_count} students out of {len(df)} records"
        if success_count > 0:
            status_message += f" (added {success_count} new"
            if update_count > 0:
                status_message += f", updated {update_count}"
            status_message += ")"
        elif update_count > 0:
            status_message += f" (updated {update_count})"
        
        if invalid_count > 0:
            status_message += f". {invalid_count} records were skipped due to validation errors."
        if error_count > 0:
            status_message += f" {error_count} records failed during processing."
            # Include some details about errors if available
            if error_details:
                # Show first 3 errors in the message with ellipsis if more
                if len(error_details) > 3:
                    error_summary = ". Sample errors: " + "; ".join(error_details[:3]) + "..."
                else:
                    error_summary = ". Errors: " + "; ".join(error_details)
                status_message += error_summary
        if users_to_email:
            status_message += " Account credentials will be sent via email to all processed students after 10 seconds."
            
        messages.success(request, status_message)
        return HttpResponseRedirect(reverse("bulk_upload_student"))
        
    except Exception as e:
        messages.error(request, f"Failed to process file: {str(e)}")
        import traceback
        print(f"Exception in bulk_upload_student_save: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return HttpResponseRedirect(reverse("bulk_upload_student"))

def download_sample_file(request, type):
    """
    View function to download sample Excel files for bulk upload.
    """
    if type not in ['staff', 'student']:
        return HttpResponse("Invalid file type")
    
    # Create sample data
    if type == 'staff':
        data = {
            'first_name': ['John', 'Jane'],
            'last_name': ['Doe', 'Smith'],
            'email': ['john.doe@example.com', 'jane.smith@example.com'],
            'password': ['password123', 'password456'],
            'address': ['123 Main St', '456 Oak Ave'],
            'employee_id': ['EMP001', 'EMP002']
        }
    else:
        data = {
            'first_name': ['John', 'Jane'],
            'last_name': ['Doe', 'Smith'],
            'email': ['john.doe@example.com', 'jane.smith@example.com'],
            'address': ['123 Main St', '456 Oak Ave'],
            'gender': ['Male', 'Female'],
            'registration_number': ['REG001', 'REG002'],
            'parents_email': ['parent1@example.com', 'parent2@example.com']
        }
    
    # Create DataFrame and save as Excel
    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="sample_{type}.xlsx"'
    df.to_excel(response, index=False)
    return response

def delete_staff(request, staff_id):
    """
    View function to handle staff deletion.
    Deletes the specified staff member and stores their ID for reuse.
    """
    try:
        admin = CustomUser.objects.get(id=staff_id)
        staff = Staffs.objects.get(admin=admin)
        staff_id_value = staff.id
        
        # Check if this staff is assigned to any subjects
        class_subjects = ClassSubject.objects.filter(staff=staff)
        if class_subjects.exists():
            messages.error(request, "Cannot delete staff who is assigned to subjects. Please reassign the subjects first.")
            return HttpResponseRedirect(reverse("manage_staff"))
        
        # Store the deleted ID
        DeletedStaffID.objects.create(deleted_id=staff_id_value)
        
        # Delete the user account (will cascade delete the staff record)
        admin.delete()
        
        messages.success(request, "Staff deleted successfully.")
    except Exception as e:
        messages.error(request, f"Failed to delete staff: {str(e)}")
    
    return HttpResponseRedirect(reverse("manage_staff"))

def update_staff_employee_id(request):
    """
    View function to handle AJAX request for updating staff employee ID.
    """
    if request.method != "POST":
        return HttpResponse("Method Not Allowed")
    
    staff_id = request.POST.get("staff_id")
    employee_id = request.POST.get("employee_id")
    
    try:
        staff = Staffs.objects.get(admin_id=staff_id)
        
        # Check if the employee ID is already in use
        if Staffs.objects.filter(employee_id=employee_id).exclude(admin_id=staff_id).exists():
            return JsonResponse({"status": "error", "message": "Employee ID already exists"}, status=400)
        
        staff.employee_id = employee_id
        staff.save()
        
        return JsonResponse({"status": "success", "message": "Employee ID updated successfully"})
    except Staffs.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Staff not found"}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@csrf_exempt
def get_course_sessions(request):
    """
    View function to handle AJAX request for getting course sessions.
    """
    if request.method != "POST":
        return HttpResponse("Method Not Allowed")
    
    course_id = request.POST.get("course_id")
    session_id = request.POST.get("session_id")
    
    try:
        course = Courses.objects.get(id=course_id)
        
        # If session_id is provided, check if the specific course-session combination exists
        if session_id:
            session = SessionYearModel.objects.get(id=session_id)
            exists = CourseSession.objects.filter(course=course, session_year=session).exists()
            return JsonResponse({
                "exists": exists,
                "course_name": course.course_name,
                "session_name": f"{session.start_year} - {session.end_year}"
            })
        
        # Otherwise return all sessions for this course
        course_sessions = CourseSession.objects.filter(course=course)
        
        sessions_data = []
        for cs in course_sessions:
            sessions_data.append({
                'id': cs.id,
                'session_name': f"{cs.session_year.start_year} - {cs.session_year.end_year}"
            })
        
        return JsonResponse({"course_sessions": sessions_data})
    except Courses.DoesNotExist:
        return JsonResponse({"error": "Course not found"}, status=404)
    except SessionYearModel.DoesNotExist:
        return JsonResponse({"error": "Session not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def delete_subject(request, subject_id):
    """
    View function to delete a subject.
    """
    try:
        subject = Subjects.objects.get(id=subject_id)
        subject.delete()
        messages.success(request, "Subject deleted successfully!")
        return redirect('manage_subject')
    except Subjects.DoesNotExist:
        messages.error(request, "Subject does not exist")
        return redirect('manage_subject')
    except Exception as e:
        messages.error(request, f"Error occurred while deleting subject: {str(e)}")
        return redirect('manage_subject')

def manage_class(request):
    """
    View function to display and manage classes.
    """
    classes = Class.objects.all()
    courses = Courses.objects.all()
    sessions = SessionYearModel.objects.all()
    staffs = Staffs.objects.all()
    return render(request, "hod_template/manage_class_template.html", {
        "classes": classes,
        "courses": courses,
        "sessions": sessions,
        "staffs": staffs
    })

def add_class_save(request):
    """
    View function to save a new class from the add_class form.
    This function only processes the POST request and should not be accessed directly.
    """
    if request.method != "POST":
        messages.error(request, "Invalid method")
        return redirect('manage_class')
    
    course_id = request.POST.get("course")
    session_id = request.POST.get("session")
    section = request.POST.get("section")
    
    if not course_id or not session_id or not section:
        messages.error(request, "Please provide all required fields")
        return redirect('manage_class')
    
    try:
        course = Courses.objects.get(id=course_id)
        session = SessionYearModel.objects.get(id=session_id)
        
        # Get or create the course session
        course_session, created = CourseSession.objects.get_or_create(
            course=course,
            session_year=session
        )
        
        # Check if class with same course session and section already exists
        if Class.objects.filter(course_session=course_session, section=section).exists():
            messages.error(request, "Class with this course, session, and section already exists")
            return redirect('manage_class')
        
        class_obj = Class(
            course_session=course_session,
            section=section
        )
        class_obj.save()
        
        messages.success(request, "Class added successfully!")
        return redirect('manage_class')
        
    except Courses.DoesNotExist:
        messages.error(request, "Course does not exist")
    except SessionYearModel.DoesNotExist:
        messages.error(request, "Session year does not exist")
    except Exception as e:
        messages.error(request, f"Failed to add class: {str(e)}")
    
    return redirect('manage_class')

@csrf_exempt
def get_subjects_by_course_session(request):
    """
    View function to handle AJAX request for getting subjects based on course session.
    """
    if request.method != "POST":
        return HttpResponse("Method Not Allowed")
    
    course_session_id = request.POST.get("course_session_id")
    
    try:
        course_session = CourseSession.objects.get(id=course_session_id)
        subjects = Subjects.objects.filter(course_session=course_session)
        
        subjects_data = []
        for subject in subjects:
            staff_name = f"{subject.staff_id.first_name} {subject.staff_id.last_name}" if subject.staff_id else "Not Assigned"
            subjects_data.append({
                'id': subject.id,
                'name': subject.subject_name,
                'staff': staff_name
            })
        
        return JsonResponse({"subjects": subjects_data})
    except CourseSession.DoesNotExist:
        return JsonResponse({"error": "Course session not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def get_subjects_by_class(request):
    """
    View function to handle AJAX request for getting subjects assigned to a class
    and available subjects that can be assigned.
    """
    if request.method != "POST":
        return HttpResponse("Method Not Allowed")
    
    class_id = request.POST.get("class_id")
    
    try:
        class_obj = Class.objects.get(id=class_id)
        # Get all subjects for this course session
        course_session = class_obj.course_session
        all_subjects = Subjects.objects.filter(course_session=course_session)
        
        # Get subjects already assigned to this class
        class_subjects = ClassSubject.objects.filter(class_id=class_obj)
        assigned_subject_ids = class_subjects.values_list('subject_id', flat=True)
        
        subjects_data = []
        
        # First add assigned subjects
        for cs in class_subjects:
            staff_name = f"{cs.staff.admin.first_name} {cs.staff.admin.last_name}" if cs.staff else "Not Assigned"
            subjects_data.append({
                'id': cs.subject.id,
                'subject_name': cs.subject.subject_name,
                'staff_name': staff_name,
                'staff_id': cs.staff.id if cs.staff else None,
                'is_assigned': True,
                'class_subject_id': cs.id
            })
        
        # Then add unassigned subjects
        for subject in all_subjects.exclude(id__in=assigned_subject_ids):
            subjects_data.append({
                'id': subject.id,
                'subject_name': subject.subject_name,
                'staff_name': None,
                'staff_id': None,
                'is_assigned': False,
                'class_subject_id': None
            })
        
        return JsonResponse({"subjects": subjects_data})
    except Class.DoesNotExist:
        return JsonResponse({"error": "Class not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def get_assigned_subjects(request):
    """
    View function to handle AJAX request for getting subjects assigned to a staff.
    """
    if request.method != "POST":
        return HttpResponse("Method Not Allowed")
    
    staff_id = request.POST.get("staff_id")
    
    try:
        staff = Staffs.objects.get(id=staff_id)
        class_subjects = ClassSubject.objects.filter(staff=staff)
        
        subjects_data = []
        for cs in class_subjects:
            subjects_data.append({
                'id': cs.id,
                'subject_name': cs.subject.subject_name,
                'class_name': cs.class_id.class_name
            })
        
        return JsonResponse({"subjects": subjects_data})
    except Staffs.DoesNotExist:
        return JsonResponse({"error": "Staff not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def assign_subject_to_class(request):
    """
    View function to handle assigning a subject to a class with a staff.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method Not Allowed"}, status=405)
    
    class_id = request.POST.get("class_id")
    subject_id = request.POST.get("subject_id")
    staff_id = request.POST.get("staff_id")
    
    if not class_id or not subject_id or not staff_id:
        return JsonResponse({"status": "error", "message": "Missing required fields"}, status=400)
    
    try:
        class_obj = Class.objects.get(id=class_id)
        subject = Subjects.objects.get(id=subject_id)
        staff = Staffs.objects.get(id=staff_id)
        
        # Check if subject is already assigned to the class
        if ClassSubject.objects.filter(class_id=class_obj, subject=subject).exists():
            return JsonResponse({"status": "error", "message": "Subject is already assigned to this class"}, status=400)
        
        # Create the class subject
        class_subject = ClassSubject(
            class_id=class_obj,
            subject=subject,
            staff=staff
        )
        class_subject.save()
        
        return JsonResponse({
            "status": "success",
            "message": "Subject assigned successfully",
            "id": class_subject.id,
            "subject_name": subject.subject_name,
            "staff_name": f"{staff.admin.first_name} {staff.admin.last_name}",
            "staff_id": staff.id
        })
    except Class.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Class not found"}, status=404)
    except Subjects.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Subject not found"}, status=404)
    except Staffs.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Staff not found"}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@csrf_exempt
def update_subject_staff(request):
    """
    View function to handle updating the staff assigned to a class subject.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method Not Allowed"}, status=405)
    
    class_subject_id = request.POST.get("class_subject_id")
    staff_id = request.POST.get("staff_id")
    
    if not class_subject_id or not staff_id:
        return JsonResponse({"status": "error", "message": "Missing required fields"}, status=400)
    
    try:
        class_subject = ClassSubject.objects.get(id=class_subject_id)
        staff = Staffs.objects.get(id=staff_id)
        
        # Update the staff
        class_subject.staff = staff
        class_subject.save()
        
        return JsonResponse({
            "status": "success",
            "message": "Staff updated successfully",
            "staff_name": f"{staff.admin.first_name} {staff.admin.last_name}",
            "staff_id": staff.id
        })
    except ClassSubject.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Class subject not found"}, status=404)
    except Staffs.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Staff not found"}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@csrf_exempt
def remove_subject_from_class(request):
    """
    View function to handle removing a subject from a class.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method Not Allowed"}, status=405)
    
    class_subject_id = request.POST.get("class_subject_id")
    
    if not class_subject_id:
        return JsonResponse({"status": "error", "message": "Missing required fields"}, status=400)
    
    try:
        class_subject = ClassSubject.objects.get(id=class_subject_id)
        
        # Delete the class subject
        class_subject.delete()
        
        return JsonResponse({
            "status": "success",
            "message": "Subject removed from class successfully"
        })
    except ClassSubject.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Class subject not found"}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@csrf_exempt
def add_students_to_class(request):
    """
    View function to handle AJAX request for adding students to a class.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method Not Allowed"}, status=405)
    
    class_id = request.POST.get("class_id")
    
    # Handle student_ids which can be sent as either a comma-separated string or as an array
    student_ids_raw = request.POST.get("student_ids", "")
    
    # Check if it's a list from getlist or a comma-separated string
    if not student_ids_raw:
        student_ids = request.POST.getlist("student_ids[]")
    else:
        # If it's a string, split it (handles both comma-separated and single values)
        student_ids = student_ids_raw.split(",") if "," in student_ids_raw else [student_ids_raw]
    
    if not class_id or not student_ids:
        return JsonResponse({"error": "Missing required fields"}, status=400)
    
    try:
        class_obj = Class.objects.get(id=class_id)
        
        added_students = []
        for student_id in student_ids:
            try:
                student = Students.objects.get(id=student_id)
                
                # Create StudentClass association
                StudentClass.objects.create(
                    student=student,
                    class_id=class_obj
                )
                
                added_students.append({
                    "id": student.id,
                    "name": student.admin.first_name + " " + student.admin.last_name,
                    "registration_number": student.registration_number
                })
            except Students.DoesNotExist:
                pass  # Skip non-existent students
            except IntegrityError:
                # Skip if the student is already in the class (unique_together constraint)
                pass
        
        return JsonResponse({
            "status": "success",
            "message": f"{len(added_students)} students added to class successfully",
            "students": added_students
        })
    except Class.DoesNotExist:
        return JsonResponse({"error": "Class not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def remove_student_from_class(request, class_id, student_id):
    """
    View function to handle removing a student from a class.
    """
    try:
        class_obj = Class.objects.get(id=class_id)
        student = Students.objects.get(id=student_id)
        
        # Update the student's class to None
        student.class_id = None
        student.save()
        
        messages.success(request, f"Student {student.admin.first_name} {student.admin.last_name} removed from class successfully")
        return redirect('manage_class')
    except Class.DoesNotExist:
        messages.error(request, "Class not found")
        return redirect('manage_class')
    except Students.DoesNotExist:
        messages.error(request, "Student not found")
        return redirect('manage_class')
    except Exception as e:
        messages.error(request, f"Error removing student: {str(e)}")
        return redirect('manage_class')

@csrf_exempt
def remove_student_ajax(request):
    """
    View function to handle AJAX request for removing a student from a class.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method Not Allowed"}, status=405)
    
    class_id = request.POST.get("class_id")
    student_id = request.POST.get("student_id")
    
    if not class_id or not student_id:
        return JsonResponse({"status": "error", "message": "Missing required fields"}, status=400)
    
    try:
        class_obj = Class.objects.get(id=class_id)
        student = Students.objects.get(id=student_id)
        
        # Delete the StudentClass association instead of setting class_id to None
        student_class = StudentClass.objects.get(student=student, class_id=class_obj)
        student_class.delete()
        
        return JsonResponse({
            "status": "success",
            "message": f"Student {student.admin.first_name} {student.admin.last_name} removed from class successfully"
        })
    except Class.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Class not found"}, status=404)
    except Students.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Student not found"}, status=404)
    except StudentClass.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Student is not in this class"}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

def delete_class(request, class_id):
    """
    View function to handle deleting a class.
    """
    try:
        class_obj = Class.objects.get(id=class_id)
        
        # Get the class name before deleting for the success message
        class_name = class_obj.class_name
        
        # Delete the class
        class_obj.delete()
        
        messages.success(request, f"Class {class_name} deleted successfully")
        return redirect('manage_class')
    except Class.DoesNotExist:
        messages.error(request, "Class not found")
        return redirect('manage_class')
    except Exception as e:
        messages.error(request, f"Error deleting class: {str(e)}")
        return redirect('manage_class')

@csrf_exempt
def get_class_students(request):
    """
    View function to handle AJAX request for getting students in a class.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method Not Allowed"}, status=405)
    
    class_id = request.POST.get("class_id")
    
    if not class_id:
        return JsonResponse({"error": "Missing class ID"}, status=400)
    
    try:
        class_obj = Class.objects.get(id=class_id)
        # Get students in this class using StudentClass model
        student_classes = StudentClass.objects.filter(class_id=class_obj)
        
        students_data = []
        for student_class in student_classes:
            student = student_class.student
            students_data.append({
                "id": student.id,
                "name": student.admin.first_name + " " + student.admin.last_name,
                "registration_number": student.registration_number,
                "email": student.admin.email,
                "gender": student.gender,
                "address": student.address,
                "parents_email": student.parents_email
            })
        
        return JsonResponse({"students": students_data})
    except Class.DoesNotExist:
        return JsonResponse({"error": "Class not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def get_available_students(request):
    """
    View function to handle AJAX request for getting students not assigned to any class
    for a specific course session.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method Not Allowed"}, status=405)
    
    course_session_id = request.POST.get("course_session_id")
    
    if not course_session_id:
        return JsonResponse({"error": "Missing course session ID"}, status=400)
    
    try:
        # Get the course session
        course_session = CourseSession.objects.get(id=course_session_id)
        
        # Get all students for this course and session
        students = Students.objects.filter(
            course_id=course_session.course,
            session_year_id=course_session.session_year
        )
        
        # Get IDs of students already assigned to a class in this course session
        classes = Class.objects.filter(course_session=course_session)
        assigned_student_ids = StudentClass.objects.filter(
            class_id__in=classes
        ).values_list('student_id', flat=True)
        
        # Filter out students already assigned to classes
        available_students = students.exclude(id__in=assigned_student_ids)
        
        # Prepare data for response
        students_data = []
        for student in available_students:
            students_data.append({
                "id": student.id,
                "name": student.admin.first_name + " " + student.admin.last_name,
                "registration_number": student.registration_number
            })
        
        return JsonResponse({"students": students_data})
    
    except CourseSession.DoesNotExist:
        return JsonResponse({"error": "Course session not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def get_students_by_range(request):
    """
    View function to handle AJAX request for getting students within a specified registration number range.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method Not Allowed"}, status=405)
    
    start_reg = request.POST.get("start_reg")
    end_reg = request.POST.get("end_reg")
    
    if not start_reg or not end_reg:
        return JsonResponse({"status": "error", "message": "Missing registration range"}, status=400)
    
    try:
        # Get students within the registration number range
        students = Students.objects.filter(
            registration_number__gte=start_reg,
            registration_number__lte=end_reg
        )
        
        students_data = []
        for student in students:
            students_data.append({
                "id": student.id,
                "name": f"{student.admin.first_name} {student.admin.last_name}",
                "registration_number": student.registration_number
            })
        
        return JsonResponse({"students": students_data})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def delete_student(request, student_id):
    """
    View function to delete a student and their associated user account.
    """
    try:
        student = Students.objects.get(admin=student_id)
        user = student.admin
        student_id_value = student.id
        email = user.email
        
        # Store the deleted ID for future reuse
        DeletedStudentID.objects.create(deleted_id=student_id_value)
        
        # Delete the student profile first
        student.delete()
        
        # Explicitly nullify email before deletion to avoid integrity constraints
        # This helps ensure the email can be reused
        user.email = f"deleted_{user.email}_{timezone.now().strftime('%Y%m%d%H%M%S')}"
        user.save(update_fields=['email'])
        
        # Then delete the user account
        user.delete()
        
        messages.success(request, f"Student deleted successfully. Email address {email} is now available for reuse.")
    except Students.DoesNotExist:
        messages.error(request, "Student not found")
    except Exception as e:
        messages.error(request, f"Error deleting student: {str(e)}")
    
    return redirect('manage_student')

@csrf_exempt
def get_available_students(request):
    """
    View function to handle AJAX request for getting students not assigned to any class.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method Not Allowed"}, status=405)
    
    # Get the course_session_id from the request
    course_session_id = request.POST.get("course_session_id")
    
    if not course_session_id:
        return JsonResponse({"status": "error", "message": "Missing course session ID"}, status=400)
    
    try:
        course_session = CourseSession.objects.get(id=course_session_id)
        
        # Get all students in the same course and session
        students_in_course = Students.objects.filter(
            course_id=course_session.course,
            session_year_id=course_session.session_year
        )
        
        # Get all students already assigned to classes for this course session
        class_ids = Class.objects.filter(course_session=course_session).values_list('id', flat=True)
        assigned_student_ids = StudentClass.objects.filter(class_id__in=class_ids).values_list('student_id', flat=True)
        
        # Filter out students who are already assigned
        available_students = students_in_course.exclude(id__in=assigned_student_ids)
        
        students_data = []
        for student in available_students:
            students_data.append({
                "id": student.id,
                "name": f"{student.admin.first_name} {student.admin.last_name}",
                "registration_number": student.registration_number
            })
        
        return JsonResponse({"students": students_data})
    except CourseSession.DoesNotExist:
        return JsonResponse({"error": "Course session not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def get_students_by_range(request):
    """
    View function to handle AJAX request for getting students within a specified registration number range.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method Not Allowed"}, status=405)
    
    start_reg = request.POST.get("start_reg")
    end_reg = request.POST.get("end_reg")
    
    if not start_reg or not end_reg:
        return JsonResponse({"status": "error", "message": "Missing registration range"}, status=400)
    
    try:
        # Get students within the registration number range
        students = Students.objects.filter(
            registration_number__gte=start_reg,
            registration_number__lte=end_reg
        )
        
        students_data = []
        for student in students:
            students_data.append({
                "id": student.id,
                "name": f"{student.admin.first_name} {student.admin.last_name}",
                "registration_number": student.registration_number
            })
        
        return JsonResponse({"students": students_data})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def add_session_save(request):
    """
    View function to handle saving a new session year.
    """
    if request.method != "POST":
        messages.error(request, "Invalid Method")
        return redirect('add_session')
    
    start_year = request.POST.get('session_start')
    end_year = request.POST.get('session_end')
    
    try:
        if not start_year or not end_year:
            messages.error(request, "Please provide both start and end years")
            return redirect('add_session')
        
        if int(start_year) >= int(end_year):
            messages.error(request, "End year should be greater than start year")
            return redirect('add_session')
        
        # Check if session already exists
        if SessionYearModel.objects.filter(start_year=start_year, end_year=end_year).exists():
            messages.error(request, "Session year already exists")
            return redirect('add_session')
        
        session_year = SessionYearModel(
            start_year=start_year,
            end_year=end_year
        )
        session_year.save()
        
        messages.success(request, "Session year added successfully")
        return redirect('manage_session')
    except Exception as e:
        messages.error(request, f"Failed to add session year: {str(e)}")
        return redirect('add_session')


@csrf_exempt
def admin_get_attendance_dates(request):
    """
    View function to handle AJAX request for getting attendance dates.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method Not Allowed"}, status=405)
    
    class_subject_id = request.POST.get("class_subject_id")
    
    if not class_subject_id:
        return JsonResponse({"status": "error", "message": "Missing class subject ID"}, status=400)
    
    try:
        class_subject = ClassSubject.objects.get(id=class_subject_id)
        attendance_records = Attendance.objects.filter(class_subject=class_subject)
        
        dates = []
        for attendance in attendance_records:
            dates.append({
                "id": attendance.id,
                "date": attendance.attendance_date.strftime("%Y-%m-%d"),
                "is_locked": attendance.is_locked
            })
        
        return JsonResponse({"attendance_dates": dates})
    except ClassSubject.DoesNotExist:
        return JsonResponse({"error": "Class subject not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500) 

@csrf_exempt
def admin_get_attendance_student(request):
    """
    View function to handle AJAX request for getting student attendance data.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method Not Allowed"}, status=405)
    
    attendance_id = request.POST.get("attendance_id")
    
    if not attendance_id:
        return JsonResponse({"status": "error", "message": "Missing attendance ID"}, status=400)
    
    try:
        attendance = Attendance.objects.get(id=attendance_id)
        attendance_reports = AttendanceReport.objects.filter(attendance=attendance)
        
        student_data = []
        for report in attendance_reports:
            student_data.append({
                "id": report.id,
                "student_id": report.student.id,
                "name": f"{report.student.admin.first_name} {report.student.admin.last_name}",
                "status": report.status,
                "registration_number": report.student.registration_number
            })
        
        return JsonResponse({
            "students": student_data,
            "date": attendance.attendance_date.strftime("%Y-%m-%d"),
            "is_locked": attendance.is_locked
        })
    except Attendance.DoesNotExist:
        return JsonResponse({"error": "Attendance record not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500) 

@csrf_exempt
def get_classes_by_session(request):
    """
    View function to handle AJAX request for getting classes by session year.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method Not Allowed"}, status=405)
    
    # Accept either session_year_id or session_id for flexibility
    session_year_id = request.POST.get("session_year_id") or request.POST.get("session_id")
    
    if not session_year_id:
        return JsonResponse({"status": "error", "message": "Missing session year ID"}, status=400)
    
    try:
        session_year = SessionYearModel.objects.get(id=session_year_id)
        classes = Class.objects.filter(course_session__session_year=session_year)
        
        classes_data = []
        for class_obj in classes:
            classes_data.append({
                "id": class_obj.id,
                "name": class_obj.class_name,
                "course_name": class_obj.course_session.course.course_name,
                "section": class_obj.section
            })
        
        return JsonResponse({"classes": classes_data})
    except SessionYearModel.DoesNotExist:
        return JsonResponse({"error": "Session year not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def admin_change_password(request):
    """
    View function to display admin change password form.
    """
    return render(request, "hod_template/admin_change_password.html")

def admin_change_password_save(request):
    """
    View function to process admin change password form.
    """
    if request.method != "POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    
    old_password = request.POST.get("old_password")
    new_password = request.POST.get("new_password")
    confirm_password = request.POST.get("confirm_password")
    
    if not old_password or not new_password or not confirm_password:
        messages.error(request, "Please provide all fields")
        return redirect('admin_change_password')
    
    if new_password != confirm_password:
        messages.error(request, "New password and confirm password do not match")
        return redirect('admin_change_password')
    
    user = CustomUser.objects.get(id=request.user.id)
    if not user.check_password(old_password):
        messages.error(request, "Old password is incorrect")
        return redirect('admin_change_password')
    
    user.set_password(new_password)
    user.save()
    
    messages.success(request, "Password changed successfully! Please login again with your new password")
    return redirect('logout')

def admin_profile(request):
    """
    View function to display admin profile form.
    """
    user = CustomUser.objects.get(id=request.user.id)
    return render(request, "hod_template/admin_profile.html", {"user": user})

def admin_profile_save(request):
    """
    View function to process admin profile form.
    """
    if request.method != "POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    
    first_name = request.POST.get("first_name")
    last_name = request.POST.get("last_name")
    
    try:
        user = CustomUser.objects.get(id=request.user.id)
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        
        messages.success(request, "Profile updated successfully!")
        return redirect('admin_profile')
    except Exception as e:
        messages.error(request, f"Failed to update profile: {str(e)}")
        return redirect('admin_profile')

def debug_settings(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    if not request.user.is_superuser:
        messages.error(request, "Access Denied! You don't have permission to access this page.")
        return redirect('admin_home')
    
    # Get error logs
    error_logs = ErrorLog.objects.all().order_by('-timestamp')[:1000]  # Get last 1000 logs
    
    context = {
        'error_logs': error_logs,
    }
    
    return render(request, 'hod_template/debug_settings_template.html', context)

def save_debug_settings(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    if not request.user.is_superuser:
        messages.error(request, "Access Denied! You don't have permission to access this page.")
        return redirect('admin_home')
    
    messages.error(request, "Direct editing of environment settings has been disabled for security reasons.")
    return redirect('debug_settings')

# No longer allow updating environment settings
def update_environment_settings(debug, domain_name, email_host_user, email_host_password):
    """Helper function that has been deprecated for security reasons"""
    # This function intentionally does nothing now
    pass

def log_error(request=None, level='ERROR', location='', description='', stack_trace=None, additional_data=None):
    """Helper function to log errors"""
    try:
        error_log = ErrorLog(
            level=level,
            location=location,
            description=description,
            stack_trace=stack_trace,
            additional_data=additional_data,
            user=request.user if request and request.user.is_authenticated else None,
            ip_address=request.META.get('REMOTE_ADDR') if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT') if request else None
        )
        error_log.save()
        return error_log
    except Exception as e:
        # If we can't log to the database, log to console
        print(f"Failed to log error: {str(e)}")
        print(f"Original error: {description}")
        return None

def attendance_edit_requests(request):
    """
    View function to display all attendance edit requests.
    """
    edit_requests = AttendanceEditRequest.objects.all().order_by('-created_at')
    return render(request, "hod_template/attendance_edit_requests.html", {"edit_requests": edit_requests})

def approve_attendance_edit(request, request_id):
    """
    View function to approve an attendance edit request.
    """
    try:
        edit_request = AttendanceEditRequest.objects.get(id=request_id)
        
        # Update the status to approved
        edit_request.status = 'approved'
        edit_request.save()
        
        # Unlock the attendance for editing
        attendance = edit_request.attendance
        attendance.is_locked = False
        attendance.save()
        
        messages.success(request, "Attendance edit request approved successfully")
        return redirect('attendance_edit_requests')
    except AttendanceEditRequest.DoesNotExist:
        messages.error(request, "Edit request not found")
        return redirect('attendance_edit_requests')
    except Exception as e:
        messages.error(request, f"Error approving edit request: {str(e)}")
        return redirect('attendance_edit_requests')

def reject_attendance_edit(request, request_id):
    """
    View function to reject an attendance edit request.
    """
    try:
        edit_request = AttendanceEditRequest.objects.get(id=request_id)
        
        # Update the status to rejected
        edit_request.status = 'rejected'
        edit_request.save()
        
        messages.success(request, "Attendance edit request rejected")
        return redirect('attendance_edit_requests')
    except AttendanceEditRequest.DoesNotExist:
        messages.error(request, "Edit request not found")
        return redirect('attendance_edit_requests')
    except Exception as e:
        messages.error(request, f"Error rejecting edit request: {str(e)}")
        return redirect('attendance_edit_requests')

@csrf_exempt
def get_class_details(request):
    """
    View function to handle AJAX request for getting class details.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method Not Allowed"}, status=405)
    
    class_id = request.POST.get("class_id")
    
    if not class_id:
        return JsonResponse({"status": "error", "message": "Missing class ID"}, status=400)
    
    try:
        class_obj = Class.objects.get(id=class_id)
        
        return JsonResponse({
            "id": class_obj.id,
            "course_session_id": class_obj.course_session.id,
            "course_id": class_obj.course_session.course.id,
            "session_year_id": class_obj.course_session.session_year.id,
            "section": class_obj.section,
            "class_name": class_obj.class_name
        })
    except Class.DoesNotExist:
        return JsonResponse({"error": "Class not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def manage_admin(request):
    """
    View function to manage admin users.
    Only accessible by admin users.
    """
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, "You don't have permission to access this page")
        return HttpResponseRedirect(reverse("show_login"))
    
    admins = CustomUser.objects.filter(user_type=1)  # 1 is the user type for admin
    return render(request, 'hod_template/manage_admin_template.html', {'admins': admins})

@login_required
def export_class_students_excel(request, class_id):
    """
    View function to export class students to Excel format.
    """
    if not request.user.user_type == '1':  # Check if user is HOD
        messages.error(request, "Access Denied")
        return redirect('login')
        
    try:
        class_obj = Class.objects.get(id=class_id)
        student_classes = StudentClass.objects.filter(class_id=class_obj).select_related('student', 'student__admin')
        
        if not student_classes.exists():
            messages.error(request, "No students found in this class")
            return redirect('manage_class')
        
        response, error = export_to_excel(student_classes, class_obj)
        if error:
            messages.error(request, error)
            return redirect('manage_class')
            
        return response
        
    except Class.DoesNotExist:
        messages.error(request, "Class not found")
        return redirect('manage_class')
    except Exception as e:
        messages.error(request, f"Error exporting students: {str(e)}")
        return redirect('manage_class')

@login_required
def export_class_students_pdf(request, class_id):
    """
    View function to export class students to PDF format.
    """
    if not request.user.user_type == '1':  # Check if user is HOD
        messages.error(request, "Access Denied")
        return redirect('login')
        
    try:
        class_obj = Class.objects.get(id=class_id)
        student_classes = StudentClass.objects.filter(class_id=class_obj).select_related('student', 'student__admin')
        
        if not student_classes.exists():
            messages.error(request, "No students found in this class")
            return redirect('manage_class')
        
        response, error = export_to_pdf(student_classes, class_obj)
        if error:
            messages.error(request, error)
            return redirect('manage_class')
            
        return response
        
    except Class.DoesNotExist:
        messages.error(request, "Class not found")
        return redirect('manage_class')
    except Exception as e:
        messages.error(request, f"Error exporting students: {str(e)}")
        return redirect('manage_class')

@csrf_exempt
def remove_all_students_from_class(request):
    """
    View function to remove all students from a class.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method Not Allowed"}, status=405)
    
    if not request.user.user_type == '1':  # Check if user is HOD
        return JsonResponse({"error": "Access Denied"}, status=403)
    
    class_id = request.POST.get("class_id")
    if not class_id:
        return JsonResponse({"error": "Class ID is required"}, status=400)
    
    try:
        class_obj = Class.objects.get(id=class_id)
        student_count = StudentClass.objects.filter(class_id=class_obj).count()
        
        if student_count == 0:
            return JsonResponse({"error": "No students found in this class"}, status=404)
        
        # Delete all student-class associations
        StudentClass.objects.filter(class_id=class_obj).delete()
        
        return JsonResponse({
            "success": True,
            "message": f"Successfully removed {student_count} students from the class"
        })
        
    except Class.DoesNotExist:
        return JsonResponse({"error": "Class not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def export_attendance_pdf(request):
    """
    View function to export attendance statistics to PDF
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from django.http import HttpResponse
    import io

    if request.method == 'POST':
        session_id = request.POST.get('session_id')
        class_id = request.POST.get('class_id')
        subject_id = request.POST.get('subject_id')

        try:
            # Get the class subject and related data
            class_subject = ClassSubject.objects.get(class_id=class_id, subject_id=subject_id)
            session = SessionYearModel.objects.get(id=session_id)
            class_obj = Class.objects.get(id=class_id)
            subject = Subjects.objects.get(id=subject_id)
            
            # Get faculty name
            faculty_name = "Not Assigned"
            if class_subject.staff:
                faculty_name = f"{class_subject.staff.admin.first_name} {class_subject.staff.admin.last_name}"

            # Get attendance records
            attendance_records = Attendance.objects.filter(class_subject=class_subject)
            total_classes = attendance_records.count()

            # Get students attendance data
            students = StudentClass.objects.filter(class_id=class_id)
            attendance_data = []

            for student_class in students:
                student = student_class.student
                present_count = AttendanceReport.objects.filter(
                    student=student,
                    attendance__class_subject=class_subject,
                    status=True
                ).count()

                absent_count = total_classes - present_count
                attendance_percentage = (present_count / total_classes * 100) if total_classes > 0 else 0

                attendance_data.append([
                    f"{student.admin.first_name} {student.admin.last_name}",
                    student.registration_number,
                    str(total_classes),
                    str(present_count),
                    str(absent_count),
                    f"{round(attendance_percentage, 1)}%"
                ])

            # Create the PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
            elements = []

            # Add title and details
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30
            )
            
            elements.append(Paragraph("Attendance Statistics Report", title_style))
            
            # Add session, class, subject details
            detail_style = ParagraphStyle(
                'Details',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=12
            )
            
            elements.append(Paragraph(f"Session: {session.start_year} - {session.end_year}", detail_style))
            elements.append(Paragraph(f"Class: {class_obj.course_session.course.course_name} - {class_obj.section}", detail_style))
            elements.append(Paragraph(f"Subject: {subject.subject_name}", detail_style))
            elements.append(Paragraph(f"Faculty: {faculty_name}", detail_style))
            elements.append(Paragraph(f"Total Classes: {total_classes}", detail_style))
            elements.append(Paragraph(f"Total Students: {len(attendance_data)}", detail_style))
            
            elements.append(Spacer(1, 20))

            # Create table
            table_data = [['Student Name', 'Registration Number', 'Total Classes', 'Classes Attended', 'Classes Absent', 'Attendance %']]
            table_data.extend(attendance_data)
            
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(table)

            # Build PDF
            doc.build(elements)
            buffer.seek(0)
            
            # Create the HTTP response
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="attendance_report_{subject.subject_name}.pdf"'
            response.write(buffer.getvalue())
            buffer.close()
            
            return response

        except Exception as e:
            messages.error(request, f"Error generating PDF: {str(e)}")
            return redirect('admin_view_attendance')

    return redirect('admin_view_attendance')

@csrf_exempt
def get_terminal_output(request):
    """
    View function to retrieve recent terminal output for debugging.
    This reads from system logs rather than modifying any environment variables.
    """
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({"error": "Access denied"}, status=403)
    
    try:
        # Get the last 100 lines from application log file
        import os
        import subprocess
        
        log_file = os.path.join(settings.BASE_DIR, 'logs', 'app.log')
        if not os.path.exists(log_file):
            # If app.log doesn't exist, try to get Django server output
            result = subprocess.run(['tail', '-n', '100', '/var/log/django.log'], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                # If Django log doesn't exist, return message
                return JsonResponse({"output": "No log files found. Check server configuration."})
            output = result.stdout.decode('utf-8')
        else:
            # Read from app.log
            result = subprocess.run(['tail', '-n', '100', log_file], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = result.stdout.decode('utf-8')
        
        # Filter out sensitive information (e.g., passwords, tokens)
        import re
        output = re.sub(r'password[s]?\s*[=:]\s*\S+', 'password=*****', output, flags=re.IGNORECASE)
        output = re.sub(r'token[s]?\s*[=:]\s*\S+', 'token=*****', output, flags=re.IGNORECASE)
        output = re.sub(r'secret[s]?\s*[=:]\s*\S+', 'secret=*****', output, flags=re.IGNORECASE)
        
        return JsonResponse({"output": output})
    except Exception as e:
        return JsonResponse({"output": f"Error reading logs: {str(e)}"})
