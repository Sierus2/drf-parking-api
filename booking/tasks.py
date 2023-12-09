import json
from time import sleep

from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings

from parking.celery import app
from .models import Booking, BookingSum
from .serializers import BookingSerializer
import xlsxwriter
import datetime
import uuid
import smtplib
from celery.schedules import crontab, schedule

from django_celery_beat.models import PeriodicTask, IntervalSchedule

from celery import Celery
from celery.schedules import crontab


@shared_task
def my_task():
    for i in range(11):
        print(i)
        sleep(1)
    return 'Task complete!'


@shared_task()
def export_to_excel_task(user_id):
    bookings = Booking.objects.select_related('car', 'parking').filter(car__owner=user_id)
    serializer = BookingSerializer(bookings, many=True)

    current_datetime = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    output_filename = f'media/report-{current_datetime}-{uuid.uuid4().hex[:5]}.xlsx'
    workbook = xlsxwriter.Workbook(output_filename)
    worksheet = workbook.add_worksheet()

    headers = ['Автомобил', 'Парковка', 'Бошлаш', 'Якунлаш', 'Сумма']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header)

    for row, data in enumerate(serializer.data, start=1):
        car = data['car']
        parking = data['parking']
        booking_sum = BookingSum.objects.filter(
            booking__car=car, booking__parking=parking,
            booking__start_time=data['start_time'], booking__end_time=data['end_time']
        ).first()

        formatted_start_time = datetime.datetime.strptime(data.get('start_time', ''), '%Y-%m-%dT%H:%M:%SZ').strftime(
            '%Y-%m-%d %H:%M')
        formatted_end_time = datetime.datetime.strptime(data.get('end_time', ''), '%Y-%m-%dT%H:%M:%SZ').strftime(
            '%Y-%m-%d %H:%M')

        worksheet.write(row, 0, 111)
        worksheet.write(row, 1, 222)
        worksheet.write(row, 2, formatted_start_time)
        worksheet.write(row, 3, formatted_end_time)
        worksheet.write(row, 4, booking_sum.sum if booking_sum and booking_sum.sum else '')

    workbook.close()

    # Send email with the Excel file as an attachment using smtplib
    email = EmailMessage(
        'Booking Information',
        'Please find the attached booking information file.',
        settings.EMAIL_HOST_USER,
        [settings.EMAIL_USER],
    )
    with open(output_filename, 'rb') as file:
        email.attach(output_filename, file.read(), 'application/vnd.ms-excel')

    try:
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            server.starttls()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.send_message(email)
            return output_filename
    except Exception as e:
        return str(e)
