import json
import threading
from datetime import datetime, timedelta
from uuid import uuid4
import traceback
import pytz
from django.utils import timezone
from django.contrib import messages
from django.core import serializers
from django.forms import model_to_dict
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.conf import settings
from django.db import transaction, OperationalError

from student_management_app.models import Subjects, SessionYearModel, Students, Attendance, AttendanceReport, \
    Staffs, FeedBackStaffs, CustomUser, Courses, NotificationStaffs, ClassSubject, StudentClass, NotificationStudent, \
    AttendanceEditRequest
from student_management_app.utils import send_email
from .tasks import send_attendance_notifications


def staff_home(request):
    #For Fetch All Student Under Staff
    subjects=Subjects.objects.filter(staff_id=request.user.id)
    # Get all class subjects for these subjects
    class_subjects = ClassSubject.objects.filter(subject__in=subjects)
    # Count attendances for these class subjects
    attendance_count=Attendance.objects.filter(class_subject__in=class_subjects).count()
    #For Fetch All Approved Leave
    staff=Staffs.objects.get(admin=request.user.id)
    #For Fetch Total Subjects
    subject_count=subjects.count()

    # Get all students in the classes taught by this staff
    student_classes = StudentClass.objects.filter(class_id__in=[cs.class_id for cs in class_subjects])
    students_count = student_classes.count()  # Changed from student_count to students_count

    # Fetch Attendance Data by Subjects
    subject_list=[]
    attendance_list=[]
    for subject in subjects:
        class_subjects_for_subject = ClassSubject.objects.filter(subject=subject)
        attendance_count_per_subject = Attendance.objects.filter(class_subject__in=class_subjects_for_subject).count()
        subject_list.append(subject.subject_name)
        attendance_list.append(attendance_count_per_subject)

    # Get student attendance data
    student_list=[]
    present_list=[]
    absent_list=[]
    for student_class in student_classes:
        student = student_class.student
        attendance_present = AttendanceReport.objects.filter(
            student=student,
            attendance__class_subject__in=class_subjects,
            status=True
        ).count()
        attendance_absent = AttendanceReport.objects.filter(
            student=student,
            attendance__class_subject__in=class_subjects,
            status=False
        ).count()
        student_list.append(f"{student.admin.first_name} {student.admin.last_name}")
        present_list.append(attendance_present)
        absent_list.append(attendance_absent)

    context={
        "students_count": students_count,
        "attendance_count": json.dumps(attendance_count),  # Convert to JSON for JavaScript
        "subject_count": subject_count,
        "subject_list": json.dumps(subject_list),
        "attendance_list": json.dumps(attendance_list),  # Convert to JSON for JavaScript
        "student_list": json.dumps(student_list),
        "present_list": json.dumps(present_list),  # Convert to JSON for JavaScript
        "absent_list": json.dumps(absent_list),  # Convert to JSON for JavaScript
    }
    return render(request,"staff_template/staff_home_template.html",context)

def staff_take_attendance(request):
    staff = Staffs.objects.get(admin=request.user.id)
    class_subjects = ClassSubject.objects.filter(staff=staff)
    context = {
        "class_subjects": class_subjects
    }
    return render(request, "staff_template/staff_take_attendance.html", context)

@csrf_exempt
def get_students(request):
    class_subject_id = request.POST.get("class_subject")
    attendance_date = request.POST.get("attendance_date")
    try:
        class_subject = ClassSubject.objects.get(id=class_subject_id)
        
        # Check if attendance already exists for this date and class subject
        existing_attendance = Attendance.objects.filter(
            class_subject=class_subject,
            attendance_date=attendance_date
        ).first()
        
        students = StudentClass.objects.filter(class_id=class_subject.class_id)
        student_data = []
        
        for student_class in students:
            student = student_class.student
            # Default to True (present) unless there's an existing record showing absent
            status = True
            if existing_attendance:
                # Get existing attendance status if it exists
                attendance_report = AttendanceReport.objects.filter(
                    student=student,
                    attendance=existing_attendance
                ).first()
                if attendance_report:
                    status = attendance_report.status
                    
            data = {
                "id": student.id,
                "name": f"{student.admin.first_name} {student.admin.last_name}",
                "registration_number": student.registration_number,
                "student_email": student.admin.email,
                "parent_email": student.parent_email if hasattr(student, 'parent_email') else "",
                "status": status
            }
            student_data.append(data)
        return JsonResponse(json.dumps(student_data), safe=False)
    except Exception as e:
        return JsonResponse(f"Error: {str(e)}", safe=False)

