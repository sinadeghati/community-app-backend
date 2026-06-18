from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Signed token for email verification — separate from password reset tokens."""

    def _make_hash_value(self, user, timestamp):
        email = user.email or ""
        return f"{user.pk}{email}{timestamp}{user.is_active}"


email_verification_token_generator = EmailVerificationTokenGenerator()
