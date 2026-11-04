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
        fields = ['status', 'priority', 'assigned_to', 'deadline_before', 'deadline_after']