@csrf_exempt
def save_attendance_data(request):
    student_ids = request.POST.get("student_data")
    class_subject_id = request.POST.get("class_subject")
    attendance_date = request.POST.get("attendance_date")
    students = json.loads(student_ids)
    try:
        class_subject = ClassSubject.objects.get(id=class_subject_id)
        
        # Check if attendance already exists for this date
        existing_attendance = Attendance.objects.filter(
            class_subject=class_subject,
            attendance_date=attendance_date
        ).first()
        
        if existing_attendance:
            # If attendance exists but is not locked (approved for editing)
            if not existing_attendance.is_locked:
                # Update existing attendance reports
                AttendanceReport.objects.filter(attendance=existing_attendance).delete()
                
                for student in students:
                    student_obj = Students.objects.get(id=student['student'])
                    attendance_report = AttendanceReport(
                        student=student_obj,
                        attendance=existing_attendance,
                        status=student['status']
                    )
                    attendance_report.save()
                
                # Re-lock the attendance after editing
                existing_attendance.is_locked = True
                existing_attendance.save()
                
                # Delete any approved edit requests
                AttendanceEditRequest.objects.filter(
                    attendance=existing_attendance,
                    status='approved'
                ).update(status='completed')
                
                # Start background notification task (without .delay, as a normal function call)
                # Use threading to avoid blocking the response
                notification_thread = threading.Thread(
                    target=send_attendance_notifications,
                    args=(existing_attendance.id,)
                )
                notification_thread.daemon = True
                notification_thread.start()
                
                return HttpResponse("OK")
            else:
                return HttpResponse("Error: Attendance for this date is locked. You need to request an edit.")
        else:
            # Create new attendance (locked by default)
            attendance = Attendance(
                class_subject=class_subject,
                attendance_date=attendance_date,
                is_locked=True
            )
            attendance.save()

            for student in students:
                student_obj = Students.objects.get(id=student['student'])
                attendance_report = AttendanceReport(
                    student=student_obj,
                    attendance=attendance,
                    status=student['status']
                )
                attendance_report.save()
            
            # Start background notification task (without .delay, as a normal function call)
            # Use threading to avoid blocking the response
            notification_thread = threading.Thread(
                target=send_attendance_notifications,
                args=(attendance.id,)
            )
            notification_thread.daemon = True
            notification_thread.start()
                
            return HttpResponse("OK")
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}")

def staff_update_attendance(request):
    staff = Staffs.objects.get(admin=request.user.id)
    class_subjects = ClassSubject.objects.filter(staff=staff)
    
    # Get attendance statistics if a class subject is selected
    selected_subject = request.GET.get('class_subject')
    attendance_data = []
    
    if selected_subject:
        try:
            class_subject = ClassSubject.objects.get(id=selected_subject)
            # Get all attendance records for this subject
            attendance_records = Attendance.objects.filter(class_subject=class_subject)
            total_classes = attendance_records.count()
            
            # Get all students in this class
            students = StudentClass.objects.filter(class_id=class_subject.class_id)
            
            for student_class in students:
                student = student_class.student
                # Count present and absent records
                present_count = AttendanceReport.objects.filter(
                    student=student,
                    attendance__class_subject=class_subject,
                    status=True
                ).count()
                absent_count = total_classes - present_count
                
                # Calculate percentage
                attendance_percentage = (present_count / total_classes * 100) if total_classes > 0 else 0
                
                student_data = {
                    'student_name': f"{student.admin.first_name} {student.admin.last_name}",
                    'registration_number': student.registration_number,
                    'total_classes': total_classes,
                    'classes_attended': present_count,
                    'classes_absent': absent_count,
                    'attendance_percentage': round(attendance_percentage, 2)
                }
                attendance_data.append(student_data)
        except Exception as e:
            messages.error(request, f"Error calculating attendance: {str(e)}")
    
    context = {
        "class_subjects": class_subjects,
        "selected_subject": selected_subject,
        "attendance_data": attendance_data
    }
    return render(request, "staff_template/staff_update_attendance.html", context)

@csrf_exempt
def get_attendance_dates(request):
    class_subject_id = request.POST.get("class_subject")
    try:
        class_subject = ClassSubject.objects.get(id=class_subject_id)
        attendance = Attendance.objects.filter(class_subject=class_subject)
        attendance_list = []
        for attendance_single in attendance:
            data = {
                "id": attendance_single.id,
                "attendance_date": str(attendance_single.attendance_date)
            }
            attendance_list.append(data)
        return JsonResponse(json.dumps(attendance_list), safe=False)
    except Exception as e:
        return JsonResponse(f"Error: {str(e)}", safe=False)

