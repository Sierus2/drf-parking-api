from rest_framework import serializers

from booking.models import Parking, Booking, UserToCar, Car, BaseSum, EmployeeOfParking


class ParkingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parking
        fields = '__all__'


class EmployeeOfParkingSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeOfParking
        fields = '__all__'


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['car', 'start_time', 'end_time', 'parking']
        # read_only_fields = ['car', ]  # Majburiy emasligini aniqlash

    def validate(self, data):
        if data.get('start_time') and data.get('end_time'):
            if data['start_time'] > data['end_time']:
                raise serializers.ValidationError("End time should be after start time")
        return data


class UserToCarSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserToCar
        fields = '__all__'


class CarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = ('id', 'model', 'brand', 'year', 'is_truck')


class BaseSumSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaseSum
        fields = '__all__'

