import datetime
from django.utils import timezone
from datetime import timedelta
import pytz

from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from student_management_app.models import Students, Courses, Subjects, CustomUser, Attendance, AttendanceReport, \
    FeedBackStudent, NotificationStudent, SessionYearModel, CourseSession, ClassSubject, Class, StudentClass
from student_management_app.utils import send_email


def student_home(request):
    student_obj=Students.objects.get(admin=request.user.id)
    attendance_total=AttendanceReport.objects.filter(student_id=student_obj).count()
    attendance_present=AttendanceReport.objects.filter(student_id=student_obj,status=True).count()
    attendance_absent=AttendanceReport.objects.filter(student_id=student_obj,status=False).count()
    course=Courses.objects.get(id=student_obj.course_id.id)
    subjects=Subjects.objects.filter(course_id=course).count()
    subjects_data=Subjects.objects.filter(course_id=course)
    session_obj=SessionYearModel.objects.get(id=student_obj.session_year_id.id)
    
    subject_name=[]
    data_present=[]
    data_absent=[]
    subject_data=Subjects.objects.filter(course_id=student_obj.course_id)
    for subject in subject_data:
        attendance=Attendance.objects.filter(class_subject=subject)
        attendance_present_count=AttendanceReport.objects.filter(attendance_id__in=attendance,status=True,student_id=student_obj.id).count()
        attendance_absent_count=AttendanceReport.objects.filter(attendance_id__in=attendance,status=False,student_id=student_obj.id).count()
        subject_name.append(subject.subject_name)
        data_present.append(attendance_present_count)
        data_absent.append(attendance_absent_count)

    context = {
        'student_obj': student_obj,
        'attendance_total': attendance_total,
        'attendance_present': attendance_present,
        'attendance_absent': attendance_absent,
        'course': course,
        'subjects': subjects,
        'subjects_data': subjects_data,
        'session_obj': session_obj,
        'subject_name': subject_name,
        'data_present': data_present,
        'data_absent': data_absent
    }
    return render(request, 'student_template/student_profile.html', context)

def student_view_attendance(request):
    student = Students.objects.get(admin=request.user.id)
    
    # Get the course_session that matches the student's course and session
    try:
        course_session = CourseSession.objects.get(
            course=student.course_id,
            session_year=student.session_year_id
        )
        
        # Try to get the class for this course_session
        try:
            student_class = Class.objects.get(course_session=course_session)
            
            # Get subjects for this class through ClassSubject
            class_subjects = ClassSubject.objects.filter(class_id=student_class)
            
            if not class_subjects.exists():
                messages.warning(request, "No subjects found for your class")
                return render(request, "student_template/student_view_attendance.html", {"attendance_data": []})
            
            # Get attendance for all subjects in the class
            subject_attendance = []
            
            for class_subject in class_subjects:
                # Get all attendance records for this class subject
                attendance_records = Attendance.objects.filter(class_subject=class_subject)
                
                # Get attendance reports for this student for these attendance records
                attendance_present_count = AttendanceReport.objects.filter(
                    student_id=student,
                    attendance_id__in=attendance_records,
                    status=True
                ).count()
                
                attendance_absent_count = AttendanceReport.objects.filter(
                    student_id=student,
                    attendance_id__in=attendance_records,
                    status=False
                ).count()
                
                total_attendance = attendance_present_count + attendance_absent_count
                
                if total_attendance > 0:
                    attendance_percentage = round((attendance_present_count / total_attendance) * 100, 2)
                else:
                    attendance_percentage = 0
                
                subject_data = {
                    "class_subject": class_subject.subject.subject_name,
                    "total_classes": total_attendance,
                    "classes_attended": attendance_present_count,
                    "classes_absent": attendance_absent_count,
                    "attendance_percentage": attendance_percentage
                }
                subject_attendance.append(subject_data)
            
            context = {
                "attendance_data": subject_attendance,
                "student_name": student.admin.first_name + " " + student.admin.last_name
            }
            
            return render(request, "student_template/student_view_attendance.html", context)
        
        except Class.DoesNotExist:
            messages.warning(request, "No class found for your course and session")
            return render(request, "student_template/student_view_attendance.html", {"attendance_data": []})
    
    except CourseSession.DoesNotExist:
        messages.warning(request, "No course session found for your enrollment")
        return render(request, "student_template/student_view_attendance.html", {"attendance_data": []})

def student_view_attendance_post(request):
    subject_id=request.POST.get("subject")
    try:
        subject_obj=Subjects.objects.get(id=subject_id)
        user_object=CustomUser.objects.get(id=request.user.id)
        stud_obj=Students.objects.get(admin=user_object)

        # Get all attendance for this subject
        attendance=Attendance.objects.filter(class_subject=subject_obj)
        attendance_reports=AttendanceReport.objects.filter(attendance_id__in=attendance,student_id=stud_obj).order_by('-attendance_id__attendance_date')
        
        # Calculate attendance statistics
        total_classes = attendance_reports.count()
        present_count = attendance_reports.filter(status=True).count()
        absent_count = total_classes - present_count
        attendance_percentage = (present_count / total_classes) * 100 if total_classes > 0 else 0

        # Prepare context data
        context = {
            "attendance_reports": attendance_reports,
            "total_classes": total_classes,
            "present_count": present_count,
            "absent_count": absent_count,
            "attendance_percentage": attendance_percentage,
            "subject_name": subject_obj.subject_name
        }

        return render(request, "student_template/student_attendance_data.html", context)
    except Exception as e:
        messages.error(request, f"Error fetching attendance data: {str(e)}")
        return HttpResponseRedirect(reverse("student_view_attendance"))

