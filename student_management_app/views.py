import datetime
import json
import os
import random
import logging
import pytz

import requests
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, HttpResponseRedirect, Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django import forms
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.utils import timezone

from student_management_app.EmailBackEnd import EmailBackEnd
from student_management_app.models import CustomUser, Courses, SessionYearModel, Staffs, Subjects, Students, CourseSession, SystemSettings, AdminHOD
from student_management_system import settings
from student_management_app.utils import send_email, log_user_activity, send_activation_email, send_admin_notification_email, generate_random_password, send_account_credentials_email
from student_management_app.email_utils import is_activation_token_valid, generate_activation_token

def showLoginPage(request):
    # Generate two random numbers between 1 and 10 for the captcha
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    
    # Get system settings for signup options
    from student_management_app.models import SystemSettings
    
    # Default all to False if settings don't exist
    enable_admin_signup = False
    enable_staff_signup = False
    enable_student_signup = False
    
    # Get settings from database if they exist
    try:
        admin_signup = SystemSettings.objects.get(setting_key='enable_admin_signup')
        enable_admin_signup = admin_signup.setting_value == 'True'
    except SystemSettings.DoesNotExist:
        pass
    
    try:
        staff_signup = SystemSettings.objects.get(setting_key='enable_staff_signup')
        enable_staff_signup = staff_signup.setting_value == 'True'
    except SystemSettings.DoesNotExist:
        pass
    
    try:
        student_signup = SystemSettings.objects.get(setting_key='enable_student_signup')
        enable_student_signup = student_signup.setting_value == 'True'
    except SystemSettings.DoesNotExist:
        pass
    
    context = {
        "captcha_num1": num1, 
        "captcha_num2": num2,
        "enable_admin_signup": enable_admin_signup,
        "enable_staff_signup": enable_staff_signup,
        "enable_student_signup": enable_student_signup
    }
    
    return render(request, "login_page.html", context)

def doLogin(request):
    if request.method!="POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        # Get client IP for logging
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        # Get user agent for logging
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        try:
            # Verify the captcha
            captcha_answer = request.POST.get("captcha_answer")
            num1 = int(request.POST.get("captcha_num1"))
            num2 = int(request.POST.get("captcha_num2"))
            
            if not captcha_answer or int(captcha_answer) != (num1 + num2):
                messages.error(request, "Invalid Captcha. Please try again.")
                
                # Log failed captcha attempt
                email = request.POST.get("email")
                try:
                    user = CustomUser.objects.get(email=email)
                    log_user_activity(
                        user=user,
                        action='failed_login',
                        ip_address=ip,
                        user_agent=user_agent,
                        target_detail="Invalid captcha",
                        extra_data={'reason': 'Invalid captcha'}
                    )
                except CustomUser.DoesNotExist:
                    # Anonymous user with invalid captcha
                    pass
                    
                return HttpResponseRedirect("/")

        except Exception as e:
            messages.error(request, "Error validating captcha. Please try again.")
            return HttpResponseRedirect("/")

        email = request.POST.get("email")
        password = request.POST.get("password")
        user = EmailBackEnd.authenticate(request, username=email, password=password)
        
        if user != None:
            login(request, user)
            
            # Log successful login
            log_user_activity(
                user=user,
                action='login',
                ip_address=ip,
                user_agent=user_agent,
                target_detail=f"User type: {user.user_type}"
            )
            
            if user.user_type=="1":
                return HttpResponseRedirect('/admin_home')
            elif user.user_type=="2":
                return HttpResponseRedirect(reverse("staff_profile"))
            else:
                return HttpResponseRedirect(reverse("student_profile"))
        else:
            # Log failed login attempt
            try:
                # If user exists but password is wrong
                user_obj = CustomUser.objects.get(email=email)
                log_user_activity(
                    user=user_obj,
                    action='failed_login',
                    ip_address=ip,
                    user_agent=user_agent,
                    target_detail="Invalid credentials",
                    extra_data={'reason': 'Invalid password'}
                )
            except CustomUser.DoesNotExist:
                # If user doesn't exist, we can't log against a user
                pass
                
            messages.error(request, "Invalid Email or Password")
            return HttpResponseRedirect("/")

