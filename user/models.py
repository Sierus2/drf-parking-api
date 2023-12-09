from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser
from django.db import models

from user.utils import CustomPasswordValidator


class CustomUser(AbstractUser):
    repeat_password = models.CharField(max_length=255)
    photo = models.ImageField(upload_to='images/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.pk is None:  # Agar yangi obyekt (yangi foydalanuvchi) qo'shilayotgan bo'lsa
            validator = CustomPasswordValidator()
            validator.validate_password(self.repeat_password)  # Parolni tekshiramiz
            self.password = make_password(self.repeat_password)  # Parolni hash qilamiz
        super().save(*args, **kwargs)  # Ma'lumotlar bazasiga saqlash
