from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

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
    permission_classes = [IsManagerOrAssignee]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = TaskFilter
    ordering_fields = ['deadline', 'priority', 'created_at', 'status']
    ordering = ['deadline', '-priority']
    search_fields = ['title', 'description']

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
