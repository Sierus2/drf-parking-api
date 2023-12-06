from django.contrib import admin
from django.urls import path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import routers, permissions
from rest_framework.routers import DefaultRouter, SimpleRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from rest_framework_swagger.views import get_swagger_view

from booking.views import CarViewSet, BookingViewSet, ParkingViewSet, EmployeeOfParkingViewSet, BaseSumViewSet
from user.views import RegisterView, getProfile, PasswordResetView, PasswordResetConfirmView, MyObtainTokenPairView, \
    ChangePasswordView

schema_view = get_swagger_view(title='Booking API')

router = routers.SimpleRouter()

urlpatterns = router.urls
schema_view = get_schema_view(
    openapi.Info(
        title="Booking API",
        default_version='v1',
        description="Этот API позволяет пользователю бронировать парковку заранее",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

router = DefaultRouter()

router.register(r'cars', CarViewSet, basename='cars')
router.register(r'parkings', ParkingViewSet, basename='parking')
router.register(r'employeeofparkings', EmployeeOfParkingViewSet, basename='employee_of_parking')
router.register(r'parking', ParkingViewSet)
router.register(r'employee', EmployeeOfParkingViewSet)
router.register(r'basesum', BaseSumViewSet)
router.register(r'booking', BookingViewSet)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    path('api/v1/auth/register/', RegisterView.as_view(), name='auth_register'),
    path('api/v1/auth/profile/', getProfile, name='profile'),
    path('api/v1/auth/reset-password/', PasswordResetView.as_view(), name='password_reset'),
    path('api/v1/auth/password-reset-confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
    path('api/v1/auth/login/', MyObtainTokenPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/auth/password/change/', ChangePasswordView.as_view(), name='change_password'),

    path('api/v1/booking/profit/', BookingViewSet.as_view({'get': 'calculate_user_profit'}), name='calculate-user-profit'),
    path('api/v1/booking/pre-cancellation/', BookingViewSet.as_view({'post': 'pre_cancellation'}), name='pre-cancellation'),
    # Qolgan yo'nalishlar...

    # Booking Endpoints
    path('api/v1/', include(router.urls)),



]
