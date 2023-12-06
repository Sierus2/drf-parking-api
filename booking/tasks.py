# tasks.py yoki mos nomlangan fayl

from celery import shared_task
from django.http import HttpResponse
from .models import Car, Parking, BookingSum
from .serializers import BookingSerializer
import xlsxwriter
import datetime
import uuid

@shared_task
def export_to_excel_task(user_id):
    queryset = Booking.objects.filter(car__owner=user_id)
    serializer = BookingSerializer(queryset, many=True)

    output_filename = f'media/{uuid.uuid4()}.xlsx'
    workbook = xlsxwriter.Workbook(output_filename)
    worksheet = workbook.add_worksheet()

    # Write header row
    headers = ['Автомобил', 'Парковка', 'Бошлаш', 'Якунлаш', 'Сумма']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header)

    # Write data rows
    for row, data in enumerate(serializer.data, start=1):
        car = Car.objects.get(pk=data['car'])
        parking = Parking.objects.get(pk=data['parking'])
        booking_sum = BookingSum.objects.filter(
            booking__car=car, booking__parking=parking, booking__start_time=data['start_time'],
            booking__end_time=data['end_time']
        ).first()

        start_time = data.get('start_time', '')
        formatted_start_time = datetime.datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%SZ')
        formatted_start_date_for_excel = formatted_start_time.strftime('%Y-%m-%d %H:%M')

        end_time = data.get('end_time', '')
        formatted_end_time = datetime.datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%SZ')
        formatted_end_date_for_excel = formatted_end_time.strftime('%Y-%m-%d %H:%M')

        worksheet.write(row, 0, car.model)
        worksheet.write(row, 1, parking.title)
        worksheet.write(row, 2, formatted_start_date_for_excel)
        worksheet.write(row, 3, formatted_end_date_for_excel)
        worksheet.write(row, 4, booking_sum.sum if booking_sum.sum else '')

    workbook.close()

    with open(output_filename, 'rb') as file:
        response = HttpResponse(file.read(), content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=' + output_filename
        return response
