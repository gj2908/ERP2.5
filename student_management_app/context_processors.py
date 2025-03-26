from django.conf import settings

def session_timeout(request):
    """Make session idle timeout available in templates."""
    return {
        'SESSION_IDLE_TIMEOUT': settings.SESSION_IDLE_TIMEOUT
    } 