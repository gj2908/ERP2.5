from django.core.mail import EmailMultiAlternatives, get_connection, send_mail
from django.conf import settings
import logging
import re
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import secrets
from datetime import datetime, timedelta
import random
import string

logger = logging.getLogger(__name__)

def get_email_connection():
    """Get email connection using settings from .env file"""
    try:
        connection = get_connection(
            backend=settings.EMAIL_BACKEND,
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_HOST_USER,
            password=settings.EMAIL_HOST_PASSWORD,
            use_tls=settings.EMAIL_USE_TLS
        )
        return connection
    except Exception as e:
        logger.error(f"Error creating email connection: {str(e)}")
        return None

def send_email(subject, body, to_emails, html_content=None, fail_silently=True):
    """
    Send an email using settings from .env file
    
    Args:
        subject (str): Email subject
        body (str): Plain text email body
        to_emails (list): List of recipient email addresses
        html_content (str, optional): HTML content for the email
        fail_silently (bool, optional): Whether to raise exceptions on failure
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Validate email settings first
        if not settings.EMAIL_HOST or not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            logger.error("Missing email configuration. Please check your EMAIL_HOST, EMAIL_HOST_USER, and EMAIL_HOST_PASSWORD settings.")
            print("Missing email configuration. Please check your EMAIL_HOST, EMAIL_HOST_USER, and EMAIL_HOST_PASSWORD settings.")
            return False
        
        # Get connection using .env settings
        connection = get_email_connection()
        if not connection:
            logger.error("Failed to establish email connection. Check your email settings in .env file.")
            print("Failed to establish email connection. Check your email settings in .env file.")
            return False
            
        # Create the email message
        from_email = settings.EMAIL_HOST_USER
        
        # Convert single email to list if needed
        recipient_list = to_emails if isinstance(to_emails, list) else [to_emails]
        
        # Log email details (excluding sensitive content)
        logger.info(f"Sending email to: {recipient_list}, Subject: {subject}")
        print(f"Attempting to send email to: {recipient_list}, Subject: {subject}")
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=from_email,
            to=recipient_list,
            connection=connection
        )
        
        # Add HTML content if provided
        if html_content:
            email.content_subtype = "html"
            email.attach_alternative(html_content, "text/html")
            
        # Send the email
        email.send(fail_silently=fail_silently)
        logger.info(f"Email sent successfully to: {recipient_list}")
        print(f"Email sent successfully to: {recipient_list}")
        return True
        
    except Exception as e:
        error_msg = f"Error sending email: {str(e)}"
        logger.error(error_msg)
        print(error_msg)
        # Log email settings (without password)
        logger.error(f"Email settings: HOST={settings.EMAIL_HOST}, PORT={settings.EMAIL_PORT}, USER={settings.EMAIL_HOST_USER}, TLS={settings.EMAIL_USE_TLS}")
        print(f"Email settings: HOST={settings.EMAIL_HOST}, PORT={settings.EMAIL_PORT}, USER={settings.EMAIL_HOST_USER}, TLS={settings.EMAIL_USE_TLS}")
        return False

def log_user_activity(user, action, ip_address=None, user_agent=None, target_model=None, target_id=None, target_detail=None, extra_data=None):
    """
    Utility function to manually log user activities
    
    Args:
        user: CustomUser instance
        action: String representing the action type ('login', 'logout', etc.)
        ip_address: Client IP address (optional)
        user_agent: Client user agent string (optional)
        target_model: Name of the model being acted upon (optional)
        target_id: ID of the object being acted upon (optional)
        target_detail: Additional detail about the action (optional)
        extra_data: Dictionary of additional data to log (optional)
    
    Returns:
        UserActivity instance that was created
    """
    # Avoid circular imports
    from student_management_app.models import UserActivity
    
    # Create activity log
    activity = UserActivity.objects.create(
        user=user,
        action=action,
        ip_address=ip_address,
        user_agent=user_agent,
        target_model=target_model,
        target_id=target_id,
        target_detail=target_detail,
        extra_data=extra_data
    )
    
    return activity 

def generate_activation_token():
    """Generate a secure random token for account activation"""
    return secrets.token_urlsafe(32)

def is_activation_token_valid(user):
    """Check if the activation token is still valid (not older than 24 hours)"""
    if not user.activation_token_created:
        return False
    expiry_time = user.activation_token_created + timedelta(hours=24)
    return datetime.now().timestamp() < expiry_time.timestamp()

def send_activation_email(user, request):
    """Send activation email to user"""
    # Generate activation token if not exists
    if not user.activation_token:
        user.activation_token = generate_activation_token()
        user.activation_token_created = datetime.now()
        user.save()

    # Build activation link with full URL
    protocol = 'https' if request.is_secure() else 'http'
    domain = settings.DOMAIN_NAME
    activation_link = f"{protocol}://{domain}/activate/{user.activation_token}/"

    # Create plain text message
    plain_message = f"""Hello {user.first_name},

