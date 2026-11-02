# Accounts App Setup Guide: Step-by-Step

This guide provides the complete, step-by-step instructions for setting up the **`accounts`** app in Django & Django REST Framework (DRF) with custom user roles (`MANAGER` vs. `EMPLOYEE`), JWT authentication, and role-based access control.

---

## Table of Contents
1. [Step 1: Set Up & Activate Virtual Environment](#step-1-set-up--activate-virtual-environment)
2. [Step 2: Install Dependencies](#step-2-install-dependencies)
3. [Step 3: Initialize Project & App](#step-3-initialize-project--app)
4. [Step 4: Define Custom User Model](#step-4-define-custom-user-model)
5. [Step 5: Configure Project Settings](#step-5-configure-project-settings)
6. [Step 6: Database Migrations](#step-6-database-migrations)
7. [Step 7: Role-Based Permissions](#step-7-role-based-permissions)
8. [Step 8: User Serializers](#step-8-user-serializers)
9. [Step 9: User Views & ViewSet](#step-9-user-views--viewset)
10. [Step 10: App URL Routing](#step-10-app-url-routing)
11. [Step 11: Connect to Root URLs](#step-11-connect-to-root-urls)
12. [Step 12: Register in Django Admin](#step-12-register-in-django-admin)
13. [Step 13: Verification & API Testing](#step-13-verification--api-testing)

---

## Step 1: Set Up & Activate Virtual Environment

Open your terminal (PowerShell) in the project root:

```powershell
# 1. Create the virtual environment folder named .venv
python -m venv .venv

# 2. Allow script execution in current PowerShell session (if restricted)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

# 3. Activate the virtual environment
.\.venv\Scripts\Activate.ps1
```

> **Note:** When activated, your prompt will show `(.venv)` at the beginning.

---

## Step 2: Install Dependencies

Create a `requirements.txt` file in the project root:

```txt
Django>=5.0,<6.0
djangorestframework>=3.15.0
djangorestframework-simplejwt>=5.3.1
django-filter>=24.2
```

Install packages in your terminal:

```powershell
pip install -r requirements.txt
```

---

## Step 3: Initialize Project & App

Run the following commands in the root directory:

```powershell
# Initialize Django project named 'config' in current directory
django-admin startproject config .

# Create the 'accounts' app
python manage.py startapp accounts
```

---

## Step 4: Define Custom User Model

Open `accounts/models.py` and replace its content with:

```python
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        MANAGER = 'MANAGER', 'Manager'
        EMPLOYEE = 'EMPLOYEE', 'Employee'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE,
        help_text="Role: MANAGER or EMPLOYEE"
    )

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER or self.is_superuser

    @property
    def is_employee(self):
        return self.role == self.Role.EMPLOYEE

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
```

---

## Step 5: Configure Project Settings

> **CRITICAL:** `AUTH_USER_MODEL` must be set before running any database migrations.

Open `config/settings.py` and make the following updates:

### 1. Add Installed Apps
```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party packages
    'rest_framework',
    'rest_framework_simplejwt',

    # Local apps
    'accounts',
]
```

### 2. Set Custom User Model & DRF/JWT Configuration
Add the following to the bottom of `config/settings.py`:

```python
# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

# SimpleJWT Configuration
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

---

## Step 6: Database Migrations

Run initial migrations in PowerShell:

```powershell
# 1. Create migration file for accounts app
python manage.py makemigrations accounts

# 2. Apply all migrations
python manage.py migrate
```

---

## Step 7: Role-Based Permissions

Create a new file: `accounts/permissions.py`:

```python
from rest_framework.permissions import BasePermission

class IsManager(BasePermission):
    """Allows access only to authenticated users with the MANAGER role or superusers."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_manager)

class IsManagerOrSelf(BasePermission):
    """Managers have full access; regular employees can only view/edit their own account."""
    def has_object_permission(self, request, view, obj):
        if request.user.is_manager:
            return True
        return obj == request.user
```

---

## Step 8: User Serializers

Create a new file: `accounts/serializers.py`:

```python
from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    """Serializer used for reading user information."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'date_joined']
        read_only_fields = ['id', 'date_joined']

class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer used by managers to register employees (hashes password)."""
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'password']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
```

---

## Step 9: User Views & ViewSet

Open `accounts/views.py` and replace its content with:

```python
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import User
from .serializers import UserSerializer, UserCreateSerializer
from .permissions import IsManager, IsManagerOrSelf

class UserViewSet(viewsets.ModelViewSet):
    """
    CRUD for User accounts:
    - Managers can list, create, edit, and delete any user.
    - Employees can only view/edit their own profile (/me/ or /users/{id}/).
    """
    queryset = User.objects.all().order_by('id')

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            return [IsManager()]
        if self.action in ['retrieve', 'update', 'partial_update']:
            return [IsManagerOrSelf()]
        if self.action == 'me':
            return [IsAuthenticated()]
        return [IsManager()]

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Returns the currently logged-in user's profile."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
```

---

## Step 10: App URL Routing

Create a new file: `accounts/urls.py`:

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import UserViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    # JWT Auth Endpoints
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # User Endpoints
    path('', include(router.urls)),
]
```

---

## Step 11: Connect to Root URLs

Open `config/urls.py` and include the `accounts` routing:

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('accounts.urls')),
]
```

---

## Step 12: Register in Django Admin

Open `accounts/admin.py` to enable admin portal visibility:

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Role Information', {'fields': ('role',)}),
    )
    list_display = ['username', 'email', 'role', 'is_staff']
    list_filter = ['role', 'is_staff', 'is_active']
```

---

## Step 13: Verification & API Testing

### 1. Create Initial Superuser (Manager)
Run in PowerShell:
```powershell
python manage.py createsuperuser
```
*(Enter username `admin_manager`, email, and password)*

Assign the `MANAGER` role in Django shell:
```powershell
python manage.py shell
```
Inside the Python shell:
```python
from accounts.models import User
u = User.objects.get(username='admin_manager')
u.role = User.Role.MANAGER
u.save()
exit()
```

### 2. Start the Server
```powershell
python manage.py runserver
```

### 3. Test Endpoints (PowerShell)
In a second terminal window:

```powershell
# 1. Login to obtain JWT Token
$response = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/auth/login/" `
  -ContentType "application/json" `
  -Body '{"username": "admin_manager", "password": "yourpassword"}'

$token = $response.access

# 2. View current user profile (/me/)
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/users/me/" `
  -Headers @{ Authorization = "Bearer $token" }

# 3. Create a new Employee account (Manager only)
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/users/" `
  -Headers @{ Authorization = "Bearer $token" } `
  -ContentType "application/json" `
  -Body '{"username": "john_doe", "password": "password123", "role": "EMPLOYEE", "email": "john@company.com"}'
```
