from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    """Serializer used for reading and updating user information."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'date_joined']
        read_only_fields = ['id', 'date_joined']

    def validate_role(self, value):
        """Ensure only Managers can assign or change roles."""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and not request.user.is_manager:
            if self.instance and self.instance.role != value:
                raise serializers.ValidationError("Employees are not permitted to change user roles.")
            if not self.instance and value != User.Role.EMPLOYEE:
                raise serializers.ValidationError("Employees cannot assign non-employee roles.")
        return value

class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer used by managers to register employees (hashes and validates password)."""
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        min_length=8,
        max_length=128
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'password']

    def validate(self, attrs):
        """
        Runs Django's AUTH_PASSWORD_VALIDATORS against the password,
        passing user attributes to check for similarity with username/email.
        """
        temp_user = User(
            username=attrs.get('username'),
            email=attrs.get('email'),
            first_name=attrs.get('first_name', ''),
            last_name=attrs.get('last_name', '')
        )

        password = attrs.get('password')
        try:
            validate_password(password, user=temp_user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({'password': list(error.messages)})

        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