def GetUserDetails(request):
    if request.user!=None:
        return HttpResponse("User : "+request.user.email+" usertype : "+str(request.user.user_type))
    else:
        return HttpResponse("Please Login First")

def logout_user(request):
    # Log the logout activity before the user is logged out
    if request.user.is_authenticated:
        # Get client IP for logging
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        # Get user agent for logging
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Log the logout
        log_user_activity(
            user=request.user,
            action='logout',
            ip_address=ip,
            user_agent=user_agent,
            target_detail=f"User type: {request.user.user_type}"
        )
    
    logout(request)
    return HttpResponseRedirect("/")

def showFirebaseJS(request):
    data='importScripts("https://www.gstatic.com/firebasejs/7.14.6/firebase-app.js");' \
         'importScripts("https://www.gstatic.com/firebasejs/7.14.6/firebase-messaging.js"); ' \
         'var firebaseConfig = {' \
         '        apiKey: "YOUR_API_KEY",' \
         '        authDomain: "FIREBASE_AUTH_URL",' \
         '        databaseURL: "FIREBASE_DATABASE_URL",' \
         '        projectId: "FIREBASE_PROJECT_ID",' \
         '        storageBucket: "FIREBASE_STORAGE_BUCKET_URL",' \
         '        messagingSenderId: "FIREBASE_SENDER_ID",' \
         '        appId: "FIREBASE_APP_ID",' \
         '        measurementId: "FIREBASE_MEASUREMENT_ID"' \
         ' };' \
         'firebase.initializeApp(firebaseConfig);' \
         'const messaging=firebase.messaging();' \
         'messaging.setBackgroundMessageHandler(function (payload) {' \
         '    console.log(payload);' \
         '    const notification=JSON.parse(payload);' \
         '    const notificationOption={' \
         '        body:notification.body,' \
         '        icon:notification.icon' \
         '    };' \
         '    return self.registration.showNotification(payload.notification.title,notificationOption);' \
         '});'

    return HttpResponse(data,content_type="text/javascript")

def signup_admin(request):
    # Check if user is authenticated and is a superuser
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, "You don't have permission to access this page")
        return HttpResponseRedirect(reverse("show_login"))
    
    # Get all admin accounts to display
    admins = AdminHOD.objects.all().order_by('-created_at')
    
    return render(request, "signup_admin_page.html", {"admins": admins})

def signup_student(request):
    # Check if student signup is enabled
    from student_management_app.models import SystemSettings
    try:
        setting = SystemSettings.objects.get(setting_key='enable_student_signup')
        if setting.setting_value != 'True':
            # Return 404 if student signup is disabled
            raise Http404("Student signup is disabled")
    except SystemSettings.DoesNotExist:
        # Default to disabled if setting doesn't exist
        raise Http404("Student signup is disabled")
        
    courses = Courses.objects.all()
    session_years = SessionYearModel.objects.all()
    return render(request,"signup_student_page.html", {
        "courses": courses,
        "session_years": session_years,
        "enable_student_signup": True
    })

def signup_staff(request):
    # Check if staff signup is enabled
    from student_management_app.models import SystemSettings
    try:
        setting = SystemSettings.objects.get(setting_key='enable_staff_signup')
        if setting.setting_value != 'True':
            # Return 404 if staff signup is disabled
            raise Http404("Staff signup is disabled")
    except SystemSettings.DoesNotExist:
        # Default to disabled if setting doesn't exist
        raise Http404("Staff signup is disabled")
        
    return render(request,"signup_staff_page.html")

