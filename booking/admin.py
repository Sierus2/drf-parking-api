from django.contrib import admin

from booking.models import Car, EmployeeOfParking, Parking, Booking, BaseSum

# Register your models here.
admin.site.register(Car)
admin.site.register(EmployeeOfParking)
admin.site.register(Parking)
admin.site.register(Booking)
admin.site.register(BaseSum)
