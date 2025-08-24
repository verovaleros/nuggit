"""
Email service for sending authentication-related emails.

This module provides functionality for sending verification emails,
password reset emails, and other notifications using SMTP.
"""

import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from pathlib import Path
import os
from jinja2 import Environment, FileSystemLoader, Template

logger = logging.getLogger(__name__)


class EmailConfig:
    """Email configuration settings."""
    
    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST', 'localhost')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.smtp_use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
        self.smtp_use_ssl = os.getenv('SMTP_USE_SSL', 'false').lower() == 'true'
        self.from_email = os.getenv('FROM_EMAIL', 'noreply@nuggit.app')
        self.from_name = os.getenv('FROM_NAME', 'Nuggit')
        self.base_url = os.getenv('BASE_URL', 'http://localhost:5173')
        
    @property
    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return bool(self.smtp_host and self.smtp_username and self.smtp_password)


class EmailService:
    """Service for sending emails."""
    
    def __init__(self, config: Optional[EmailConfig] = None):
        self.config = config or EmailConfig()
        self.template_dir = Path(__file__).parent.parent / "templates" / "email"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True
        )
        
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send an email asynchronously.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text email content (optional)
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not self.config.is_configured:
            logger.warning("Email service not configured, skipping email send")
            return False
            
        try:
            # Run email sending in thread pool to avoid blocking
            return await asyncio.to_thread(
                self._send_email_sync,
                to_email,
                subject,
                html_content,
                text_content
            )
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def _send_email_sync(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send email synchronously."""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.config.from_name} <{self.config.from_email}>"
            msg['To'] = to_email
            
            # Add text content
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            if self.config.smtp_use_ssl:
                server = smtplib.SMTP_SSL(self.config.smtp_host, self.config.smtp_port)
            else:
                server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
                if self.config.smtp_use_tls:
                    server.starttls()
            
            if self.config.smtp_username and self.config.smtp_password:
                server.login(self.config.smtp_username, self.config.smtp_password)
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render email template with context."""
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            raise
    
    async def send_verification_email(
        self,
        to_email: str,
        username: str,
        verification_token: str
    ) -> bool:
        """
        Send email verification email.
        
        Args:
            to_email: User email address
            username: Username
            verification_token: Email verification token
            
        Returns:
            bool: True if email was sent successfully
        """
        verification_url = f"{self.config.base_url}/verify-email?token={verification_token}"
        
        context = {
            'username': username,
            'verification_url': verification_url,
            'base_url': self.config.base_url
        }
        
        try:
            html_content = self._render_template('verification.html', context)
            text_content = self._render_template('verification.txt', context)
        except Exception:
            # Fallback to simple templates if files don't exist
            html_content = self._get_verification_html_fallback(username, verification_url)
            text_content = self._get_verification_text_fallback(username, verification_url)
        
        return await self.send_email(
            to_email=to_email,
            subject="Verify your Nuggit account",
            html_content=html_content,
            text_content=text_content
        )
    
    async def send_password_reset_email(
        self,
        to_email: str,
        username: str,
        reset_token: str
    ) -> bool:
        """
        Send password reset email.
        
        Args:
            to_email: User email address
            username: Username
            reset_token: Password reset token
            
        Returns:
            bool: True if email was sent successfully
        """
        reset_url = f"{self.config.base_url}/reset-password?token={reset_token}"
        
        context = {
            'username': username,
            'reset_url': reset_url,
            'base_url': self.config.base_url
        }
        
        try:
            html_content = self._render_template('password_reset.html', context)
            text_content = self._render_template('password_reset.txt', context)
        except Exception:
            # Fallback to simple templates if files don't exist
            html_content = self._get_password_reset_html_fallback(username, reset_url)
            text_content = self._get_password_reset_text_fallback(username, reset_url)
        
        return await self.send_email(
            to_email=to_email,
            subject="Reset your Nuggit password",
            html_content=html_content,
            text_content=text_content
        )
    
    def _get_verification_html_fallback(self, username: str, verification_url: str) -> str:
        """Fallback HTML template for email verification."""
        return f"""
        <html>
        <body>
            <h2>Welcome to Nuggit, {username}!</h2>
            <p>Please verify your email address by clicking the link below:</p>
            <p><a href="{verification_url}">Verify Email Address</a></p>
            <p>If you didn't create this account, you can safely ignore this email.</p>
            <p>Best regards,<br>The Nuggit Team</p>
        </body>
        </html>
        """
    
    def _get_verification_text_fallback(self, username: str, verification_url: str) -> str:
        """Fallback text template for email verification."""
        return f"""
        Welcome to Nuggit, {username}!
        
        Please verify your email address by visiting this link:
        {verification_url}
        
        If you didn't create this account, you can safely ignore this email.
        
        Best regards,
        The Nuggit Team
        """
    
    def _get_password_reset_html_fallback(self, username: str, reset_url: str) -> str:
        """Fallback HTML template for password reset."""
        return f"""
        <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>Hello {username},</p>
            <p>You requested a password reset for your Nuggit account. Click the link below to reset your password:</p>
            <p><a href="{reset_url}">Reset Password</a></p>
            <p>This link will expire in 1 hour. If you didn't request this reset, you can safely ignore this email.</p>
            <p>Best regards,<br>The Nuggit Team</p>
        </body>
        </html>
        """
    
    def _get_password_reset_text_fallback(self, username: str, reset_url: str) -> str:
        """Fallback text template for password reset."""
        return f"""
        Password Reset Request
        
        Hello {username},
        
        You requested a password reset for your Nuggit account. Visit this link to reset your password:
        {reset_url}
        
        This link will expire in 1 hour. If you didn't request this reset, you can safely ignore this email.
        
        Best regards,
        The Nuggit Team
        """


# Global email service instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get the global email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
