from django.contrib import admin

from booking.models import *

# Register your models here.
admin.site.register(Car)
admin.site.register(EmployeeOfParking)
admin.site.register(Parking)
admin.site.register(Booking)
admin.site.register(BaseSum)
admin.site.register(BookingSum)
