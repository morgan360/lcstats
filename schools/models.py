from django.db import models
from django.contrib.auth.models import User


class School(models.Model):
    """Model to store secondary school contact information for outreach campaigns."""

    SCHOOL_TYPE_CHOICES = [
        ('secondary', 'Secondary School'),
        ('community', 'Community College'),
        ('vocational', 'Vocational School'),
        ('comprehensive', 'Comprehensive School'),
        ('etb', 'ETB School'),
    ]

    # Basic Information
    name = models.CharField(max_length=200, help_text="Full name of the school")
    principal_name = models.CharField(max_length=200, help_text="Principal's full name")
    email = models.EmailField(help_text="Primary contact email")
    phone = models.CharField(max_length=20, blank=True, help_text="Contact phone number")
    website = models.URLField(blank=True, help_text="School website URL")

    # Secondary Contact (Maths Teacher / Career Guidance)
    secondary_contact_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Name of maths teacher, career guidance counsellor, or other contact"
    )
    secondary_contact_role = models.CharField(
        max_length=100,
        blank=True,
        help_text="Role/position (e.g., 'Maths Teacher', 'Career Guidance Counsellor')"
    )
    secondary_contact_email = models.EmailField(
        blank=True,
        help_text="Email for secondary contact (if different from principal)"
    )

    # Language / Gaelscoil
    is_gaelscoil = models.BooleanField(
        default=False,
        help_text="Is this an Irish-speaking school (Gaelscoil)?"
    )

    # Location
    address = models.TextField(blank=True, help_text="Full postal address")
    county = models.CharField(max_length=100, blank=True, help_text="County location")

    # School Details
    school_type = models.CharField(
        max_length=50,
        choices=SCHOOL_TYPE_CHOICES,
        default='secondary',
        help_text="Type of school"
    )
    roll_number = models.CharField(max_length=20, blank=True, help_text="Department of Education roll number")

    # Outreach Tracking
    initial_email_sent = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the initial outreach email was sent"
    )
    response_received = models.BooleanField(
        default=False,
        help_text="Has the school responded to our outreach?"
    )
    response_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When we received a response"
    )
    follow_up_required = models.BooleanField(
        default=False,
        help_text="Does this contact need a follow-up?"
    )
    follow_up_date = models.DateField(
        null=True,
        blank=True,
        help_text="Scheduled follow-up date"
    )

    # Additional Information
    notes = models.TextField(
        blank=True,
        help_text="Internal notes about communication with this school"
    )
    interested = models.BooleanField(
        default=False,
        help_text="School expressed interest in NumScoil"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['county', 'name']
        verbose_name = 'School'
        verbose_name_plural = 'Schools'

    def __str__(self):
        return f"{self.name} ({self.county})"


class EmailLog(models.Model):
    """Model to track all emails sent to schools for outreach campaigns."""

    EMAIL_TYPE_CHOICES = [
        ('initial', 'Initial Outreach'),
        ('follow_up', 'Follow-up'),
        ('reminder', 'Reminder'),
        ('custom', 'Custom'),
    ]

    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
    ]

    # Email Details
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='email_logs',
        help_text="School this email was sent to"
    )
    email_type = models.CharField(
        max_length=20,
        choices=EMAIL_TYPE_CHOICES,
        default='initial',
        help_text="Type of outreach email"
    )
    subject = models.CharField(max_length=200, help_text="Email subject line")
    body_text = models.TextField(help_text="Plain text version of email body")
    body_html = models.TextField(blank=True, help_text="HTML version of email body")

    # Sending Details
    sent_to = models.EmailField(help_text="Email address this was sent to")
    sent_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text="User who sent this email"
    )
    sent_at = models.DateTimeField(auto_now_add=True, help_text="When the email was sent")

    # Status Tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='sent',
        help_text="Email delivery status"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if sending failed"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'

    def __str__(self):
        return f"{self.email_type} to {self.school.name} on {self.sent_at.strftime('%Y-%m-%d %H:%M')}"
