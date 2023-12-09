import json
from email.mime.text import MIMEText

from django.http import HttpResponse
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from .tasks import export_to_excel_task
from rest_framework import viewsets, status, permissions
from rest_framework.generics import get_object_or_404

from booking.models import Parking, Car, Booking, BaseSum, EmployeeOfParking, BookingSum
from booking.serializers import ParkingSerializer, CarSerializer, BookingSerializer, EmployeeOfParkingSerializer, \
    BaseSumSerializer

from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
import datetime

from parking.settings import EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_PORT
from user.models import CustomUser
import pandas as pd

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from django.shortcuts import render


def google_login(request):
    return render(request, template_name='oauth/google_login.html')


def landing_page(request):
    return render(request, 'landing.html')


def schedule_tasks(request):
    interval, _ = IntervalSchedule.objects.get_or_create(
        every=30,
        period=IntervalSchedule.SECONDS,
    )
    PeriodicTask.objects.create(
        interval=interval,
        name='my-schedule',
        task='booking.tasks.my_task'

    )

    return HttpResponse('Task scheduled!')


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
        serializer = BookingSerializer(data=request.data)

        if serializer.is_valid():
            car_id = request.data.get('car')
            car = get_object_or_404(Car, pk=car_id)

            parking_id = request.data.get('parking')
            parking = get_object_or_404(Parking, pk=parking_id)

            if car.owner != request.user:
                return Response({
                    "status": "error",
                    "code": status.HTTP_403_FORBIDDEN,
                    "message": "You do not have permission to book this car!"
                }, status=status.HTTP_403_FORBIDDEN)

            start_time = request.data.get('start_time')
            end_time = request.data.get('end_time')
            print(start_time)
            print(end_time)
            start_time_obj = datetime.datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
            end_time_obj = datetime.datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%SZ")
            time_diff = end_time_obj - start_time_obj
            if time_diff > datetime.timedelta(minutes=180):
                return Response({
                    "status": "error",
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "You can not book the parking lot for more than 3 hours!"
                }, status=status.HTTP_400_BAD_REQUEST)

            if time_diff.total_seconds() < 10:  # 10 daqiqadan kichik bo'lsa
                return Response({
                    "status": "error",
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "The booking time should be at least 10 minutes"
                }, status=status.HTTP_400_BAD_REQUEST)

            is_truck = car.is_truck

            existing_bookings = Booking.objects.filter(
                parking=parking,
                end_time__gt=start_time,
                start_time__lt=end_time
            )
            total_spots = parking.total_spots
            booked_spots = existing_bookings.count()
            print(booked_spots)
            print(total_spots)

            print(total_spots - booked_spots)
            if booked_spots >= total_spots:
                return Response({
                    "status": "error",
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "The Parking is not available during the given time"
                }, status=status.HTTP_400_BAD_REQUEST)

            existing_booking = Booking.objects.filter(
                car=car,
                end_time__gt=start_time,
                start_time__lt=end_time
            ).first()

            if existing_booking:
                return Response({
                    "status": "error",
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "At this time, the car has already been booked"
                }, status=status.HTTP_400_BAD_REQUEST)

            new_booking = serializer.save(car=car, start_time=start_time, end_time=end_time)
            serialized_booking = BookingSerializer(new_booking)

            hourly_rate = 0.20 if car.is_truck else 0.10  # Avtomobilni aniqlash va foizni biriktirish
            total_hours = time_diff.total_seconds() / 3600  # bir soatni narxini chiqarish
            base_sum = BaseSum.objects.first()
            summa = int(hourly_rate * total_hours * base_sum.sum)

            BookingSum.objects.create(booking=new_booking, base_sum=base_sum, sum=summa)

            return Response({
                "status": "success",
                "message": "Booking created successfully",
                "summa": summa,
                'booking': serialized_booking.data
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

        if booking.end_time > timezone.now():
            base_sum = BaseSum.objects.first()
            booking_cost_percentage = 0.10 if booking.car.is_truck else 0.20
            booking_cost = base_sum.sum * booking_cost_percentage

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


class ReportViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BookingSerializer
    queryset = Booking.objects.all()

    def list(self, request):
        user = request.user
        queryset = self.get_queryset().filter(car__owner=user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def export_to_excel(self, request):
        user_id = request.user.id  # Foydalanuvchi identifikatori
        export_to_excel_task.delay(user_id)  # Celery taskini ishga tushiramiz
        return Response("Export task has been queued.")  # Taskning ishga tushirilishini xabar beramiz

    # def export_to_excel(self, request):
    #     user = request.user
    #     queryset = self.get_queryset().filter(car__owner=user)
    #     serializer = self.get_serializer(queryset, many=True)
    #
    #     # Creating a new Excel file
    #     output_filename = f'media/{uuid.uuid4()}.xlsx'
    #     workbook = xlsxwriter.Workbook(output_filename)
    #     worksheet = workbook.add_worksheet()
    #
    #     # Write header row
    #     headers = ['Автомобил', 'Парковка', 'Бошлаш', 'Якунлаш', 'Сумма']
    #     for col, header in enumerate(headers):
    #         worksheet.write(0, col, header)
    #
    #     # Write data rows
    #     for row, data in enumerate(serializer.data, start=1):
    #         print(data)
    #         car = Car.objects.get(pk=data['car'])
    #         parking = Parking.objects.get(pk=data['parking'])
    #         booking_sum = BookingSum.objects.filter(
    #             booking__car=car, booking__parking=parking, booking__start_time=data['start_time'],
    #             booking__end_time=data['end_time']).first()  # Get BookingSum object related to the current Booking
    #
    #         start_time = data.get('start_time', '')
    #         formatted_start_time = datetime.datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%SZ')
    #         formatted_start_date_for_excel = formatted_start_time.strftime('%Y-%m-%d %H:%M')
    #
    #         end_time = data.get('end_time', '')
    #         formatted_end_time = datetime.datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%SZ')
    #         formatted_end_date_for_excel = formatted_end_time.strftime('%Y-%m-%d %H:%M')
    #         print(formatted_start_time)
    #
    #         worksheet.write(row, 0, car.model)
    #         worksheet.write(row, 1, parking.title)
    #         worksheet.write(row, 2, formatted_start_date_for_excel)
    #         worksheet.write(row, 3, formatted_end_date_for_excel)
    #         worksheet.write(row, 4, booking_sum.sum if booking_sum.sum else '')  # Writing BookingSum sum if available
    #
    #     workbook.close()
    #
    #     # Returning a response to download the Excel file
    #     with open(output_filename, 'rb') as file:
    #         response = HttpResponse(file.read(), content_type='application/vnd.ms-excel')
    #         response['Content-Disposition'] = 'attachment; filename=' + output_filename
    #         return response
    #         # return Response({
    #         #     "status": "success",
    #         #     "message": "Excel file has been generated successfully",
    #         #     "download_link": f"http://127.0.0.1:8000/{output_filename}"  # Masalan, fayl yuklab olish uchun link
    #         # }, status=status.HTTP_200_OK)
