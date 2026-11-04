from rest_framework import status
from rest_framework.test import APITestCase
from accounts.models import User

class PasswordValidationAPITests(APITestCase):
    def setUp(self):
        # Create a manager to make user creation requests (since only managers can create users)
        self.manager = User.objects.create_user(
            username="manager_admin",
            password="StrongManagerPassword123!",
            role=User.Role.MANAGER
        )
        self.client.force_authenticate(user=self.manager)

    def test_reject_short_password(self):
        payload = {
            "username": "new_user_1",
            "email": "user1@example.com",
            "password": "123",
            "role": User.Role.EMPLOYEE
        }
        response = self.client.post("/api/users/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_reject_common_password(self):
        payload = {
            "username": "new_user_2",
            "email": "user2@example.com",
            "password": "password",
            "role": User.Role.EMPLOYEE
        }
        response = self.client.post("/api/users/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_reject_numeric_password(self):
        payload = {
            "username": "new_user_3",
            "email": "user3@example.com",
            "password": "123456789012",
            "role": User.Role.EMPLOYEE
        }
        response = self.client.post("/api/users/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_reject_password_similar_to_username(self):
        payload = {
            "username": "charlie_brown",
            "email": "charlie@example.com",
            "password": "charlie_brown_pw",
            "role": User.Role.EMPLOYEE
        }
        response = self.client.post("/api/users/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_accept_strong_password(self):
        payload = {
            "username": "valid_user",
            "email": "valid@example.com",
            "password": "StrongRandomPassword987!",
            "role": User.Role.EMPLOYEE
        }
        response = self.client.post("/api/users/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="valid_user").exists())
