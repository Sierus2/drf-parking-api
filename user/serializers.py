import requests
from django.contrib.auth.password_validation import validate_password
from django_rest_passwordreset.serializers import PasswordTokenSerializer
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from user.models import User
from user.utils import check_email_has


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super(MyTokenObtainPairSerializer, cls).get_token(user)

        # Add custom claims
        token['username'] = user.username
        return token


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password])
    repeat_password = serializers.CharField(write_only=True, required=True)
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'repeat_password',)

    def validate_email(self, value):
        lower_email = value.lower()
        if check_email_has(lower_email):
            print(41, 'has')
            if User.objects.filter(email__iexact=lower_email).exists():
                raise serializers.ValidationError(
                    {"email": "Email already exists! Please try other email!"})
            return lower_email
        else:
            print(41, 'not found')
            raise serializers.ValidationError(
                {"email": "Such an email is not available!"})

    def validate(self, attrs):
        if attrs['password'] != attrs['repeat_password']:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            repeat_password=validated_data['repeat_password']
        )

        user.set_password(validated_data['password'])
        user.save()

        return user


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'


class ResetPasswordEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
