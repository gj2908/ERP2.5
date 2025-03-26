from django.contrib.auth.management.commands.createsuperuser import Command as SuperuserCommand
from django.core.management.base import CommandError
from django.db import transaction
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from student_management_app.email_utils import send_email, generate_activation_token
from student_management_app.models import CustomUser


class Command(SuperuserCommand):
    help = 'Create a superuser account with inactive status requiring email activation'

    def handle(self, *args, **options):
        options.setdefault('interactive', True)
        database = options.get('database')
        
        # Get the username field
        username_field = self.UserModel._meta.get_field(self.UserModel.USERNAME_FIELD)
        
        # Get all required fields excluding username
        required_fields = (
            field
            for field in self.UserModel.REQUIRED_FIELDS
            if field != username_field
        )
        
        try:
            # Call the parent's handle method with modified arguments
            with transaction.atomic():
                # Create the superuser first
                user = super().handle(*args, **options)
                
                # Now manually update the user with user_type and set inactive status
                # Find the most recently created superuser
                if database:
                    latest_user = self.UserModel._default_manager.db_manager(database).filter(
                        is_superuser=True
                    ).latest('date_joined')
                else:
                    latest_user = self.UserModel._default_manager.filter(
                        is_superuser=True
                    ).latest('date_joined')
                
                # Set the user_type but keep inactive
                latest_user.user_type = '1'  # Admin type
                latest_user.is_active = False  # Set to inactive initially
                
                # Generate activation token
                activation_token = generate_activation_token(latest_user)
                
                # Send welcome email with activation button
                self._send_welcome_email(latest_user, activation_token)
                
                if options['verbosity'] >= 1:
                    self.stdout.write(self.style.SUCCESS(
                        f"Superuser '{latest_user.username}' created and welcome email with activation link sent successfully."
                    ))
                
                return user
                
        except Exception as e:
            raise CommandError(f"Error creating superuser: {e}")
    
    def _send_welcome_email(self, user, activation_token):
        """Send a welcome email with activation link to the newly created superuser."""
        try:
            # Prepare context for the email template
            site_url = settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'
            activation_url = f"{site_url}/activate/{activation_token}/"
            
            context = {
                'user': user,
                'activation_url': activation_url,
                'site_name': settings.SITE_NAME if hasattr(settings, 'SITE_NAME') else 'SRM Student Portal',
                'current_year': timezone.now().year
            }
            
            # Render HTML email
            html_message = render_to_string('email/welcome_admin.html', context)
            plain_message = strip_tags(html_message)
            
            subject = 'Welcome to SRM Student Portal - Activate Your Account'
            from_email = settings.EMAIL_HOST_USER
            recipient_list = [user.email]
            
            send_email(
                subject=subject,
                message=plain_message,
                from_email=from_email,
                recipient_list=recipient_list,
                html_message=html_message
            )
            
            self.stdout.write(self.style.SUCCESS(f"Welcome email with activation link sent to {user.email}"))
            return True
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Email could not be sent: {str(e)}"))
            return False 