def do_admin_signup(request):
    # Check if user is authenticated and is a superuser
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, "You don't have permission to create admin accounts")
        return HttpResponseRedirect(reverse("show_login"))
    
    username = request.POST.get("username")
    email = request.POST.get("email")
    
    # Generate a random password
    password = generate_random_password()
    
    try:
        # Create admin user (active by default)
        user = CustomUser.objects.create_user(
            username=username,
            password=password,
            email=email,
            user_type=1,
            is_active=True,
            email_verified=True
        )
        user.is_staff = True  # Give staff permissions
        user.is_superuser = True  # Give superuser permissions
        user.save()
        
        # Send credentials email
        send_account_credentials_email(user, password, request)

        # After creating the user, get all admin accounts to refresh the list
        admins = AdminHOD.objects.all().order_by('-created_at')
        messages.success(request, f"Admin account for {email} created successfully! Account credentials have been sent to the email.")
        return render(request, "signup_admin_page.html", {"admins": admins})
    except Exception as e:
        # Log the error for debugging
        print(f"Error creating admin account: {str(e)}")
        messages.error(request, f"Failed to create admin account: {str(e)}")
        return HttpResponseRedirect(reverse("signup_admin"))

def do_staff_signup(request):
    # Check if staff signup is enabled
    from student_management_app.models import SystemSettings
    try:
        setting = SystemSettings.objects.get(setting_key='enable_staff_signup')
        if setting.setting_value != 'True':
            # Return 404 if staff signup is disabled
            raise Http404("Staff signup is disabled")
    except SystemSettings.DoesNotExist:
        # Default to disabled if setting doesn't exist
        raise Http404("Staff signup is disabled")
    
    username = request.POST.get("username")
    email = request.POST.get("email")
    address = request.POST.get("address")

    # Generate a random password
    password = generate_random_password()

    try:
        # Create staff user, active by default
        user = CustomUser.objects.create_user(
            username=username,
            password=password,
            email=email,
            user_type=2,
            is_active=True,  # User is active immediately
            email_verified=True
        )
        user.staffs.address = address
        user.save()
        user.staffs.save()

        # Send credentials email
        send_account_credentials_email(user, password, request)

        messages.success(request, "Successfully Created Staff Account! Account credentials have been sent to the email.")
        return HttpResponseRedirect(reverse("show_login"))
    except Exception as e:
        messages.error(request, f"Failed to Create Staff: {str(e)}")
        return HttpResponseRedirect(reverse("signup_staff"))

