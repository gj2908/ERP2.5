from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve
from django.conf import settings
from student_management_app.models import UserActivity
import json
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser


class UserActivityMiddleware(MiddlewareMixin):
    """
    Middleware to track user activities for security purposes
    """
    
    async_mode = False  # Add this attribute for Django 5.1+ compatibility
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.get_response = get_response
        # Paths that should not be logged
        self.EXEMPT_PATHS = [
            '/static/',
            '/media/',
            '/favicon.ico',
            '/admin/jsi18n/',
        ]
        # Views that should be logged, along with their action types
        self.LOGGED_VIEWS = {
            'do_login': 'login',
            'user_logout': 'logout',
            'student_view_attendance': 'view',
            'edit_student': 'update',
            'edit_staff': 'update',
            'add_student': 'create',
            'add_staff': 'create',
            'admin_view_attendance': 'view',
            'admin_get_attendance_dates': 'view',
            'delete_student': 'delete',
            'delete_staff': 'delete',
            'manage_student': 'view',
            'manage_staff': 'view',
            'view_attendance': 'view',
            'profile': 'view',
            'reset_password': 'password_change',
        }
    
    def process_request(self, request):
        if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser):
            UserActivity.objects.update_or_create(
                user=request.user,
                defaults={
                    'last_activity': timezone.now(),
                    'session_key': request.session.session_key
                }
            )
        return None

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Do nothing for anonymous users
        if not request.user.is_authenticated:
            return None
            
        # Get URL path
        path = request.path
        
        # Skip exempt paths
        for exempt_path in self.EXEMPT_PATHS:
            if path.startswith(exempt_path):
                return None
        
        # Get view name
        view_name = resolve(path).view_name
        
        # Only log specified views
        if view_name in self.LOGGED_VIEWS:
            # Get client IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
            
            # Get user agent
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Get request data (POST or GET)
            try:
                if request.method == 'POST':
                    extra_data = {
                        'method': 'POST',
                        # Only include safe fields, not password or sensitive data
                        'data': {k: v for k, v in request.POST.items() 
                               if k.lower() not in ('password', 'csrfmiddlewaretoken', 'token')}
                    }
                else:
                    extra_data = {
                        'method': 'GET',
                        'data': {k: v for k, v in request.GET.items()}
                    }
                
                # Clean data to ensure it's JSON serializable
                for key, value in extra_data['data'].items():
                    if isinstance(value, (list, dict)):
                        extra_data['data'][key] = json.dumps(value)
            except:
                extra_data = {'method': request.method}
            
            # Create activity log
            UserActivity.objects.create(
                user=request.user,
                action=self.LOGGED_VIEWS[view_name],
                ip_address=ip,
                user_agent=user_agent,
                target_model=view_kwargs.get('model', ''),
                target_id=view_kwargs.get('id', ''),
                target_detail=view_name,
                extra_data=extra_data
            )
            
        return None 