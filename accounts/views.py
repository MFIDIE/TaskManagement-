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