@csrf_exempt
def get_attendance_student(request):
    attendance_date = request.POST.get("attendance_date")
    try:
        attendance = Attendance.objects.get(id=attendance_date)
        attendance_data = AttendanceReport.objects.filter(attendance=attendance)
        student_data = []
        for student in attendance_data:
            data = {
                "id": student.student.id,
                "name": f"{student.student.admin.first_name} {student.student.admin.last_name}",
                "status": student.status
            }
            student_data.append(data)
        return JsonResponse(json.dumps(student_data), safe=False)
    except Exception as e:
        return JsonResponse(f"Error: {str(e)}", safe=False)

@csrf_exempt
def update_attendance_data(request):
    student_data = request.POST.get("student_data")
    attendance_date = request.POST.get("attendance_date")
    students = json.loads(student_data)
    try:
        attendance = Attendance.objects.get(id=attendance_date)
        for student in students:
            student_obj = Students.objects.get(id=student['student'])
            attendance_report = AttendanceReport.objects.get(
                student=student_obj,
                attendance=attendance
            )
            attendance_report.status = student['status']
            attendance_report.save()
        return HttpResponse("OK")
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}")

def staff_feedback(request):
    staff_id=Staffs.objects.get(admin=request.user.id)
    feedback_data=FeedBackStaffs.objects.filter(staff_id=staff_id)
    return render(request,"staff_template/staff_feedback.html",{"feedback_data":feedback_data})

def staff_feedback_save(request):
    if request.method!="POST":
        return HttpResponseRedirect(reverse("staff_feedback_save"))
    else:
        feedback_msg=request.POST.get("feedback_msg")

        staff_obj=Staffs.objects.get(admin=request.user.id)
        try:
            feedback=FeedBackStaffs(staff_id=staff_obj,feedback=feedback_msg,feedback_reply="")
            feedback.save()
            messages.success(request, "Successfully Sent Feedback")
            return HttpResponseRedirect(reverse("staff_feedback"))
        except:
            messages.error(request, "Failed To Send Feedback")
            return HttpResponseRedirect(reverse("staff_feedback"))

def staff_profile(request):
    user=CustomUser.objects.get(id=request.user.id)
    staff=Staffs.objects.get(admin=user)
    return render(request,"staff_template/staff_profile.html",{"user":user,"staff":staff})

def staff_profile_save(request):
    if request.method!="POST":
        return HttpResponseRedirect(reverse("staff_profile"))
    else:
        messages.error(request,"Profile editing is restricted. Please contact HOD for any changes.")
        return HttpResponseRedirect(reverse("staff_profile"))

@csrf_exempt
def staff_fcmtoken_save(request):
    token=request.POST.get("token")
    try:
        staff=Staffs.objects.get(admin=request.user.id)
        staff.fcm_token=token
        staff.save()
        return HttpResponse("True")
    except:
        return HttpResponse("False")

def staff_all_notification(request):
    staff = Staffs.objects.get(admin=request.user.id)
    notifications = NotificationStaffs.objects.filter(staff_id=staff.id).order_by('-created_at')
    return render(request, "staff_template/all_notification.html", {"notifications": notifications})

def clear_staff_notifications(request):
    if request.method == "POST":
        staff = Staffs.objects.get(admin=request.user.id)
        NotificationStaffs.objects.filter(staff_id=staff.id).delete()
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)

@csrf_exempt
def check_attendance_exists(request):
    if request.method != 'POST':
        return HttpResponse('Method Not Allowed')
    
    class_subject_id = request.POST.get('class_subject')
    attendance_date = request.POST.get('attendance_date')
    
    try:
        attendance = Attendance.objects.get(
            class_subject_id=class_subject_id,
            attendance_date=attendance_date
        )
        return JsonResponse({
            'exists': True,
            'locked': attendance.is_locked
        })
    except Attendance.DoesNotExist:
        return JsonResponse({
            'exists': False,
            'locked': False
        })

