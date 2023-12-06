import requests
from django.core.exceptions import ValidationError
from rest_framework.response import Response


def check_email_has(email):
    response = requests.get(
        f"https://emailvalidation.abstractapi.com/v1/?api_key=8b42a7c0685e43e2bdeb85e13b30eb49&email={email}")
    if response.status_code == 200:
        return True
    else:
        return False


class CustomPasswordValidator:
    def validate_password(self, password):
        if len(password) < 8:
            raise ValidationError(
                message="The password must be at least 8 characters long.",
                code='password_too_short',
                params={'value': password},
            )

        if not any(char.islower() for char in password):
            raise ValidationError(
                message="The password must contain at least one lowercase letter.",
                code='password_no_lowercase',
                params={'value': password},
            )

        if not any(char.isupper() for char in password):
            raise ValidationError(
                message="The password must contain at least one uppercase letter.",
                code='password_no_uppercase',
                params={'value': password},
            )

        if not any(char.isdigit() for char in password):
            raise ValidationError(
                message="The password must contain at least one digit.",
                code='password_no_digit',
                params={'value': password},
            )

        initials_count = sum(1 for char in password if char.isalpha() and char.isupper())

        if initials_count < 2:
            raise ValidationError(
                message="The password must contain at least 2 uppercase initials.",
                code='password_insufficient_initials',
                params={'value': password},
            )

    def get_help_text(self):
        return (
            "Your password must be at least 8 characters long, and contain "
            "at least one uppercase letter, one lowercase letter, one digit, "
            "and at least 2 uppercase initials."
        )
