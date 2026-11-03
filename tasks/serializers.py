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