from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

# Create your models here.
class SessionYearModel(models.Model):
    id = models.AutoField(primary_key=True)
    start_year = models.IntegerField()
    end_year = models.IntegerField()
    objects = models.Manager()

    def __str__(self):
        return f"{self.start_year}-{self.end_year}"

    class Meta:
        verbose_name = "Session Year"
        verbose_name_plural = "Session Years"

class CustomUser(AbstractUser):
    user_type_data=((1,"HOD"),(2,"Staff"),(3,"Student"))
    user_type=models.CharField(default=1,choices=user_type_data,max_length=10)
    is_active = models.BooleanField(default=False)  # User must activate via email
    email_verified = models.BooleanField(default=False)
    activation_token = models.CharField(max_length=100, null=True, blank=True)
    activation_token_created = models.DateTimeField(null=True, blank=True)
    # Flag to control automatic profile creation
    skip_profile_creation = models.BooleanField(default=False)

    def generate_activation_token(self):
        """Generate a unique activation token for this user"""
        from django.utils.crypto import get_random_string
        from django.utils import timezone
        import time
        
        # Use timestamp to ensure uniqueness
        timestamp = int(time.time())
        self.activation_token = f"{get_random_string(length=20)}-{timestamp}"
        self.activation_token_created = timezone.now()
        self.save(update_fields=['activation_token', 'activation_token_created'])
        
        print(f"Generated activation token for {self.email}: {self.activation_token}")
        return self.activation_token

    def is_activation_token_valid(self):
        """Check if the current activation token is still valid"""
        if not self.activation_token or not self.activation_token_created:
            return False
        
        from django.utils import timezone
        from datetime import timedelta
        # Token is valid for 24 hours
        return (timezone.now() - self.activation_token_created) < timedelta(hours=24)

class AdminHOD(models.Model):
    id=models.AutoField(primary_key=True)
    admin=models.OneToOneField(CustomUser,on_delete=models.CASCADE)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now_add=True)
    objects=models.Manager()

class Staffs(models.Model):
    id=models.AutoField(primary_key=True)
    admin=models.OneToOneField(CustomUser,on_delete=models.CASCADE)
    address=models.TextField()
    employee_id=models.CharField(max_length=50, unique=True, null=True, blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now_add=True)
    fcm_token=models.TextField(default="")
    objects=models.Manager()

    def __str__(self):
        return f"{self.admin.first_name} {self.admin.last_name} ({self.employee_id})"

class Courses(models.Model):
    id = models.AutoField(primary_key=True)
    course_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.Manager()

    def __str__(self):
        return self.course_name

