import requests
from django.core.exceptions import ValidationError


def check_email_has(email):
    print(47, 'aaa')
    response = requests.get(
        f"https://emailvalidation.abstractapi.com/v1/?api_key=8b42a7c0685e43e2bdeb85e13b30eb49&email={email}")
    if response.status_code == 200:
        return True
    else:
        return False


class CustomPasswordValidator:
    def validate(self, password, user=None):
        if len(password) < 8:
            raise ValidationError(("The password must be at least 8 characters long."), code='password_too_short')

        # Check for at least 1 lowercase letter
        if not any(char.islower() for char in password):
            raise ValidationError(("The password must contain at least one lowercase letter."),
                                  code='password_no_lowercase')

        # Check for at least 1 uppercase letter
        if not any(char.isupper() for char in password):
            raise ValidationError(("The password must contain at least one uppercase letter."),
                                  code='password_no_uppercase')

        if not any(char.isdigit() for char in password):
            raise ValidationError(("The password must contain at least one digit."), code='password_no_digit')

        initials_count = sum(1 for char in password if char.isalpha() and char.isupper())

        if initials_count < 2:
            raise ValidationError(("The password must contain at least 2 uppercase initials."),
                                  code='password_insufficient_initials')

    def get_help_text(self):
        return (
            "Your password must be at least 8 characters long, and contain "
            "at least one uppercase letter, one lowercase letter, one digit, "
            "and at least 2 uppercase initials."
        )
