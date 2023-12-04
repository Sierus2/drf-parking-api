"""
URL configuration for parking project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import routers, permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from rest_framework_swagger.views import get_swagger_view

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

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('api/v1/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    # path('api/v1/v1token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/v1/register/', RegisterView.as_view(), name='auth_register'),
    path('api/v1/profile/', getProfile, name='profile'),
    path('api/v1/reset-password/', PasswordResetView.as_view(), name='password_reset'),
    path('api/v1/password-reset-confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('api/v1/login/', MyObtainTokenPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/password/change/', ChangePasswordView.as_view(), name='change_password'),

]
