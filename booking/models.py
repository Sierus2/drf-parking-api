from django.db import models

from parking import settings
from user.models import CustomUser


# Create your models here.
class Parking(models.Model):
    title = models.CharField(max_length=70)
    address = models.CharField(max_length=255)
    total_spots = models.IntegerField(default=0)  # Umumiy joylar soni


class EmployeeOfParking(models.Model):
    SECURITY = 0
    CEO = 1

    EMPLOYEE_CHOICES = [
        (SECURITY, "Qorovul"),
        (CEO, "Director"),
    ]

    employee = models.IntegerField(choices=EMPLOYEE_CHOICES, default=SECURITY)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    parking = models.ForeignKey(Parking, on_delete=models.CASCADE)


class Car(models.Model):
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.IntegerField()
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    is_truck = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.owner.username} | {self.brand} {self.model} ({self.year})"


class UserToCar(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='driver_to_user')
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='car_to_user')


class Booking(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='booking_to_car')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    ended = models.BooleanField(default=False)
    parking = models.ForeignKey(Parking, on_delete=models.CASCADE, related_name='booking_to_parking')


class BaseSum(models.Model):
    sum = models.IntegerField()