def do_signup_student(request):
    # Check if student signup is enabled
    from student_management_app.models import SystemSettings
    try:
        setting = SystemSettings.objects.get(setting_key='enable_student_signup')
        if setting.setting_value != 'True':
            # Return 404 if student signup is disabled
            raise Http404("Student signup is disabled")
    except SystemSettings.DoesNotExist:
        # Default to disabled if setting doesn't exist
        raise Http404("Student signup is disabled")
    
    first_name = request.POST.get("first_name")
    last_name = request.POST.get("last_name")
    username = request.POST.get("username")
    email = request.POST.get("email")
    address = request.POST.get("address")
    session_year_id = request.POST.get("session_year")
    course_id = request.POST.get("course")
    sex = request.POST.get("sex")

    # Generate a random password
    password = generate_random_password()

    try:
        # Handle profile picture
        profile_pic_url = None
        if 'profile_pic' in request.FILES:
            profile_pic = request.FILES['profile_pic']
            fs = FileSystemStorage()
            filename = fs.save(profile_pic.name, profile_pic)
            profile_pic_url = fs.url(filename)

        user = CustomUser.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            user_type=3,
            is_active=True,  # User is active immediately
            email_verified=True
        )
        user.students.address = address
        user.students.session_year_id = SessionYearModel.objects.get(id=session_year_id)
        user.students.course_id = Courses.objects.get(id=course_id)
        user.students.gender = sex
        # Generate registration number
        user.students.registration_number = f"REG{user.id:03d}"
        if profile_pic_url:
            user.students.profile_pic = profile_pic_url
        user.save()
        user.students.save()

        # Send credentials email
        send_account_credentials_email(user, password, request)

        messages.success(request, "Successfully Created Student Account! Account credentials have been sent to the email.")
        return HttpResponseRedirect(reverse("show_login"))
    except Exception as e:
        # If there was an error, delete the user if it was created
        if 'user' in locals():
            user.delete()
        messages.error(request, f"Failed to Add Student: {str(e)}")
        return HttpResponseRedirect(reverse("signup_student"))

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = CustomUser.objects.get(email=email)
            
            # Generate password reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Create password reset URL
            domain = settings.DOMAIN_NAME
            
            if not user.is_active and user.activation_token:
                # This is an inactive account with an activation token, use that path
                reset_url = f"http://{domain}/activate_user/{user.activation_token}/"
            else:
                reset_url = f"http://{domain}/reset-password/{uid}/{token}/"
            
            # Render email template with expiration time
            expiration_minutes = int(os.getenv('PASSWORD_RESET_TIMEOUT', '5'))
            email_template = render_to_string('password_reset_email.html', {
                'user': user,
                'reset_url': reset_url,
                'expiration_minutes': expiration_minutes,
                'is_activation': not user.is_active  # Flag to indicate if this is for initial activation
            })
            
            # Send email using the utility function
            send_email(
                subject='Password Reset Request' if user.is_active else 'Set Your Password',
                body=email_template,
                to_emails=user.email,
                html_content=True
            )
            
            if user.is_active:
                messages.success(request, "Password reset link has been sent to your email")
            else:
                messages.success(request, "Password setup link has been sent to your email. This will also activate your account.")
            return redirect('login')
            
        except CustomUser.DoesNotExist:
            messages.error(request, "No user found with this email address.")
            
    return render(request, 'forgot_password.html')

def reset_password(request, uidb64, token):
    try:
        # Decode the user id
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
        
        # Check if token is valid and not expired
        if not default_token_generator.check_token(user, token):
            messages.error(request, "Password reset link has expired or is invalid.")
            return redirect('login')
        
        if request.method == 'POST':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if new_password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return render(request, 'password_reset_form.html')
            
            # Password length validation
            if len(new_password) < 8:
                messages.error(request, "Password must be at least 8 characters long.")
                return render(request, 'password_reset_form.html')
            
            # Check for at least one uppercase letter
            if not any(char.isupper() for char in new_password):
                messages.error(request, "Password must contain at least one uppercase letter.")
                return render(request, 'password_reset_form.html')
            
            # Check for at least one special character
            import re
            if not re.search("[!@#$%^&*(),.?\":{}|<>]", new_password):
                messages.error(request, "Password must contain at least one special character.")
                return render(request, 'password_reset_form.html')
            
            # Set new password
            user.set_password(new_password)
            
            # If account is not active, activate it
            if not user.is_active:
                user.is_active = True
                user.email_verified = True
                # Clear any activation tokens
                user.activation_token = None
                user.activation_token_created = None
            
            user.save()
            
            if not user.is_active:
                messages.success(request, "Your account has been activated and password has been set. You can now login.")
            else:
                messages.success(request, "Password has been reset successfully. You can now login with your new password.")
            return redirect('show_login')
            
        return render(request, 'password_reset_form.html', {'is_activation': not user.is_active})
        
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        messages.error(request, "Password reset link is invalid or has expired.")
        return redirect('login')

@login_required
def student_home(request):
    if request.user.user_type != "3":  # If not a student
        messages.error(request, "You do not have access to the student dashboard")
        return redirect('login')
        
    try:
        student = Students.objects.get(admin=request.user)
        course = student.course_id
        course_session = CourseSession.objects.get(course=course)
        subjects = Subjects.objects.filter(course_session=course_session)
        
        context = {
            'student': student,
            'course': course,
            'subjects': subjects,
        }
        return render(request, 'student_template/student_home.html', context)
        
    except Students.DoesNotExist:
        messages.error(request, "Student record not found. Please contact the administrator.")
        return redirect('logout')

