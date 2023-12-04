from django.contrib.auth.models import AbstractUser
from django.db import models


# Create your models here.
class User(AbstractUser):
    repeat_password = models.CharField(max_length=255)

    # def save(self, *args, **kwargs):
    #     self.set_password(self.repeat_password)
    #     super().save(*args, **kwargs)
