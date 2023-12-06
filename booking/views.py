import smtplib
from email.mime.base import MIMEBase
from email.mime.text import MIMEText

from rest_framework import viewsets, status, permissions
from rest_framework.authentication import *
from rest_framework.generics import get_object_or_404

from booking.models import Parking, Car, Booking, BaseSum, EmployeeOfParking
from booking.serializers import ParkingSerializer, CarSerializer, BookingSerializer, EmployeeOfParkingSerializer, \
    BaseSumSerializer

from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
import datetime

from parking import settings
from parking.settings import EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_PORT
from user.models import CustomUser
import pandas as pd
import xlsxwriter
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders


# Create your views here.

class CarViewSet(viewsets.ModelViewSet):
    """
    This class defines a set of CRUD operations for the 'Car' model.
    """

    queryset = Car.objects.all()
    serializer_class = CarSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        """
        Retrieves a list of cars owned by the authenticated user.
        Swagger: Retrieve a list of cars owned by the authenticated user.
        """

        user = request.user
        cars = Car.objects.filter(owner=user)

        if not cars.exists():
            return Response(
                {
                    "status": "error",
                    "code": status.HTTP_404_NOT_FOUND,
                    "message": "Cars not found"
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(cars, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):

        """
        Creates a new car instance if the user meets the criteria.
        Swagger: Create a new car instance.
        """

        user = CustomUser.objects.get(username=request.user)
        is_truck = bool(int(request.data.get('is_truck', False)))

        if is_truck:

            count_truck = Car.objects.filter(owner=user, is_truck=True).count()

            if count_truck >= 2:
                return Response(
                    {
                        "status": "error",
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "You have more than 2 truck cars"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            count_car = Car.objects.filter(owner=user, is_truck=False).count()
            print(53, count_car)
            if count_car >= 3:
                return Response(
                    {"status": "error", "code": status.HTTP_400_BAD_REQUEST,
                     "message": "You have more than 3 regular cars"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(owner=user)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieves details of a car instance if the user has permission.
        Swagger: Retrieve details of a car instance.
        """

        instance = self.get_object()
        user = request.user
        if instance.owner != user:
            return Response(
                {"status": "error", "code": status.HTTP_403_FORBIDDEN,
                 "message": "You are not allowed to view this car's information"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Deletes a car instance if the user has permission.
        Swagger: Delete a car instance.
        """

        instance = self.get_object()
        if instance.owner != request.user:
            return Response(
                {"status": "error", "code": status.HTTP_403_FORBIDDEN,
                 "message": "You are not allowed to delete this car"},
                status=status.HTTP_403_FORBIDDEN
            )

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        """
        Updates a car instance if the user meets the criteria.
        Swagger: Update a car instance.
        """

        instance = self.get_object()
        user = request.user
        is_truck = request.data.get('is_truck', instance.is_truck)

        if is_truck != instance.is_truck:
            count_truck = Car.objects.filter(owner=user, is_truck=True).count()
            count_car = Car.objects.filter(owner=user, is_truck=False).count()

            if is_truck and count_truck >= 2:
                return Response(
                    {
                        "status": "error",
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "You have more than 2 truck cars"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif not is_truck and count_car >= 3:
                return Response(
                    {
                        "status": "error",
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "You have more than 3 regular cars"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request):
        # Checking if the request method is POST


        serializer = BookingSerializer(data=request.data)

        if serializer.is_valid():

            # Getting car details from the request data
            car_id = request.data.get('car')
            car = get_object_or_404(Car, pk=car_id)
            print(car)
            print(car_id)
            print(request.user)
            # Checking user's and car's bookings count
            user_bookings_count = Booking.objects.filter(car__owner=request.user).count()
            car_bookings_count = Booking.objects.filter(car=car, ended=False).count()
            is_truck = car.is_truck
            max_car_bookings = 2 if is_truck else 3
            car_type_message = "truck" if is_truck else "regular"

            # Handling booking limit conditions
            if car_bookings_count >= max_car_bookings:
                return Response({
                    "status": "error",
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": f"You have exceeded the maximum {car_type_message} car bookings limit"
                }, status=status.HTTP_400_BAD_REQUEST)

            if user_bookings_count >= 5:
                return Response({
                    "status": "error",
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "You have booked 5 cars already"
                }, status=status.HTTP_400_BAD_REQUEST)

            existing_booking = Booking.objects.filter(car=car, ended=False).first()

            # Checking if the car is already booked
            if existing_booking and existing_booking.end_time > timezone.now():
                return Response({
                    "status": "error",
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "This car is already booked"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Creating a new booking
            start_time = timezone.now()
            end_time = start_time + timezone.timedelta(minutes=180)
            new_booking = serializer.save(car=car, start_time=start_time, end_time=end_time)

            booking_cost_percentage = 0.20 if is_truck else 0.10
            base_sum = BaseSum.objects.first()
            summa = base_sum.sum * booking_cost_percentage

            return Response({
                "status": "success",
                "message": "Booking created successfully",
                "summa": summa
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        car_booking = get_object_or_404(Booking, pk=pk)
        serializer = BookingSerializer(car_booking)
        return Response(serializer.data)

    def calculate_user_profit(self, request):
        # Calculate user's profit based on bookings
        user = request.user
        user_bookings = Booking.objects.filter(user=user)

        total_profit = 0
        for booking in user_bookings:
            # Calculate booking cost and duration
            if booking.car.is_truck:
                booking_cost_percentage = 0.20
            else:
                booking_cost_percentage = 0.10

            booking_duration = (booking.end_time - booking.start_time).seconds / 3600

            # Check if booking duration exceeds the limit
            if booking_duration > 3:
                return Response({
                    "status": "error",
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "You cannot park a car for more than 3 hours"
                }, status=status.HTTP_400_BAD_REQUEST)

            booking_cost = BaseSum.objects.first().sum * booking_cost_percentage * booking_duration
            total_profit += booking_cost

        return Response({
            "status": "success",
            "total_profit": total_profit
        }, status=status.HTTP_200_OK)

    def pre_cancellation(self, request):
        # Pre-cancellation of a booking
        booking_id = request.data.get('booking_id')
        booking = get_object_or_404(Booking, pk=booking_id)

        if booking.car.owner != request.user:
            return Response({
                "status": "error",
                "code": status.HTTP_400_BAD_REQUEST,
                "message": "This booking does not belong to your cars"
            }, status=status.HTTP_400_BAD_REQUEST)

        if booking.ended:
            return Response({
                "status": "error",
                "code": status.HTTP_400_BAD_REQUEST,
                "message": "This booking has already been cancelled"
            }, status=status.HTTP_400_BAD_REQUEST)

        if booking.end_time > timezone.now():
            base_sum = BaseSum.objects.first()
            booking_cost_percentage = 0.10 if booking.car.is_truck else 0.20
            booking_cost = base_sum.sum * booking_cost_percentage

            booking.ended = True
            booking.save()

            # Serialize the booking data
            serializer = BookingSerializer(booking)
            return Response({
                "status": "success",
                "message": "Booking has been cancelled successfully",
                "booking_cost": booking_cost,
                "booking": serializer.data  # Returning the serialized data as JSON
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "status": "error",
                "code": status.HTTP_400_BAD_REQUEST,
                "message": "This booking is already in the parking lot"
            }, status=status.HTTP_400_BAD_REQUEST)

    def create_excel_and_send_email(self, request):
        bookings = Booking.objects.all().values('car__id', 'car__brand', 'car__model', 'car__year', 'start_time',
                                                'end_time', 'parking__title', 'parking__address')  # Ma'lumotlarni olish
        bookings_data = list(bookings)

        # Ma'lumotlarni DataFramega joylash
        df = pd.DataFrame(bookings_data)

        # Excel fayl yaratish
        excel_file = 'avtomobil_kirimlari.xlsx'  # Excel fayl nomini o'zgartiring
        with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)

        # Elektron pochta yuborish
        sender_email = "your_email@example.com"  # Yuboruvchi pochta manzili
        receiver_email = "recipient_email@example.com"  # Qabul qiluvchi pochta manzili
        subject = "Avtomobil Kirimlari"  # Pochta mavzusi
        body = "Ushbu elektron pochta bilan avtomobil kirimlari faylini jo'natyapmiz."

        # Pochta xabarini tuzish
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        # Excel faylni biriktirish va pochta orqali jo'natish
        with open(excel_file, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())

        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {excel_file}",
        )

        message.attach(part)
        text = message.as_string()

        # SMTP server bilan ulashish
        smtp_server = EMAIL_HOST  # SMTP server manzili
        smtp_port = EMAIL_PORT  # SMTP port
        username = EMAIL_HOST_USER  # SMTP server uchun foydalanuvchi nomi
        password = EMAIL_HOST_PASSWORD  # SMTP server uchun parol

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(username, password)
            server.sendmail(sender_email, receiver_email, text)

        return Response({"status": "success", "message": "Excel fayl elektron pochta orqali jo'natildi"},
                        status=status.HTTP_200_OK)


class ParkingViewSet(viewsets.ModelViewSet):
    queryset = Parking.objects.all()  # queryset atributini qo'shish
    serializer_class = ParkingSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):

        user = self.request.user
        check_parking_existence = EmployeeOfParking.objects.filter(user=user, employee=EmployeeOfParking.CEO).exists()

        if not check_parking_existence:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                print(385, serializer.is_valid())
                self.perform_create(serializer)
                employee = EmployeeOfParking.objects.create(
                    user=user,
                    parking=serializer.instance,
                    employee=EmployeeOfParking.CEO
                )
                employee.save()

                response_data = {
                    'status': 'success',
                    'message': 'Parkovka muvaffaqiyatli yaratildi',
                    'data': serializer.data
                }
                return Response(response_data, status=status.HTTP_201_CREATED)

            response_data = {
                'status': 'error',
                'message': 'Xatolik yuz berdi',
                'errors': serializer.errors
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        response_data = {
            'status': 'error',
            'message': 'Sizda allaqachon parking bor va boshqa parking yaratish huquqi yo\'q!'
        }
        return Response(response_data, status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Ma'lumotni o'chirish
        self.perform_destroy(instance)

        # Parkingga bog'liq bo'lgan barcha EmployeeOfParking obyektlarini o'chirish
        related_employees = EmployeeOfParking.objects.filter(parking=instance)
        related_employees.delete()

        return Response(
            {
                'status': 'success',
                'message': 'Ma\'lumot muvaffaqiyatli o\'chirildi'
            },
            status=status.HTTP_204_NO_CONTENT)


class EmployeeOfParkingViewSet(viewsets.ModelViewSet):
    queryset = EmployeeOfParking.objects.all()
    serializer_class = EmployeeOfParkingSerializer

    def create(self, request, *args, **kwargs):
        parking_id = request.data.get('parking')
        ceo_count = EmployeeOfParking.objects.filter(parking_id=parking_id, employee=EmployeeOfParking.CEO).count()

        if ceo_count > 0:
            return Response({
                "status": "error",
                "message": "Faqatgina bitta direktor bo'lishi mumkin"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Ma'lumotlar uchun serializer yaratish va tekshirish
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Ma'lumotlarni saqlash
        self.perform_create(serializer)

        # Muvaffaqiyatli qo'shilgan xodimni JSON formatida qaytarish
        return Response({
            "status": "success",
            "message": "Xodim muvaffaqiyatli qo'shildi",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        # Xodim obyektini olish
        instance = self.get_object()

        # Parking ID sifatida ma'lumotlarni olish
        parking_id = instance.parking_id

        # Direktorlik (CEO) xodimlar sonini hisoblash (hozirgi xodim tashqi)
        ceo_count = EmployeeOfParking.objects.filter(parking_id=parking_id, employee=EmployeeOfParking.CEO).exclude(
            id=instance.id).count()

        # Agar hozirgi xodim direktor bo'lsa va boshqa direktor mavjud bo'lsa, 400 Bad Request xatoligi bilan javob berish
        if instance.employee == EmployeeOfParking.CEO and ceo_count > 0:
            return Response({
                "status": "error",
                "message": "Faqatgina bitta direktor bo'lishi mumkin"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Ma'lumotlar uchun serializer yaratish va tekshirish
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        # Ma'lumotlarni yangilash
        self.perform_update(serializer)

        # Muvaffaqiyatli yangilangan xodimni JSON formatida qaytarish
        return Response({
            "status": "success",
            "message": "Xodim muvaffaqiyatli yangilandi",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


class BaseSumViewSet(viewsets.ModelViewSet):
    queryset = BaseSum.objects.all()
    serializer_class = BaseSumSerializer
    permission_classes = [permissions.IsAdminUser]  # Ruxsat sozlamasi
