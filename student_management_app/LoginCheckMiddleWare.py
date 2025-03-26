from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
import inspect
from datetime import datetime
from .models import UserActivity
from django.contrib import messages


class LoginCheckMiddleWare(MiddlewareMixin):
    async_mode = False  # Add this attribute for Django 5.1+ compatibility
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.get_response = get_response

    def process_view(self, request, view_func, view_args, view_kwargs):
        modulename = view_func.__module__
        user = request.user

        if user.is_authenticated:
            if user.user_type == "1":  # HOD
                if modulename in ["student_management_app.StaffViews", "student_management_app.StudentViews"]:
                    messages.error(request, "Access Denied")
                    return HttpResponseRedirect(reverse("admin_home"))
            elif user.user_type == "2":  # Staff
                if modulename in ["student_management_app.HodViews", "student_management_app.StudentViews"]:
                    messages.error(request, "Access Denied")
                    return HttpResponseRedirect(reverse("staff_home"))
            elif user.user_type == "3":  # Student
                if modulename in ["student_management_app.HodViews", "student_management_app.StaffViews"]:
                    messages.error(request, "Access Denied")
                    return HttpResponseRedirect(reverse("student_home"))
            else:
                return HttpResponseRedirect(reverse("show_login"))
        else:
            if request.path == reverse("show_login") or request.path == reverse("do_login") or modulename == "django.contrib.auth.views" or request.path == reverse("signup_admin") or request.path == reverse("do_admin_signup") or request.path == reverse("signup_staff") or request.path == reverse("do_staff_signup") or request.path == reverse("signup_student") or request.path == reverse("do_signup_student") or request.path == reverse("forgot_password") or request.path == reverse("reset_password"):
                pass
            else:
                return HttpResponseRedirect(reverse("show_login"))

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self,request,view_func,view_args,view_kwargs):
        modulename=view_func.__module__
        # print(modulename)
        user=request.user

        # Extract details for logging
        if user.is_authenticated:
            # Get view name
            view_name = view_func.__name__
            
            # Record the user activity
            # Skip recording for some common views to avoid cluttering the logs
            if not (
                view_name in ['static', 'media', 'admin_view_activity_logs'] or
                modulename.startswith('django.') or
                modulename.startswith('debug_toolbar')
            ):
                try:
                    UserActivity.objects.create(
                        user=user,
                        action=view_name,
                        path=request.path,
                        method=request.method,
                        timestamp=datetime.now()
                    )
                except:
                    # Silently fail if logging fails
                    pass

        #Check whether the user is logged in or not
        if not user.is_authenticated:
            if modulename == "student_management_app.HodViews" or modulename == "student_management_app.StaffViews" or modulename == "student_management_app.StudentViews" or modulename == "student_management_app.ActivityViews":
                return HttpResponseRedirect(reverse("show_login"))
            
        else:
            if modulename == "student_management_app.views" or modulename == "django.views.static":
                pass
            else:
                if user.user_type == "1":
                    if modulename != "student_management_app.HodViews" and modulename != "student_management_app.ActivityViews":
                        return HttpResponseRedirect(reverse("admin_home"))
                elif user.user_type == "2":
                    if modulename != "student_management_app.StaffViews":
                        return HttpResponseRedirect(reverse("staff_home"))
                elif user.user_type == "3":
                    if modulename != "student_management_app.StudentViews":
                        return HttpResponseRedirect(reverse("student_home"))
                else:
                    return HttpResponseRedirect(reverse("show_login"))