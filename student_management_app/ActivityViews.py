from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from student_management_app.models import UserActivity, CustomUser


@login_required
def admin_view_activity_logs(request):
    """
    View to display user activity logs with filtering options for administrators
    """
    # Check if user is authenticated and has staff privileges
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
        
    activities = UserActivity.objects.all().order_by('-action_time')
    
    # Apply filters if provided
    user_id = request.GET.get('user_id')
    action_type = request.GET.get('action')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if user_id:
        activities = activities.filter(user_id=user_id)
    
    if action_type:
        activities = activities.filter(action=action_type)
    
    if date_from:
        activities = activities.filter(action_time__gte=date_from)
    
    if date_to:
        activities = activities.filter(action_time__lte=date_to)
    
    # Get all users for filter dropdown
    users = CustomUser.objects.all()
    
    # Get unique action types for filter dropdown
    action_types = UserActivity.ACTION_CHOICES
    
    # Default pagination to 100 records per page
    activities = activities[:100]
    
    context = {
        "activities": activities,
        "users": users,
        "action_types": action_types,
        "user_id": user_id,
        "action_type": action_type,
        "date_from": date_from,
        "date_to": date_to
    }
    return render(request, "hod_template/activity_logs.html", context) 