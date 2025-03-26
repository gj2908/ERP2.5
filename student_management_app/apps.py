from django.apps import AppConfig


class StudentManagementAppConfig(AppConfig):
    name = 'student_management_app'
    
    def ready(self):
        """
        Method called when the application is ready.
        Import and set up signal handlers and any app initialization here.
        """
        # Import models inside ready() to avoid circular imports
        import student_management_app.models
        
        # We don't need to call create_default_admin() here
        # It will be called by the post_migrate signal handler