@csrf_exempt
def request_attendance_edit(request):
    if request.method != 'POST':
        return HttpResponse('Method Not Allowed')
    
    class_subject_id = request.POST.get('class_subject')
    attendance_date = request.POST.get('attendance_date')
    request_message = request.POST.get('request_message', 'Request to edit attendance')
    
    # Get the staff object
    staff = Staffs.objects.get(admin=request.user)
    
    try:
        # Check if attendance exists
        attendance = Attendance.objects.get(
            class_subject_id=class_subject_id,
            attendance_date=attendance_date
        )
        
        # Check if an edit request already exists
        existing_request = AttendanceEditRequest.objects.filter(
            attendance=attendance,
            staff=staff,
            status='pending'
        ).first()
        
        if existing_request:
            return JsonResponse({
                'status': False,
                'message': 'You already have a pending request for this attendance'
            })
        
        # Create a new request
        edit_request = AttendanceEditRequest(
            attendance=attendance,
            staff=staff,
            request_message=request_message
        )
        edit_request.save()
        
        # Notify admins
        admin_users = CustomUser.objects.filter(user_type=1)
        for admin in admin_users:
            notification = NotificationStaffs.objects.create(
                staff_id=staff,
                message=f"Request to edit attendance for {attendance.class_subject.subject.subject_name} on {attendance.attendance_date}"
            )
        
        return JsonResponse({
            'status': True,
            'message': 'Edit request submitted successfully'
        })
        
    except Attendance.DoesNotExist:
        return JsonResponse({
            'status': False,
            'message': 'Attendance record not found'
        })
    except Exception as e:
        return JsonResponse({
            'status': False,
            'message': f'Error: {str(e)}'
        })

@csrf_exempt
def check_edit_request_status(request):
    if request.method != 'POST':
        return HttpResponse('Method Not Allowed')
    
    class_subject_id = request.POST.get('class_subject')
    attendance_date = request.POST.get('attendance_date')
    
    # Get the staff object
    staff = Staffs.objects.get(admin=request.user)
    
    try:
        # Check if attendance exists
        attendance = Attendance.objects.get(
            class_subject_id=class_subject_id,
            attendance_date=attendance_date
        )
        
        # Check for pending requests
        pending_request = AttendanceEditRequest.objects.filter(
            attendance=attendance,
            staff=staff,
            status='pending'
        ).first()
        
        if pending_request:
            return JsonResponse({
                'status': 'pending',
                'message': 'Your edit request is pending approval'
            })
        
        # Check for approved requests
        approved_request = AttendanceEditRequest.objects.filter(
            attendance=attendance,
            staff=staff,
            status='approved'
        ).first()
        
        if approved_request:
            # Update the attendance lock status
            attendance.is_locked = False
            attendance.save()
            
            return JsonResponse({
                'status': 'approved',
                'message': 'Your edit request has been approved'
            })
        
        # Check for rejected requests
        rejected_request = AttendanceEditRequest.objects.filter(
            attendance=attendance,
            staff=staff,
            status='rejected'
        ).first()
        
        if rejected_request:
            return JsonResponse({
                'status': 'rejected',
                'message': 'Your edit request has been rejected'
            })
        
        return JsonResponse({
            'status': 'none',
            'message': 'No edit requests found'
        })
        
    except Attendance.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Attendance record not found'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error: {str(e)}'
        })

def returnHtmlWidget(request):
    return render(request,"widget.html")

@csrf_exempt
def export_attendance_excel(request):
    import xlwt
    from django.http import HttpResponse
    from datetime import datetime
    
    class_subject_id = request.POST.get('class_subject')
    try:
        class_subject = ClassSubject.objects.get(id=class_subject_id)
        attendance_records = Attendance.objects.filter(class_subject=class_subject)
        total_classes = attendance_records.count()
        students = StudentClass.objects.filter(class_id=class_subject.class_id)
        
        # Create workbook and sheet
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Attendance Report')
        
        # Write headers
        row_num = 0
        font_style = xlwt.XFStyle()
        font_style.font.bold = True
        
        columns = ['Registration No.', 'Student Name', 'Total Classes', 'Classes Attended', 'Classes Absent', 'Attendance %']
        for col_num, column_title in enumerate(columns):
            ws.write(row_num, col_num, column_title, font_style)
        
        # Write data
        font_style = xlwt.XFStyle()
        for student_class in students:
            row_num += 1
            student = student_class.student
            present_count = AttendanceReport.objects.filter(
                student=student,
                attendance__class_subject=class_subject,
                status=True
            ).count()
            absent_count = total_classes - present_count
            attendance_percentage = (present_count / total_classes * 100) if total_classes > 0 else 0
            
            row = [
                student.registration_number,
                f"{student.admin.first_name} {student.admin.last_name}",
                total_classes,
                present_count,
                absent_count,
                f"{round(attendance_percentage, 2)}%"
            ]
            
            for col_num, cell_value in enumerate(row):
                ws.write(row_num, col_num, cell_value, font_style)
        
        # Generate filename
        filename = f'Attendance_Report_{class_subject.subject.subject_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xls'
        
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        return response
        
    except Exception as e:
        print(f"Error exporting to Excel: {str(e)}")  # Log the error
        return HttpResponse(f"Error: {str(e)}")

