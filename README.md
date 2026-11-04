# Task Management API

A Django REST API for creating, assigning, and tracking tasks. Managers create accounts and assign work. Employees view their assigned tasks and update their status.

## Run locally

The setup below was checked with Python 3.12. The project uses SQLite for local development.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

On Windows PowerShell, activate the environment with `.\.venv\Scripts\Activate.ps1`.

Open [Swagger UI](http://127.0.0.1:8000/api/docs/) to explore the API, or download the [OpenAPI schema](http://127.0.0.1:8000/api/schema/). The initial superuser has manager access. The included Django settings are intended for local development.

## API quickstart

Send a JSON body with `Content-Type: application/json`. For protected endpoints, send `Authorization: Bearer <access_token>`. The examples below use paths relative to `http://127.0.0.1:8000`.

1. **Log in as the superuser** with `POST /api/auth/login/` and a JSON body containing your `username` and `password`. The response contains `access` and `refresh` tokens. In Swagger, use **Authorize** and enter the access token. To get a fresh access token, send `{"refresh":"<refresh_token>"}` to `POST /api/auth/refresh/`.
2. **Create an employee** with `POST /api/users/` using the manager token. Replace the example password with a strong local test password. The API returns `201 Created` and the employee's `id`.

   ```json
   {
     "username": "employee1",
     "password": "<choose-a-strong-test-password>",
     "role": "EMPLOYEE"
   }
   ```

3. **Assign a task** with `POST /api/tasks/` using the manager token. Replace `2` with the employee ID from the previous response. The API returns `201 Created` and the task's `id`.

   ```json
   {
     "title": "Prepare the weekly report",
     "deadline": "2027-01-15T17:00:00Z",
     "priority": "HIGH",
     "assigned_to": 2
   }
   ```

4. **Update progress as the employee.** Log in with the employee credentials and use the employee's access token. Call `GET /api/tasks/` to list assigned tasks. Send the following body to `PATCH /api/tasks/<task_id>/`. The response returns `200 OK` with the updated status.

   ```json
   {
     "status": "IN_PROGRESS"
   }
   ```

## Access by role

| Endpoint | Manager | Employee |
| --- | --- | --- |
| `GET /api/users/me/` | View own profile | View own profile |
| `/api/users/` and `/api/users/<id>/` | List, create, view, update, and delete users | View own profile by ID |
| `/api/tasks/` and `/api/tasks/<id>/` | List, create, view, update, and delete tasks | List and view assigned tasks and update their status |

Swagger currently omits some task request and response schemas. Use the task examples above when trying those endpoints.


Task list filtering and sorting are tracked in [issue #1](https://github.com/MFIDIE/TaskManagement-/issues/1).

For implementation details, see the [accounts guide](ACCOUNTS_SETUP_GUIDE.md) and [tasks guide](TASKS_IMPLEMENTATION_GUIDE.md).
