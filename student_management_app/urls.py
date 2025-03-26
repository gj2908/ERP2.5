from django.urls import path, include
from . import views, HodViews, StaffViews, StudentViews
from student_management_app import ActivityViews
from . import views

urlpatterns = [
    # Main URLs moved from student_management_system/urls.py
    path("", views.showLoginPage, name='main_home_page'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('admin-signup/', views.signup_admin, name='signup_admin'),
    path('student-signup/', views.signup_student, name='signup_student'),
    path('staff-signup/', views.signup_staff, name='signup_staff'),
    path('accounts/login/', views.showLoginPage, name="show_login"),
    path('doLogin', views.doLogin, name="do_login"),
    path('get_user_details', views.GetUserDetails),
    path('logout_user', views.logout_user, name="logout"),
    path('forgot-password/', views.forgot_password, name="forgot_password"),
    path('reset-password/<str:token>/', views.reset_password, name="reset_password"),
    path('manage_admin/', HodViews.manage_admin, name="manage_admin"),
    
    # Existing URLs
    path('', views.showLoginPage, name="show_login"),
    path('get_user_details', views.GetUserDetails),
    path('logout_user', views.logout_user, name="logout"),
    path('doLogin', views.doLogin, name="do_login"),
    path('signup_admin', views.signup_admin, name="signup_admin"),
    path('signup_staff', views.signup_staff, name="signup_staff"),
    path('signup_student', views.signup_student, name="signup_student"),
    path('do_admin_signup', views.do_admin_signup, name="do_admin_signup"),
    path('do_staff_signup', views.do_staff_signup, name="do_staff_signup"),
    path('do_signup_student', views.do_signup_student, name="do_signup_student"),
    path('delete_admin/<str:admin_id>', views.delete_admin, name="delete_admin"),
    path('admin_home', HodViews.admin_home, name="admin_home"),
    
    # Staff URLs
    path('staff_home/', StaffViews.staff_home, name="staff_home"),
    path('add_staff', HodViews.add_staff, name="add_staff"),
    path('manage_staff', HodViews.manage_staff, name="manage_staff"),
    path('edit_staff/<str:staff_id>', HodViews.edit_staff, name="edit_staff"),
    path('edit_staff_save', HodViews.edit_staff_save, name="edit_staff_save"),
    path('delete_staff/<str:staff_id>/', HodViews.delete_staff, name="delete_staff"),
    path('update_staff_employee_id/', HodViews.update_staff_employee_id, name="update_staff_employee_id"),
    path('staff_profile/', StaffViews.staff_profile, name="staff_profile"),
    path('staff_profile_save/', StaffViews.staff_profile_save, name="staff_profile_save"),
    path('staff_fcmtoken_save/', StaffViews.staff_fcmtoken_save, name='staff_fcmtoken_save'),
    
    # Modified Staff URLs
    path('add_staff_save/', HodViews.add_staff_save, name="add_staff_save"),
    path('bulk_upload_staff/', HodViews.bulk_upload_staff, name="bulk_upload_staff"),
    path('bulk_upload_staff_save/', HodViews.bulk_upload_staff_save, name="bulk_upload_staff_save"),
    
    # Modified Student URLs
    path('add_student_save/', HodViews.add_student_save, name="add_student_save"),
    path('bulk_upload_student/', HodViews.bulk_upload_student, name="bulk_upload_student"),
    path('bulk_upload_student_save/', HodViews.bulk_upload_student_save, name="bulk_upload_student_save"),
    path('download_sample/<str:type>/', HodViews.download_sample_file, name="download_sample"),
    
    # Staff Functionality URLs
    path('staff_feedback/', StaffViews.staff_feedback, name="staff_feedback"),
    path('staff_feedback_save/', StaffViews.staff_feedback_save, name="staff_feedback_save"),
    path('staff_all_notification/', StaffViews.staff_all_notification, name="staff_all_notification"),
    path('clear_staff_notifications/', StaffViews.clear_staff_notifications, name="clear_staff_notifications"),
    
    # Course URLs
    path('add_course/', HodViews.add_course, name="add_course"),
    path('add_course_save/', HodViews.add_course_save, name="add_course_save"),
    path('manage_course/', HodViews.manage_course, name="manage_course"),
    path('edit_course/<str:course_id>/', HodViews.edit_course, name="edit_course"),
    path('edit_course_save/', HodViews.edit_course_save, name="edit_course_save"),
    path('delete_course/<str:course_id>/', HodViews.delete_course, name="delete_course"),
    path('get_course_sessions/', HodViews.get_course_sessions, name="get_course_sessions"),
    
    # Course Session URLs
    path('add_course_session/', HodViews.add_course_session, name="add_course_session"),
    path('add_course_session_save/', HodViews.add_course_session_save, name="add_course_session_save"),
    path('manage_course_session/', HodViews.manage_course_session, name="manage_course_session"),
    
    # Subject URLs
    path('add_subject/', HodViews.add_subject, name="add_subject"),
    path('add_subject_save/', HodViews.add_subject_save, name="add_subject_save"),
    path('manage_subject/', HodViews.manage_subject, name="manage_subject"),
    path('edit_subject/<str:subject_id>/', HodViews.edit_subject, name="edit_subject"),
    path('edit_subject_save/', HodViews.edit_subject_save, name="edit_subject_save"),
    path('delete_subject/<str:subject_id>/', HodViews.delete_subject, name="delete_subject"),
    
    # Class URLs
    path('manage_class/', HodViews.manage_class, name="manage_class"),
    path('add_class_save/', HodViews.add_class_save, name="add_class_save"),
    path('get_courses_by_session/', HodViews.get_courses_by_session, name="get_courses_by_session"),
    path('get_subjects_by_course_session/', HodViews.get_subjects_by_course_session, name="get_subjects_by_course_session"),
    path('get_subjects_by_class/', HodViews.get_subjects_by_class, name="get_subjects_by_class"),
    path('get_assigned_subjects/', HodViews.get_assigned_subjects, name="get_assigned_subjects"),
    path('assign_subject_to_class/', HodViews.assign_subject_to_class, name="assign_subject_to_class"),
    path('update_subject_staff/', HodViews.update_subject_staff, name="update_subject_staff"),
    path('remove_subject_from_class/', HodViews.remove_subject_from_class, name="remove_subject_from_class"),
    path('add_students_to_class/', HodViews.add_students_to_class, name="add_students_to_class"),
    path('remove_student_from_class/<str:class_id>/<str:student_id>/', HodViews.remove_student_from_class, name="remove_student_from_class"),
    path('remove_student_ajax/', HodViews.remove_student_ajax, name="remove_student_ajax"),
    path('delete_class/<str:class_id>/', HodViews.delete_class, name="delete_class"),
    path('get_class_students/', HodViews.get_class_students, name="get_class_students"),
    path('get_class_details/', HodViews.get_class_details, name="get_class_details"),
    path('get_available_students/', HodViews.get_available_students, name="get_available_students"),
    path('get_students_by_range/', HodViews.get_students_by_range, name="get_students_by_range"),
    path('export_class_students_excel/<int:class_id>/', HodViews.export_class_students_excel, name='export_class_students_excel'),
    path('export_class_students_pdf/<int:class_id>/', HodViews.export_class_students_pdf, name='export_class_students_pdf'),
    path('remove_all_students_from_class/', HodViews.remove_all_students_from_class, name='remove_all_students_from_class'),
    
    # Student URLs
    path('add_student/', HodViews.add_student, name="add_student"),
    path('manage_student/', HodViews.manage_student, name="manage_student"),
    path('edit_student/<str:student_id>/', HodViews.edit_student, name="edit_student"),
    path('edit_student_save/', HodViews.edit_student_save, name="edit_student_save"),
    path('delete_student/<str:student_id>/', HodViews.delete_student, name="delete_student"),
    
    # Session URLs
    path('add_session/', HodViews.add_session, name="add_session"),
    path('add_session_save/', HodViews.add_session_save, name="add_session_save"),
    path('manage_session/', HodViews.manage_session, name="manage_session"),
    path('edit_session/<str:session_id>/', HodViews.edit_session, name="edit_session"),
    path('edit_session_save/', HodViews.edit_session_save, name="edit_session_save"),
    path('delete_session/<str:session_id>/', HodViews.delete_session, name="delete_session"),
    
    # Attendance URLs
    path('admin_view_attendance/', HodViews.admin_view_attendance, name="admin_view_attendance"),
    path('admin_get_attendance_dates/', HodViews.admin_get_attendance_dates, name="admin_get_attendance_dates"),
    path('admin_get_attendance_student/', HodViews.admin_get_attendance_student, name="admin_get_attendance_student"),
    path('export_attendance_pdf/', HodViews.export_attendance_pdf, name="export_attendance_pdf"),
    path('get_classes_by_session/', HodViews.get_classes_by_session, name="get_classes_by_session"),
    
    # Feedback URLs
    path('student_feedback_message/', HodViews.student_feedback_message, name="student_feedback_message"),
    path('staff_feedback_message/', HodViews.staff_feedback_message, name="staff_feedback_message"),
    path('student_feedback_message_replied/', HodViews.student_feedback_message_replied, name="student_feedback_message_replied"),
    path('staff_feedback_message_replied/', HodViews.staff_feedback_message_replied, name="staff_feedback_message_replied"),
    
    # Staff Attendance URLs
    path('staff_take_attendance/', StaffViews.staff_take_attendance, name="staff_take_attendance"),
    path('get_students/', StaffViews.get_students, name="get_students"),
    path('save_attendance_data/', StaffViews.save_attendance_data, name="save_attendance_data"),
    path('check_attendance_exists/', StaffViews.check_attendance_exists, name="check_attendance_exists"),
    path('request_attendance_edit/', StaffViews.request_attendance_edit, name="request_attendance_edit"),
    path('check_edit_request_status/', StaffViews.check_edit_request_status, name="check_edit_request_status"),
    path('staff_update_attendance/', StaffViews.staff_update_attendance, name="staff_update_attendance"),
    path('get_attendance_dates/', StaffViews.get_attendance_dates, name="get_attendance_dates"),
    path('get_attendance_student/', StaffViews.get_attendance_student, name="get_attendance_student"),
    path('update_attendance_data/', StaffViews.update_attendance_data, name="update_attendance_data"),
    path('export_attendance_excel/', StaffViews.export_attendance_excel, name="export_attendance_excel"),
    path('export_staff_attendance_pdf/', StaffViews.export_staff_attendance_pdf, name="export_staff_attendance_pdf"),
    path('student_home/', views.student_home, name="student_home"),
    path('student_view_attendance/', StudentViews.student_view_attendance, name="student_view_attendance"),
    path('student_feedback/', StudentViews.student_feedback, name="student_feedback"),
    path('student_notifications/', StudentViews.student_all_notification, name="student_notifications"),
    path('clear_student_notifications/', StudentViews.clear_student_notifications, name="clear_student_notifications"),
    path('student_profile/', StudentViews.student_profile, name='student_profile'),
    path('student_view_attendance_post/', StudentViews.student_view_attendance_post, name='student_view_attendance_post'),
    path('student_feedback_save/', StudentViews.student_feedback_save, name='student_feedback_save'),
    path('check_email_exist/', HodViews.check_email_exist, name='check_email_exist'),
    path('check_username_exist/', HodViews.check_username_exist, name='check_username_exist'),
    path('download_sample/<str:file_type>/', HodViews.download_sample_file, name='download_sample'),
    
    # Password Change URLs
    path('admin_change_password/', HodViews.admin_change_password, name='admin_change_password'),
    path('admin_change_password_save/', HodViews.admin_change_password_save, name='admin_change_password_save'),
    path('admin_profile/', HodViews.admin_profile, name='admin_profile'),
    path('admin_profile_save/', HodViews.admin_profile_save, name='admin_profile_save'),
    path('staff_change_password/', StaffViews.staff_change_password, name='staff_change_password'),
    path('staff_change_password_save/', StaffViews.staff_change_password_save, name='staff_change_password_save'),
    path('student_change_password/', StudentViews.student_change_password, name='student_change_password'),
    path('student_change_password_save/', StudentViews.student_change_password_save, name='student_change_password_save'),
    path('check_student_notifications/', StudentViews.check_student_notifications, name="check_student_notifications"),
    
    # Developer/Environment settings
    path('debug_settings', HodViews.debug_settings, name="debug_settings"),
    path('save_debug_settings', HodViews.save_debug_settings, name="save_debug_settings"),
    path('get_terminal_output', HodViews.get_terminal_output, name="get_terminal_output"),
    
    # Attendance Edit Request URLs for Admin
    path('attendance_edit_requests/', HodViews.attendance_edit_requests, name="attendance_edit_requests"),
    path('approve_attendance_edit/<str:request_id>/', HodViews.approve_attendance_edit, name="approve_attendance_edit"),
    path('reject_attendance_edit/<str:request_id>/', HodViews.reject_attendance_edit, name="reject_attendance_edit"),
    path('set-password/', views.set_password, name='set_password'),
    
    # URL path for Activity Logs
    path('admin_view_activity_logs/', ActivityViews.admin_view_activity_logs, name="admin_view_activity_logs"),
] 