@csrf_exempt
def export_attendance_pdf(request):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape  # Import landscape for wider pages
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    from io import BytesIO
    import traceback  # Import traceback for detailed error logging
    
    class_subject_id = request.POST.get('class_subject')
    try:
        class_subject = ClassSubject.objects.get(id=class_subject_id)
        attendance_records = Attendance.objects.filter(class_subject=class_subject)
        total_classes = attendance_records.count()
        students = StudentClass.objects.filter(class_id=class_subject.class_id)
        
        # Create the PDF buffer and document
        buffer = BytesIO()
        # Use landscape orientation for wider pages
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []
        
        # Create data for the table
        data = [['Student Name', 'Total Attendance']]
        
        for student_class in students:
            student = student_class.student
            present_count = AttendanceReport.objects.filter(
                student=student,
                attendance__class_subject=class_subject,
                status=True
            ).count()
            
            data.append([
                f"{student.admin.first_name} {student.admin.last_name}",
                str(present_count)
            ])
        
        # Create the table and style it
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        
        # Generate response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Attendance_Statistics_{class_subject.subject.subject_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        return response
        
    except Exception as e:
        error_message = f"Error exporting to PDF: {str(e)}\n{traceback.format_exc()}"
        print(error_message)  # Log the detailed error
        return HttpResponse(f"Error: {error_message}")

def staff_change_password(request):
    return render(request, "staff_template/change_password.html")

def staff_change_password_save(request):
    if request.method != "POST":
        return HttpResponseRedirect(reverse("staff_change_password"))
    else:
        old_password = request.POST.get("old_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")
        
        user = CustomUser.objects.get(id=request.user.id)
        
        if not user.check_password(old_password):
            messages.error(request, "Old Password is Incorrect!")
            return HttpResponseRedirect(reverse("staff_change_password"))
        
        if new_password != confirm_password:
            messages.error(request, "New Password and Confirm Password do not match!")
            return HttpResponseRedirect(reverse("staff_change_password"))
        
        # Check password length
        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long!")
            return HttpResponseRedirect(reverse("staff_change_password"))
        
        # Check for at least one uppercase letter
        if not any(char.isupper() for char in new_password):
            messages.error(request, "Password must contain at least one uppercase letter!")
            return HttpResponseRedirect(reverse("staff_change_password"))
        
        # Check for at least one special character
        import re
        if not re.search("[!@#$%^&*(),.?\":{}|<>]", new_password):
            messages.error(request, "Password must contain at least one special character!")
            return HttpResponseRedirect(reverse("staff_change_password"))
        
        user.set_password(new_password)
        user.save()
        messages.success(request, "Password changed successfully!")
        return HttpResponseRedirect(reverse("staff_home"))

def export_staff_attendance_pdf(request):
    """
    View function to export attendance statistics to PDF for staff view
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from django.http import HttpResponse
    import io

    if request.method == 'POST':
        class_subject_id = request.POST.get('class_subject_id')

        try:
            # Get the class subject and related data
            class_subject = ClassSubject.objects.get(id=class_subject_id)
            
            # Get attendance records
            attendance_records = Attendance.objects.filter(class_subject=class_subject)
            total_classes = attendance_records.count()
            
            # Get students attendance data
            students = StudentClass.objects.filter(class_id=class_subject.class_id)
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
                    student.registration_number,
                    f"{student.admin.first_name} {student.admin.last_name}",
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
            
            # Add class and subject details
            detail_style = ParagraphStyle(
                'Details',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=12
            )
            
            elements.append(Paragraph(f"Class: {class_subject.class_id.course_session.course.course_name} - {class_subject.class_id.section}", detail_style))
            elements.append(Paragraph(f"Subject: {class_subject.subject.subject_name}", detail_style))
            elements.append(Paragraph(f"Total Classes: {total_classes}", detail_style))
            elements.append(Paragraph(f"Total Students: {len(attendance_data)}", detail_style))
            
            elements.append(Spacer(1, 20))

            # Create table
            table_data = [['Registration Number', 'Student Name', 'Total Classes', 'Classes Attended', 'Classes Absent', 'Attendance %']]
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
            response['Content-Disposition'] = f'attachment; filename="attendance_report_{class_subject.subject.subject_name}.pdf"'
            response.write(buffer.getvalue())
            buffer.close()
            
            return response

        except Exception as e:
            messages.error(request, f"Error generating PDF: {str(e)}")
            return redirect('staff_update_attendance')

    return redirect('staff_update_attendance')