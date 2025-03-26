from django.conf import settings
from student_management_app.models import Students, NotificationStudent, ClassSubject, Attendance, AttendanceReport
from student_management_app.utils import send_email
import time

def send_attendance_notifications(attendance_id):
    """
    Send attendance notifications to students and parents after a delay
    Only send email notifications for ABSENT students
    But display all notifications on the dashboard
    """
    # Wait for 1 minute
    time.sleep(60)
    
    try:
        # Get the attendance record
        attendance = Attendance.objects.get(id=attendance_id)
        class_subject = attendance.class_subject
        attendance_date = attendance.attendance_date
        
        # Get all attendance reports for this attendance
        attendance_reports = AttendanceReport.objects.filter(attendance=attendance)
        
        for report in attendance_reports:
            student_obj = report.student
            is_present = report.status
            
            # Create student notification for dashboard (for both present and absent)
            notification_student = NotificationStudent(
                student_id=student_obj,
                message=f"[{student_obj.registration_number}] Your attendance for {class_subject.subject.subject_name} on {attendance_date} has been marked as {'Present' if is_present else 'Absent'}."
            )
            notification_student.save()
            
            # Only send emails if the student is marked as ABSENT
            if not is_present:
                # Send email to student using the utility function
                send_email(
                    subject=f'Attendance Update - {class_subject.subject.subject_name}',
                    body=f"Dear {student_obj.admin.first_name},\n\nYour attendance for {class_subject.subject.subject_name} on {attendance_date} has been marked as Absent.\n\nRegards,\nAdmin",
                    to_emails=student_obj.admin.email,
                    fail_silently=True
                )
                
                # Send email to parent if parent email exists
                if hasattr(student_obj, 'parents_email') and student_obj.parents_email:
                    send_email(
                        subject=f'Student Attendance Update - {class_subject.subject.subject_name}',
                        body=f"Dear Parent,\n\nYour child's ({student_obj.admin.first_name} - {student_obj.registration_number}) attendance for {class_subject.subject.subject_name} on {attendance_date} has been marked as Absent.\n\nRegards,\nAdmin",
                        to_emails=student_obj.parents_email,
                        fail_silently=True
                    )
    except Exception as e:
        print(f"Error sending notifications: {str(e)}") 