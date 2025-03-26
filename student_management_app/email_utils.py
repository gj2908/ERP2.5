from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def generate_activation_token(user):
    """Generate a new activation token for a user"""
    token = get_random_string(length=32)
    user.activation_token = token
    user.activation_token_created = timezone.now()
    user.save()
    return token

def is_activation_token_valid(user):
    """Check if the activation token for a user is still valid (not expired)"""
    if not user.activation_token or not user.activation_token_created:
        return False
    # Token is valid for 24 hours
    return (timezone.now() - user.activation_token_created) < timedelta(hours=24)

def send_activation_email(user, activation_token):
    """
    Send activation email to the user.
    
    Args:
        user: The CustomUser instance
        activation_token: The activation token
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        site_url = settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'
        activation_url = f"{site_url}/activate/{activation_token}/"
        
        context = {
            'user': user,
            'activation_url': activation_url,
            'site_name': settings.SITE_NAME if hasattr(settings, 'SITE_NAME') else 'Student Management System',
        }
        
        # Render HTML email
        html_message = render_to_string('email/activation_email.html', context)
        plain_message = strip_tags(html_message)
        
        # Send email
        subject = 'Activate your account'
        from_email = settings.EMAIL_HOST_USER
        recipient_list = [user.email]
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False
        )
        
        print(f"Activation email sent to {user.email}")
        return True
    except Exception as e:
        print(f"Failed to send activation email: {str(e)}")
        return False

def send_email(subject, message, from_email, recipient_list, html_message=None):
    """
    General function to send an email.
    
    Args:
        subject: Email subject
        message: Plain text message
        from_email: Sender email
        recipient_list: List of recipient emails
        html_message: HTML version of the message (optional)
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False
        )
        print(f"Email sent to {', '.join(recipient_list)}")
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False 