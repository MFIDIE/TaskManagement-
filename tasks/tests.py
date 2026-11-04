from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from accounts.models import User
from tasks.models import Task


class TaskPermissionAPITests(APITestCase):
    def setUp(self):
        # 1. Create a Manager
        self.manager = User.objects.create_user(
            username="manager_jane",
            password="StrongPassword123!",
            role=User.Role.MANAGER
        )

        # 2. Create two separate Employees
        self.employee_alice = User.objects.create_user(
            username="alice",
            password="StrongPassword123!",
            role=User.Role.EMPLOYEE
        )
        self.employee_bob = User.objects.create_user(
            username="bob",
            password="StrongPassword123!",
            role=User.Role.EMPLOYEE
        )

        # 3. Create sample tasks
        self.task_alice = Task.objects.create(
            title="Alice's Task",
            description="Work on frontend",
            deadline=timezone.now() + timezone.timedelta(days=3),
            priority=Task.Priority.HIGH,
            status=Task.Status.TODO,
            assigned_to=self.employee_alice,
            created_by=self.manager
        )

        self.task_bob = Task.objects.create(
            title="Bob's Task",
            description="Work on backend",
            deadline=timezone.now() + timezone.timedelta(days=5),
            priority=Task.Priority.MEDIUM,
            status=Task.Status.TODO,
            assigned_to=self.employee_bob,
            created_by=self.manager
        )

    # ==========================================
    # 1. UNAUTHENTICATED ACCESS
    # ==========================================
    def test_unauthenticated_requests_are_rejected(self):
        """Unauthenticated requests must receive 401 Unauthorized."""
        response = self.client.get("/api/tasks/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ==========================================
    # 2. MANAGER PERMISSIONS (FULL CRUD)
    # ==========================================
    def test_manager_can_list_all_tasks(self):
        """Managers can view all tasks across the company."""
        self.client.force_authenticate(user=self.manager)
        response = self.client.get("/api/tasks/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_manager_can_create_task(self):
        """Managers can create new tasks and assign them."""
        self.client.force_authenticate(user=self.manager)
        payload = {
            "title": "New Manager Task",
            "description": "Urgent review",
            "deadline": (timezone.now() + timezone.timedelta(days=2)).isoformat(),
            "priority": Task.Priority.URGENT,
            "assigned_to": self.employee_alice.id
        }
        response = self.client.post("/api/tasks/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_task = Task.objects.get(title="New Manager Task")
        self.assertEqual(new_task.created_by, self.manager)

    def test_manager_can_update_any_task(self):
        """Managers can modify any task attributes."""
        self.client.force_authenticate(user=self.manager)
        payload = {"title": "Updated by Manager", "priority": Task.Priority.LOW}
        response = self.client.patch(f"/api/tasks/{self.task_alice.id}/", payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task_alice.refresh_from_db()
        self.assertEqual(self.task_alice.title, "Updated by Manager")
        self.assertEqual(self.task_alice.priority, Task.Priority.LOW)

    def test_manager_can_delete_task(self):
        """Managers can delete any task."""
        self.client.force_authenticate(user=self.manager)
        response = self.client.delete(f"/api/tasks/{self.task_alice.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Task.objects.filter(id=self.task_alice.id).exists())

    # ==========================================
    # 3. EMPLOYEE RESTRICTIONS & ISOLATION
    # ==========================================
    def test_employee_cannot_create_task(self):
        """Employees must receive 403 Forbidden when attempting to create a task."""
        self.client.force_authenticate(user=self.employee_alice)
        payload = {
            "title": "Unauthorized Task",
            "deadline": (timezone.now() + timezone.timedelta(days=1)).isoformat()
        }
        response = self.client.post("/api/tasks/", payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_delete_task(self):
        """Employees must receive 403 Forbidden when attempting to delete a task."""
        self.client.force_authenticate(user=self.employee_alice)
        response = self.client.delete(f"/api/tasks/{self.task_alice.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_only_sees_assigned_tasks_in_list(self):
        """Alice should only see her task, not Bob's task in the list."""
        self.client.force_authenticate(user=self.employee_alice)
        response = self.client.get("/api/tasks/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.task_alice.id)

    def test_employee_cannot_retrieve_other_employee_task(self):
        """Alice receives 404 when attempting to access Bob's task directly by ID."""
        self.client.force_authenticate(user=self.employee_alice)
        response = self.client.get(f"/api/tasks/{self.task_bob.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_employee_cannot_update_other_employee_task(self):
        """Alice receives 404 when attempting to edit Bob's task."""
        self.client.force_authenticate(user=self.employee_alice)
        payload = {"status": Task.Status.COMPLETED}
        response = self.client.patch(f"/api/tasks/{self.task_bob.id}/", payload)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ==========================================
    # 4. FIELD-LEVEL PERMISSION RESTRICTIONS
    # ==========================================
    def test_employee_can_update_status_on_own_task(self):
        """Alice can update the status of her own task."""
        self.client.force_authenticate(user=self.employee_alice)
        payload = {"status": Task.Status.IN_PROGRESS}
        response = self.client.patch(f"/api/tasks/{self.task_alice.id}/", payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task_alice.refresh_from_db()
        self.assertEqual(self.task_alice.status, Task.Status.IN_PROGRESS)

    def test_employee_cannot_change_title_or_reassign_own_task(self):
        """
        When Alice tries to change the title or reassign the task to Bob,
        the request succeeds for valid fields (status), but restricted fields
        remain unchanged because of TaskProgressUpdateSerializer.
        """
        self.client.force_authenticate(user=self.employee_alice)
        payload = {
            "title": "Hacked Title",
            "assigned_to": self.employee_bob.id,
            "status": Task.Status.COMPLETED
        }
        response = self.client.patch(f"/api/tasks/{self.task_alice.id}/", payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.task_alice.refresh_from_db()
        # Status was successfully updated
        self.assertEqual(self.task_alice.status, Task.Status.COMPLETED)
        # Title and assigned_to were NOT modified
        self.assertEqual(self.task_alice.title, "Alice's Task")
        self.assertEqual(self.task_alice.assigned_to, self.employee_alice)

    # ==========================================
    # 5. FILTERING, SORTING & SEARCH
    # ==========================================
    def test_filter_tasks_by_status(self):
        """Filtering by status returns only matching tasks."""
        self.client.force_authenticate(user=self.manager)
        # Update Bob's task to COMPLETED
        self.task_bob.status = Task.Status.COMPLETED
        self.task_bob.save()

        # Query only COMPLETED tasks
        response = self.client.get("/api/tasks/?status=COMPLETED")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.task_bob.id)

    def test_filter_tasks_by_priority(self):
        """Filtering by priority returns only tasks with that priority."""
        self.client.force_authenticate(user=self.manager)
        response = self.client.get("/api/tasks/?priority=HIGH")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.task_alice.id)

    def test_order_tasks_by_deadline(self):
        """Ordering by deadline sorts ascending and descending."""
        self.client.force_authenticate(user=self.manager)
        # Ascending: Alice's deadline (+3 days) comes before Bob's (+5 days)
        response_asc = self.client.get("/api/tasks/?ordering=deadline")
        self.assertEqual(response_asc.status_code, status.HTTP_200_OK)
        self.assertEqual(response_asc.data[0]["id"], self.task_alice.id)
        self.assertEqual(response_asc.data[1]["id"], self.task_bob.id)

        # Descending: Bob's deadline (+5 days) comes before Alice's (+3 days)
        response_desc = self.client.get("/api/tasks/?ordering=-deadline")
        self.assertEqual(response_desc.status_code, status.HTTP_200_OK)
        self.assertEqual(response_desc.data[0]["id"], self.task_bob.id)
        self.assertEqual(response_desc.data[1]["id"], self.task_alice.id)

    def test_search_tasks_by_keyword(self):
        """Searching by keyword matches across title and description."""
        self.client.force_authenticate(user=self.manager)
        response = self.client.get("/api/tasks/?search=frontend")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.task_alice.id)