def set_password(request):
    """Handle first-time password setting for users"""
    if request.method == 'POST':
        token = request.POST.get('token')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        try:
            # Find user by activation token
            user = CustomUser.objects.get(activation_token=token)
            
            # Validate token
            if not user.is_activation_token_valid():
                messages.error(request, "Password set link has expired. Please request a new one.")
                return redirect('show_login')
                
            # Validate passwords
            if password != confirm_password:
                messages.error(request, "Passwords do not match!")
                return render(request, 'password_set_form.html', {'token': token})
                
            # Set the password
            user.set_password(password)
            user.is_active = True  # Activate user
            user.email_verified = True  # Mark email as verified
            user.activation_token = None  # Clear token
            user.activation_token_created = None
            user.save()
            
            messages.success(request, "Password set successfully! You can now login.")
            return redirect('show_login')
            
        except CustomUser.DoesNotExist:
            messages.error(request, "Invalid activation link.")
            return redirect('show_login')
    
    # Handle GET request - show form with token from URL
    token = request.GET.get('token')
    if not token:
        messages.error(request, "Invalid password set link.")
        return redirect('show_login')
        
    try:
        # Validate token exists
        user = CustomUser.objects.get(activation_token=token)
        if not user.is_activation_token_valid():
            messages.error(request, "Password set link has expired. Please request a new one.")
            return redirect('show_login')
            
        return render(request, 'password_set_form.html', {'token': token})
        
    except CustomUser.DoesNotExist:
        messages.error(request, "Invalid activation link.")
        return redirect('show_login')

def send_email(subject, body, to_emails, html_content=False, from_email=None):
    """Utility function to send emails"""
    if not from_email:
        from_email = settings.EMAIL_HOST_USER if hasattr(settings, 'EMAIL_HOST_USER') else 'noreply@example.com'
    
    if not isinstance(to_emails, list):
        to_emails = [to_emails]
    
    try:
        if html_content:
            # Send HTML email
            from django.core.mail import EmailMessage
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=from_email,
                to=to_emails
            )
            email.content_subtype = "html"
            email.send(fail_silently=False)
        else:
            # Send plain text email
            from django.core.mail import send_mail
            send_mail(
                subject=subject,
                message=body,
                from_email=from_email,
                recipient_list=to_emails,
                fail_silently=False
            )
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def delete_admin(request, admin_id):
    """Delete an admin account"""
    from student_management_app.models import AdminHOD, CustomUser
    
    # Check if user has permission (must be a superuser)
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to delete admin accounts")
        return HttpResponseRedirect(reverse("signup_admin"))
    
    try:
        # Get the admin record
        admin = AdminHOD.objects.get(id=admin_id)
        user = admin.admin
        
        # Store information for message
        username = user.username
        email = user.email
        
        # Delete the CustomUser which will cascade delete the AdminHOD
        user.delete()
        
        # Log the activity
        if hasattr(request, 'user') and request.user.is_authenticated:
            from student_management_app.utils import log_user_activity
            log_user_activity(
                user=request.user,
                action='delete',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                target_detail=f"Deleted admin account: {username} ({email})"
            )
        
        messages.success(request, f"Admin account for {username} ({email}) deleted successfully")
    except AdminHOD.DoesNotExist:
        messages.error(request, "Admin account not found")
    except Exception as e:
        messages.error(request, f"Error deleting admin account: {str(e)}")
    
    return HttpResponseRedirect(reverse("signup_admin"))

def download_sample(request, type):
    """Redirects to the download_sample_file function in hodview.py"""
    from student_management_app.HodViews import download_sample_file
    return download_sample_file(request, type)