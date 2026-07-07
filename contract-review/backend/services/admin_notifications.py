from logger_config import get_logger
logger = get_logger(__name__)

"""
Admin Notification Service
Sends email notifications to admins when key events occur (e.g., interview completion)
"""

import os
from typing import List, Dict, Any
from database import get_supabase

# Get centralized Supabase client
supabase = get_supabase()

# Optional: Resend API key for email notifications
# If not set, notifications will be logged only
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")

if RESEND_API_KEY:
    try:
        import resend
        resend.api_key = RESEND_API_KEY
        RESEND_AVAILABLE = True
        logger.info("[Admin Notifications] Resend email service configured")
    except ImportError:
        RESEND_AVAILABLE = False
        logger.warning("[Admin Notifications] Resend library not installed. Emails will not be sent.")
        logger.warning("[Admin Notifications] To enable: pip install resend-python")
else:
    RESEND_AVAILABLE = False
    logger.warning("[Admin Notifications] RESEND_API_KEY not set. Email notifications disabled.")


async def get_admin_emails() -> List[str]:
    """
    Get email addresses of all admin users

    Returns:
        List of admin email addresses
    """
    try:
        result = supabase.table('users')\
            .select('email')\
            .eq('role', 'admin')\
            .execute()

        if result.data:
            return [user['email'] for user in result.data if user.get('email')]
        return []
    except Exception as e:
        logger.info(f"[Admin Notifications] Failed to get admin emails: {str(e)}")
        return []


async def send_interview_complete_notification(
    extraction_id: str,
    client_id: str,
    completeness_score: int
) -> Dict[str, Any]:
    """
    Send notification to admins when an interview is completed and ready for review

    Args:
        extraction_id: UUID of interview_extractions record
        client_id: UUID of client record
        completeness_score: Completeness score from Solomon Stage 1 (0-100)

    Returns:
        {
            "success": bool,
            "emails_sent": int,
            "method": "email" | "log_only"
        }
    """

    try:
        # Get user info from interview session
        extraction_result = supabase.table('interview_extractions')\
            .select('metadata')\
            .eq('id', extraction_id)\
            .single()\
            .execute()

        if not extraction_result.data:
            raise ValueError(f"Extraction not found: {extraction_id}")

        import json
        metadata = json.loads(extraction_result.data.get('metadata', '{}'))
        session_id = metadata.get('session_id')

        # Get user details from interview session
        user_name = "Unknown User"
        user_email = ""

        if session_id:
            session_result = supabase.table('interview_sessions')\
                .select('user_id')\
                .eq('session_id', session_id)\
                .single()\
                .execute()

            if session_result.data:
                user_id = session_result.data['user_id']
                user_result = supabase.table('users')\
                    .select('name, email')\
                    .eq('id', user_id)\
                    .single()\
                    .execute()

                if user_result.data:
                    user_name = user_result.data.get('name', 'Unknown User')
                    user_email = user_result.data.get('email', '')

        # Get frontend URL for review dashboard link
        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
        if ',' in frontend_url:
            # If multiple URLs, use the first production one
            urls = [u.strip() for u in frontend_url.split(',')]
            frontend_url = next((u for u in urls if 'localhost' not in u), urls[0])

        review_url = f"{frontend_url}/admin/solomon-review"

        # Prepare email content
        subject = f"🎯 Interview Complete: {user_name} - Ready for Review"

        html_body = f"""
        <h2>Interview Completed Successfully</h2>

        <p>A new interview has been completed and is ready for your review.</p>

        <h3>Interview Details:</h3>
        <ul>
            <li><strong>User:</strong> {user_name}</li>
            <li><strong>Email:</strong> {user_email}</li>
            <li><strong>Completeness Score:</strong> {completeness_score}%</li>
        </ul>

        <h3>Next Steps:</h3>
        <ol>
            <li>Review the extracted data and generated system instructions</li>
            <li>Verify the configuration matches the interview transcript</li>
            <li>Approve and deploy to make the personalized assistant live</li>
        </ol>

        <p>
            <a href="{review_url}" style="display: inline-block; padding: 12px 24px; background-color: #4F46E5; color: white; text-decoration: none; border-radius: 6px; font-weight: 600;">
                Review Now
            </a>
        </p>

        <hr style="margin: 24px 0; border: none; border-top: 1px solid #E5E7EB;">

        <p style="color: #6B7280; font-size: 14px;">
            This is an automated notification from SuperAssistant.
            <a href="{review_url}">View Solomon Review Dashboard</a>
        </p>
        """

        text_body = f"""
Interview Completed Successfully

A new interview has been completed and is ready for your review.

Interview Details:
- User: {user_name}
- Email: {user_email}
- Completeness Score: {completeness_score}%

Next Steps:
1. Review the extracted data and generated system instructions
2. Verify the configuration matches the interview transcript
3. Approve and deploy to make the personalized assistant live

Review Now: {review_url}

---
This is an automated notification from SuperAssistant.
View Solomon Review Dashboard: {review_url}
        """

        # Get admin emails
        admin_emails = await get_admin_emails()

        if not admin_emails:
            print("[Admin Notifications] No admin users found")
            return {
                "success": False,
                "emails_sent": 0,
                "method": "none",
                "error": "No admin users found"
            }

        # Send email via Resend if available
        if RESEND_AVAILABLE:
            try:
                from_email = os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev")

                emails_sent = 0
                for admin_email in admin_emails:
                    try:
                        resend.Emails.send({
                            "from": from_email,
                            "to": admin_email,
                            "subject": subject,
                            "html": html_body,
                            "text": text_body
                        })
                        emails_sent += 1
                        logger.info(f"[Admin Notifications] Email sent to: {admin_email}")
                    except Exception as email_error:
                        logger.error(f"[Admin Notifications] Failed to send to {admin_email}: {str(email_error)}")

                return {
                    "success": emails_sent > 0,
                    "emails_sent": emails_sent,
                    "method": "email"
                }

            except Exception as e:
                logger.error(f"[Admin Notifications] Resend email failed: {str(e)}")
                # Fall through to log-only mode

        # Fallback: Log notification details
        print("=" * 80)
        print("[Admin Notifications] EMAIL NOTIFICATION (Log Only)")
        print("=" * 80)
        logger.info(f"To: {', '.join(admin_emails)}")
        logger.info(f"Subject: {subject}")
        print("-" * 80)
        print(text_body)
        print("=" * 80)

        return {
            "success": True,
            "emails_sent": 0,
            "method": "log_only",
            "admin_emails": admin_emails
        }

    except Exception as e:
        error_msg = f"Failed to send admin notification: {str(e)}"
        logger.error(f"[Admin Notifications] ERROR: {error_msg}")
        return {
            "success": False,
            "emails_sent": 0,
            "method": "error",
            "error": error_msg
        }
