# Tasks App Implementation Guide: Step-by-Step

This guide provides the complete, step-by-step instructions for implementing the **`tasks`** app to satisfy Core Requirements 2, 3, 4, 5, and 6:
* **Req #2:** Create tasks and assign them to employees.
* **Req #3:** Fields for title, description, deadline, priority, and status.
* **Req #4:** Employees can update the progress of their assigned tasks.
* **Req #5:** Managers can view all tasks and filter them by employee or status.
* **Req #6:** REST API endpoints with Swagger documentation.

---

## Table of Contents
1. [Step 1: Create the Tasks App](#step-1-create-the-tasks-app)
2. [Step 2: Register in Settings](#step-2-register-in-settings)
3. [Step 3: Define the Task Model](#step-3-define-the-task-model)
4. [Step 4: Run Migrations](#step-4-run-migrations)
5. [Step 5: Define Task Permissions](#step-5-define-task-permissions)
6. [Step 6: Create Task Serializers](#step-6-create-task-serializers)
7. [Step 7: Create Task Filters](#step-7-create-task-filters)
8. [Step 8: Build the Task ViewSet](#step-8-build-the-task-viewset)
9. [Step 9: Wire Task URLs](#step-9-wire-task-urls)
10. [Step 10: Register in Django Admin](#step-10-register-in-django-admin)
11. [Step 11: Verification in Swagger UI](#step-11-verification-in-swagger-ui)

---

## Step 1: Create the Tasks App

In your terminal (with `.venv` active):

```powershell
python manage.py startapp tasks
```

---

## Step 2: Register in Settings

Open `config/settings.py` and add `'tasks'` to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # Default Django apps...
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'django_filters',

    # Local apps
    'accounts',
    'tasks',  # <-- Add this line
]
```

---

## Step 3: Define the Task Model

Open `tasks/models.py` and replace its contents with:

```python
# tasks/models.py
from django.db import models
from django.conf import settings

class Task(models.Model):
    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        URGENT = 'URGENT', 'Urgent'

    class Status(models.TextChoices):
        TODO = 'TODO', 'To Do'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        IN_REVIEW = 'IN_REVIEW', 'In Review'
        COMPLETED = 'COMPLETED', 'Completed'

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    deadline = models.DateTimeField()
    
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO
    )
    
    # Assigned employee (nullable if employee account is deleted)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks'
    )
    # Manager who created the task
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_tasks'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['deadline', '-priority']

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
```

---

## Step 4: Run Migrations

Generate and apply the database migrations in PowerShell:

```powershell
python manage.py makemigrations tasks
python manage.py migrate
```

---

## Step 5: Define Task Permissions

Create `tasks/permissions.py`:

```python
# tasks/permissions.py
from rest_framework.permissions import BasePermission

class IsManagerOrAssignee(BasePermission):
    """
    Managers have full permissions to create, view, edit, and delete tasks.
    Employees can only view and update tasks assigned to them.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Managers can do anything
        if request.user.is_manager:
            return True
        
        # Employees cannot create or delete tasks
        if view.action in ['create', 'destroy']:
            return False
            
        return True

    def has_object_permission(self, request, view, obj):
        if request.user.is_manager:
            return True
        # Employees can only access tasks assigned directly to them
        return obj.assigned_to == request.user
```

---

## Step 6: Create Task Serializers

Create `tasks/serializers.py`:

```python
# tasks/serializers.py
from rest_framework import serializers
from .models import Task
from accounts.serializers import UserSerializer

class TaskSerializer(serializers.ModelSerializer):
    """Full task serializer used by Managers."""
    assigned_to_detail = UserSerializer(source='assigned_to', read_only=True)
    created_by_detail = UserSerializer(source='created_by', read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'deadline', 'priority',
            'status', 'assigned_to', 'assigned_to_detail',
            'created_by', 'created_by_detail', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Automatically record the manager who created the task
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class TaskProgressUpdateSerializer(serializers.ModelSerializer):
    """
    Restricted serializer for Employees (Req #4).
    Only the 'status' field is editable. Title, deadline, priority,
    and assigned_to are strictly read-only.
    """
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'deadline', 'priority',
            'status', 'assigned_to', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'title', 'description', 'deadline', 'priority',
            'assigned_to', 'created_by', 'created_at', 'updated_at'
        ]
```

---

## Step 7: Create Task Filters

Create `tasks/filters.py` to enable Req #5 (Manager filtering by employee and status):

```python
# tasks/filters.py
import django_filters
from .models import Task

class TaskFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=Task.Status.choices)
    priority = django_filters.ChoiceFilter(choices=Task.Priority.choices)
    assigned_to = django_filters.NumberFilter(field_name='assigned_to__id')
    deadline_before = django_filters.DateTimeFilter(field_name='deadline', lookup_expr='lte')
    deadline_after = django_filters.DateTimeFilter(field_name='deadline', lookup_expr='gte')

    class Meta:
        model = Task
        fields = ['status', 'priority', 'assigned_to']
```

---

## Step 8: Build the Task ViewSet

Open `tasks/views.py` and replace its contents with:

```python
# tasks/views.py
from rest_framework import viewsets
from .models import Task
from .serializers import TaskSerializer, TaskProgressUpdateSerializer
from .permissions import IsManagerOrAssignee
from .filters import TaskFilter

class TaskViewSet(viewsets.ModelViewSet):
    """
    CRUD for Tasks:
    - Managers: Can create tasks, view all tasks, filter by employee/status, and delete tasks.
    - Employees: Can only view tasks assigned to them and update progress (status).
    """
    filterset_class = TaskFilter
    ordering_fields = ['deadline', 'priority', 'created_at', 'status']
    permission_classes = [IsManagerOrAssignee]

    def get_queryset(self):
        user = self.request.user
        # Managers see all tasks with optimized SQL JOINs
        if user.is_manager:
            return Task.objects.select_related('assigned_to', 'created_by').all()
        # Employees only see tasks assigned to them
        return Task.objects.select_related('assigned_to', 'created_by').filter(assigned_to=user)

    def get_serializer_class(self):
        # Employees updating a task can only edit the 'status' field
        if not self.request.user.is_manager and self.action in ['update', 'partial_update']:
            return TaskProgressUpdateSerializer
        return TaskSerializer
```

---

## Step 9: Wire Task URLs

1. Create `tasks/urls.py`:

```python
# tasks/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet

router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')

urlpatterns = [
    path('', include(router.urls)),
]
```

2. Open `config/urls.py` and include `tasks.urls`:

```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('accounts.urls')),
    path('api/', include('tasks.urls')),  # <-- Add this line

    # Swagger / OpenAPI documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
```

---

## Step 10: Register in Django Admin

Open `tasks/admin.py`:

```python
# tasks/admin.py
from django.contrib import admin
from .models import Task

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'priority', 'deadline', 'assigned_to', 'created_by']
    list_filter = ['status', 'priority', 'deadline']
    search_fields = ['title', 'description']
```

---

## Step 11: Verification in Swagger UI

Start the server:
```powershell
python manage.py runserver
```
Visit **`http://127.0.0.1:8000/api/docs/`** to test:

1. **Create & Assign Task (`POST /api/tasks/`)** (as Manager):
   ```json
   {
     "title": "Prepare Financial Report",
     "description": "Complete Q4 review",
     "deadline": "2026-11-15T17:00:00Z",
     "priority": "HIGH",
     "status": "TODO",
     "assigned_to": 2
   }
   ```
2. **Filter Tasks by Employee & Status (`GET /api/tasks/?assigned_to=2&status=TODO`)** (as Manager).
3. **Employee Progress Update (`PATCH /api/tasks/1/`)** (as Employee):
   ```json
   {
     "status": "IN_PROGRESS"
   }
   ```
   *(Verifying that if the employee tries to change the deadline or assignee, it is ignored).*