class CourseSession(models.Model):
    id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Courses, on_delete=models.CASCADE)
    session_year = models.ForeignKey(SessionYearModel, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.Manager()

    class Meta:
        unique_together = ('course', 'session_year')

    def __str__(self):
        return f"{self.course.course_name} - {self.session_year}"

class Subjects(models.Model):
    id = models.AutoField(primary_key=True)
    subject_name = models.CharField(max_length=255)
    course_session = models.ForeignKey(CourseSession, on_delete=models.CASCADE)
    staff_id = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.Manager()

    def __str__(self):
        return self.subject_name

def get_default_profile_pic():
    """Returns the default profile picture path"""
    return 'profile_pics/default_profile.jpg'

class Students(models.Model):
    id = models.AutoField(primary_key=True)
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    address = models.TextField()
    course_id = models.ForeignKey(Courses, on_delete=models.DO_NOTHING, null=True)
    session_year_id = models.ForeignKey(SessionYearModel, on_delete=models.DO_NOTHING, null=True)
    gender = models.CharField(max_length=50)
    profile_pic = models.ImageField(upload_to='profile_pics/', default=get_default_profile_pic)
    registration_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    parents_email = models.EmailField(max_length=254, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.Manager()

    def __str__(self):
        return self.admin.first_name + " " + self.admin.last_name

class Class(models.Model):
    id = models.AutoField(primary_key=True)
    course_session = models.ForeignKey(CourseSession, on_delete=models.CASCADE)
    section = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.Manager()

    class Meta:
        unique_together = ('course_session', 'section')
        verbose_name_plural = 'Classes'

    @property
    def class_name(self):
        return f"{self.course_session.course.course_name} - {self.section} ({self.course_session.session_year})"

    def __str__(self):
        return self.class_name

class ClassSubject(models.Model):
    id = models.AutoField(primary_key=True)
    class_id = models.ForeignKey(Class, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subjects, on_delete=models.CASCADE)
    staff = models.ForeignKey(Staffs, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.Manager()

    class Meta:
        unique_together = ('class_id', 'subject')

    def __str__(self):
        return f"{self.class_id} - {self.subject.subject_name}"

class Attendance(models.Model):
    id = models.AutoField(primary_key=True)
    class_subject = models.ForeignKey(ClassSubject, on_delete=models.CASCADE)
    attendance_date = models.DateField()
    is_locked = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.Manager()

    def __str__(self):
        return f"{self.class_subject} - {self.attendance_date}"

class AttendanceReport(models.Model):
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Students, on_delete=models.CASCADE)
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE)
    status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.Manager()

    def __str__(self):
        return f"{self.student.admin.first_name} {self.student.admin.last_name} - {self.attendance.attendance_date}"

class AttendanceEditRequest(models.Model):
    id = models.AutoField(primary_key=True)
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE)
    staff = models.ForeignKey(Staffs, on_delete=models.CASCADE)
    request_message = models.TextField(null=True, blank=True, default="Request to edit attendance")
    status_choices = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    )
    status = models.CharField(max_length=10, choices=status_choices, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.Manager()

    def __str__(self):
        return f"Edit request for {self.attendance} by {self.staff.admin.first_name}"

class FeedBackStudent(models.Model):
    id = models.AutoField(primary_key=True)
    student_id = models.ForeignKey(Students, on_delete=models.CASCADE)
    feedback = models.TextField()
    feedback_reply = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()


class FeedBackStaffs(models.Model):
    id = models.AutoField(primary_key=True)
    staff_id = models.ForeignKey(Staffs, on_delete=models.CASCADE)
    feedback = models.TextField()
    feedback_reply=models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()


class NotificationStudent(models.Model):
    id = models.AutoField(primary_key=True)
    student_id = models.ForeignKey(Students, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()


class NotificationStaffs(models.Model):
    id = models.AutoField(primary_key=True)
    staff_id = models.ForeignKey(Staffs, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()

class StudentClass(models.Model):
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Students, on_delete=models.CASCADE)
    class_id = models.ForeignKey(Class, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.Manager()

    class Meta:
        unique_together = ('student', 'class_id')

    def __str__(self):
        return f"{self.student.admin.first_name} {self.student.admin.last_name} - {self.class_id}"

class DeletedCourseID(models.Model):
    deleted_id = models.IntegerField(unique=True)
    deleted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['deleted_id']

class DeletedSubjectID(models.Model):
    deleted_id = models.IntegerField(unique=True)
    deleted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['deleted_id']

class DeletedStudentID(models.Model):
    deleted_id = models.IntegerField(unique=True)
    deleted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['deleted_id']

class DeletedStaffID(models.Model):
    deleted_id = models.IntegerField(unique=True)
    deleted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['deleted_id']

class DeletedClassID(models.Model):
    deleted_id = models.IntegerField(unique=True)
    deleted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['deleted_id']

class SystemSettings(models.Model):
    """Model to store system-wide settings and configurations"""
    setting_key = models.CharField(max_length=50, unique=True)
    setting_value = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "System Setting"
        verbose_name_plural = "System Settings"
    
    def __str__(self):
        return f"{self.setting_key}: {self.setting_value}"
    
    @classmethod
    def get_setting(cls, key, default=None):
        """Get a setting value by key"""
        try:
            setting = cls.objects.get(setting_key=key)
            return setting.setting_value
        except cls.DoesNotExist:
            return default
    
    @classmethod
    def set_setting(cls, key, value, description=None):
        """Set a setting value (create or update)"""
        setting, created = cls.objects.update_or_create(
            setting_key=key,
            defaults={'setting_value': value, 'description': description}
        )
        return setting

class UserActivity(models.Model):
    """Model to track user activities for security and audit purposes"""
    ACTION_CHOICES = (
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
        ('download', 'Download'),
        ('upload', 'Upload'),
        ('failed_login', 'Failed Login'),
        ('password_change', 'Password Change'),
        ('other', 'Other'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    action_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    target_model = models.CharField(max_length=50, null=True, blank=True)
    target_id = models.CharField(max_length=50, null=True, blank=True)
    target_detail = models.CharField(max_length=255, null=True, blank=True)
    extra_data = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = "User Activity"
        verbose_name_plural = "User Activities"
        ordering = ['-action_time']
        
    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.action_time.strftime('%d-%m-%Y %H:%M:%S')}"

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    # Skip profile creation if the flag is set
    if created and not instance.skip_profile_creation:
        if instance.user_type == 1:
            AdminHOD.objects.create(admin=instance)
        elif instance.user_type == 2:
            # Only create staff record if it doesn't exist
            if not hasattr(instance, 'staffs'):
                Staffs.objects.create(admin=instance)
        elif instance.user_type == 3:
            # Only create student record if it doesn't exist
            if not hasattr(instance, 'students'):
                # Create the student with explicit field names matching the model
                student = Students()
                student.admin = instance
                student.gender = 'Male'  # Assuming a default gender
                student.profile_pic = 'default_profile.jpg'  # Assuming a default profile picture
                student.address = 'Default Address'  # Assuming a default address
                student.course_id = Courses.objects.first()  # Use the first available course
                # Get the first available session year
                student.session_year_id = SessionYearModel.objects.first()  # Use the first available session year
                student.registration_number = f"REG{instance.id:03d}"  # Generate registration number
                student.parents_email = 'parent@example.com'  # Default parent email
                student.save()

@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    if instance.user_type == 1:
        instance.adminhod.save()
    elif instance.user_type == 2:
        if hasattr(instance, 'staffs'):
            instance.staffs.save()
    elif instance.user_type == 3:
        if hasattr(instance, 'students'):
            instance.students.save()

@receiver(post_save, sender=CustomUser)
def activate_superuser(sender, instance, created, **kwargs):
    """
    Signal to automatically activate superusers upon creation
    """
    if created and instance.is_superuser and not instance.is_active:
        # Activate the superuser
        instance.is_active = True
        instance.user_type = '1'  # Set as admin
        
        # Use update to avoid triggering this signal again
        CustomUser.objects.filter(pk=instance.pk).update(is_active=True, user_type='1')
        
        # Try to send welcome email
        try:
            from django.conf import settings
            from django.template.loader import render_to_string
            from django.utils.html import strip_tags
            from django.utils import timezone
            from student_management_app.email_utils import send_email
            
            # Prepare context for the email template
            site_url = settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'
            login_url = f"{site_url}"
            
            context = {
                'user': instance,
                'login_url': login_url,
                'site_name': settings.SITE_NAME if hasattr(settings, 'SITE_NAME') else 'SRM Student Portal',
                'current_year': timezone.now().year
            }
            
            # Render HTML email
            html_message = render_to_string('email/welcome_admin.html', context)
            plain_message = strip_tags(html_message)
            
            subject = 'Welcome to SRM Student Portal'
            from_email = settings.EMAIL_HOST_USER
            recipient_list = [instance.email]
            
            send_email(
                subject=subject,
                message=plain_message,
                from_email=from_email,
                recipient_list=recipient_list,
                html_message=html_message
            )
            
            print(f"Welcome email sent to {instance.email}")
        except Exception as e:
            print(f"Failed to send welcome email: {str(e)}")

def create_default_admin():
    """
    Create a default admin user if none exists
    Used when the database is empty or flushed
    """
    import os
    from django.db import connection
    from django.core.management import call_command
    from django.conf import settings
    
    # Check if the tables exist
    try:
        # Check if the migrations have been applied
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM django_migrations")
            migration_count = cursor.fetchone()[0]
            
            if migration_count == 0:
                # Migrations haven't been applied, so we can't create users yet
                return
    except Exception:
        # Tables don't exist yet, so we can't check further
        return
    
    # Check if there are any existing users
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        # Check if we can query the User model
        user_count = User.objects.count()
    except Exception:
        # If we can't query the User model, return
        return
    
    # Only create default admin if no users exist
    if user_count == 0:
        # Get credentials from environment or use defaults
        admin_email = os.environ.get('DEFAULT_ADMIN_EMAIL', 'admin@example.com')
        admin_password = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'admin')
        
        try:
            # Create the admin user
            admin_user = User.objects.create_user(
                username='admin',
                email=admin_email,
                password=admin_password,
                is_staff=True,
                is_active=True,
                is_superuser=True,
                user_type=1
            )
            
            # Log the creation
            print(f"Created default admin user: {admin_email}")
            
            # Ensure the admin HoD record exists
            if not hasattr(admin_user, 'adminhod'):
                AdminHOD.objects.create(admin=admin_user)
                
        except Exception as e:
            print(f"Error creating default admin: {str(e)}")

# Import signal to run after migrations
from django.db.models.signals import post_migrate

@receiver(post_migrate)
def create_default_admin_post_migrate(sender, **kwargs):
    """
    Create default admin user after migrations are applied
    """
    create_default_admin()

class ErrorLog(models.Model):
    """Model for storing system error logs"""
    LEVEL_CHOICES = (
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    )
    
    timestamp = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='ERROR')
    location = models.CharField(max_length=255, help_text="File/view where the error occurred")
    description = models.TextField()
    stack_trace = models.TextField(null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    additional_data = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Error Log'
        verbose_name_plural = 'Error Logs'
    
    def __str__(self):
        return f"{self.level} - {self.timestamp}: {self.description[:100]}"