def student_feedback(request):
    staff_id=Students.objects.get(admin=request.user.id)
    feedback_data=FeedBackStudent.objects.filter(student_id=staff_id)
    return render(request,"student_template/student_feedback.html",{"feedback_data":feedback_data})

def student_feedback_save(request):
    if request.method!="POST":
        return HttpResponseRedirect(reverse("student_feedback"))
    else:
        feedback_msg=request.POST.get("feedback_msg")

        student_obj=Students.objects.get(admin=request.user.id)
        try:
            feedback=FeedBackStudent(student_id=student_obj,feedback=feedback_msg,feedback_reply="")
            feedback.save()
            messages.success(request, "Successfully Sent Feedback")
            return HttpResponseRedirect(reverse("student_feedback"))
        except:
            messages.error(request, "Failed To Send Feedback")
            return HttpResponseRedirect(reverse("student_feedback"))

def student_profile(request):
    user = CustomUser.objects.get(id=request.user.id)
    try:
        student = Students.objects.get(admin=user)
        session = student.session_year_id
        
        # Get the enrolled sections for this student
        class_assignments = StudentClass.objects.filter(student=student).select_related('class_id', 'class_id__course_session')
        
        context = {
            "user": user,
            "student": student,
            "session": session,
            "class_assignments": class_assignments
        }
        
        return render(request, "student_template/student_profile.html", context)
    except Students.DoesNotExist:
        messages.error(request, "No student profile found for this account. Please contact the administrator.")
        return redirect('student_home')  # Redirect to a safe page

def student_profile_save(request):
    if request.method!="POST":
        return HttpResponseRedirect(reverse("student_profile"))
    else:
        messages.error(request,"Profile editing is restricted. Please contact HOD for any changes.")
        return HttpResponseRedirect(reverse("student_profile"))

@csrf_exempt
def student_fcmtoken_save(request):
    token=request.POST.get("token")
    try:
        student=Students.objects.get(admin=request.user.id)
        student.fcm_token=token
        student.save()
        return HttpResponse("True")
    except:
        return HttpResponse("False")

def student_all_notification(request):
    student = Students.objects.get(admin=request.user.id)
    notifications = NotificationStudent.objects.filter(student_id=student.id).order_by('-created_at')
    return render(request, "student_template/all_notification.html", {"notifications": notifications})

def clear_student_notifications(request):
    if request.method == "POST":
        student = Students.objects.get(admin=request.user.id)
        NotificationStudent.objects.filter(student_id=student.id).delete()
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)

def student_change_password(request):
    return render(request, "student_template/change_password.html")

def student_change_password_save(request):
    if request.method != "POST":
        return HttpResponseRedirect(reverse("student_change_password"))
    else:
        old_password = request.POST.get("old_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")
        
        user = CustomUser.objects.get(id=request.user.id)
        
        if not user.check_password(old_password):
            messages.error(request, "Old Password is Incorrect!")
            return HttpResponseRedirect(reverse("student_change_password"))
        
        if new_password != confirm_password:
            messages.error(request, "New Password and Confirm Password do not match!")
            return HttpResponseRedirect(reverse("student_change_password"))
        
        # Check password length
        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long!")
            return HttpResponseRedirect(reverse("student_change_password"))
        
        # Check for at least one uppercase letter
        if not any(char.isupper() for char in new_password):
            messages.error(request, "Password must contain at least one uppercase letter!")
            return HttpResponseRedirect(reverse("student_change_password"))
        
        # Check for at least one special character
        import re
        if not re.search("[!@#$%^&*(),.?\":{}|<>]", new_password):
            messages.error(request, "Password must contain at least one special character!")
            return HttpResponseRedirect(reverse("student_change_password"))
        
        user.set_password(new_password)
        user.save()
        messages.success(request, "Password changed successfully!")
        return HttpResponseRedirect(reverse("student_home"))

@csrf_exempt
def check_student_notifications(request):
    """Check if the student has any new notifications and return the count"""
    if request.user.is_authenticated:
        try:
            student = Students.objects.get(admin=request.user.id)
            # Get notifications that the student hasn't seen yet
            # This assumes you have a 'seen' field on the NotificationStudent model
            # If not, you can check by creation time
            
            # Get notifications created in the last 5 minutes
            five_minutes_ago = timezone.now() - timedelta(minutes=5)
            new_notifications = NotificationStudent.objects.filter(
                student_id=student,
                created_at__gte=five_minutes_ago
            ).count()
            
            return JsonResponse({
                'status': 'success',
                'new_notifications': new_notifications
            })
        except Students.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Student not found'
            })
    return JsonResponse({
        'status': 'error',
        'message': 'User not authenticated'
    })