Your account has been created. Please click the link below to activate your account and set your password:

{activation_link}

This link will expire in 24 hours.

If you did not create this account, please ignore this email.

Best regards,
SRM Institute of Science and Technology"""

    # Render HTML template
    context = {
        'user': user,
        'activation_link': activation_link,
        'protocol': protocol,
        'domain': domain
    }
    html_message = render_to_string('email/account_activation.html', context)

    # Send email
    send_mail(
        'Activate your SRM Institute Account',
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )

def send_admin_notification_email(user, request):
    """Send notification email to admin about account creation"""
    # Build context
    protocol = 'https' if request and request.is_secure() else 'http'
    domain = request.get_host() if request else settings.ALLOWED_HOSTS[0]
    
    context = {
        'user': user,
        'protocol': protocol,
        'domain': domain
    }
    html_message = render_to_string('email/admin_account_notification.html', context)
    plain_message = strip_tags(html_message)

    # Send email
    send_email(
        subject='Your SRMIST Administrator Account Has Been Created',
        body=plain_message,
        to_emails=user.email,
        html_content=html_message,
        fail_silently=False
    )

def generate_random_password():
    """Generate a random password that meets requirements"""
    # Define character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special_chars = "!@#$%^&*(),.?\":{}|<>"
    
    # Generate password with at least one from each category
    password = [
        random.choice(lowercase),
        random.choice(uppercase),
        random.choice(digits),
        random.choice(special_chars)
    ]
    
    # Add more random characters to meet length requirement (at least 8 chars)
    all_chars = lowercase + uppercase + digits + special_chars
    password.extend(random.choice(all_chars) for _ in range(4))
    
    # Shuffle the password characters
    random.shuffle(password)
    
    # Convert list to string
    return ''.join(password)

def send_account_credentials_email(user, password, request=None):
    """Send email with account credentials to a new user"""
    try:
        protocol = 'https' if request and request.is_secure() else 'http'
        domain = request.get_host() if request else settings.ALLOWED_HOSTS[0]
        login_url = f"{protocol}://{domain}"
        
        # Determine user type and select appropriate template
        if user.user_type == "1":
            user_type_str = "Administrator"
            template_name = 'email/welcome_admin.html'
        elif user.user_type == "2":
            user_type_str = "Staff"
            template_name = 'email/welcome_staff.html'
        elif user.user_type == "3":
            user_type_str = "Student"
            template_name = 'email/welcome_student.html'
        else:
            user_type_str = "User"
            template_name = 'email/account_credentials.html'
        
        # Get current year for copyright in footer
        current_year = datetime.now().year
        
        context = {
            'user': user,
            'password': password,
            'login_url': login_url,
            'user_type': user_type_str,
            'current_year': current_year
        }
        
        # Log which template is being used
        print(f"Using email template: {template_name} for user type: {user_type_str}")
        
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)
        
        # Send email
        result = send_email(
            subject=f'Welcome to SRM Institute Student Portal - Your {user_type_str} Account Details',
            body=plain_message,
            to_emails=user.email,
            html_content=html_message,
            fail_silently=False
        )
        
        return result
    except Exception as e:
        logger.error(f"Error in send_account_credentials_email: {str(e)}")
        print(f"Error in send_account_credentials_email: {str(e)}")
        return False 