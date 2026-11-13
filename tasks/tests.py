"""
Automated tests. Run with:  python manage.py test

Django creates a temporary test database ("test_<DB_NAME>"), so the
PostgreSQL user needs permission to create databases.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Project, Tag, Task, UserProfile

User = get_user_model()


class TaskApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="pass12345")
        self.project = Project.objects.create(name="Demo Project")
        self.tag = Tag.objects.create(name="Homework")
        self.list_url = reverse("task-list")
        self.payload = {
            "title": "Write report",
            "description": "First draft",
            "status": "Pending",
            "priority": "Medium",
            "due_date": (timezone.localdate() + timedelta(days=5)).isoformat(),
            "project": self.project.id,
            "assigned_to": self.user.id,
            "tag_ids": [self.tag.id],
        }

    def make_task(self, title, **extra):
        return Task.objects.create(title=title, project=self.project, **extra)

    # ---- CRUD ----
    def test_create_task(self):
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["project_detail"]["name"], "Demo Project")
        self.assertEqual(response.data["assigned_to_detail"]["username"], "alice")
        self.assertEqual(response.data["tags"][0]["name"], "Homework")

    def test_retrieve_update_delete_task(self):
        task = self.make_task("Old title")
        url = reverse("task-detail", args=[task.id])
        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)
        patch = self.client.patch(url, {"status": "Completed"}, format="json")
        self.assertEqual(patch.status_code, status.HTTP_200_OK)
        self.assertEqual(patch.data["status"], "Completed")
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)

    # ---- Validation ----
    def test_empty_title_rejected(self):
        self.payload["title"] = ""
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", response.data)

    def test_invalid_status_and_priority_rejected(self):
        self.payload["status"] = "Done"
        self.payload["priority"] = "Urgent"
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)
        self.assertIn("priority", response.data)

    def test_past_due_date_rejected(self):
        self.payload["due_date"] = "2020-01-01"
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("due_date", response.data)

    def test_missing_or_unknown_project_rejected(self):
        del self.payload["project"]
        self.assertEqual(
            self.client.post(self.list_url, self.payload, format="json").status_code, 400
        )
        self.payload["project"] = 999999
        self.assertEqual(
            self.client.post(self.list_url, self.payload, format="json").status_code, 400
        )

    def test_high_priority_requires_due_date(self):
        self.payload["priority"] = "High"
        del self.payload["due_date"]
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("due_date", response.data)

    def test_duplicate_task_title_in_same_project_rejected(self):
        self.client.post(self.list_url, self.payload, format="json")
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", response.data)

    # ---- Filtering, searching, ordering ----
    def test_filter_by_status_and_priority(self):
        self.make_task("A", status="Pending", priority="Low")
        self.make_task("B", status="Completed", priority="High",
                       due_date=timezone.localdate())
        response = self.client.get(self.list_url, {"status": "Completed"})
        self.assertEqual(response.data["count"], 1)
        response = self.client.get(self.list_url, {"priority": "Low"})
        self.assertEqual(response.data["results"][0]["title"], "A")

    def test_search_by_title_and_description(self):
        self.make_task("Math assignment")
        self.make_task("Buy milk", description="for the assignment party")
        self.make_task("Gym")
        response = self.client.get(self.list_url, {"search": "assignment"})
        self.assertEqual(response.data["count"], 2)

    def test_ordering_by_priority(self):
        self.make_task("Low one", priority="Low")
        self.make_task("High one", priority="High", due_date=timezone.localdate())
        self.make_task("Medium one", priority="Medium")
        response = self.client.get(self.list_url, {"ordering": "-priority"})
        titles = [task["title"] for task in response.data["results"]]
        self.assertEqual(titles, ["High one", "Medium one", "Low one"])

    # ---- Pagination ----
    def test_pagination_format_and_page_size(self):
        for number in range(12):
            self.make_task(f"Task {number}")
        response = self.client.get(self.list_url)
        self.assertEqual(
            set(response.data.keys()), {"count", "next", "previous", "results"}
        )
        self.assertEqual(response.data["count"], 12)
        self.assertEqual(len(response.data["results"]), 10)
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])


class TagProjectProfileTests(APITestCase):
    def test_duplicate_tag_rejected_case_insensitive(self):
        url = reverse("tag-list")
        self.assertEqual(self.client.post(url, {"name": "Work"}).status_code, 201)
        self.assertEqual(self.client.post(url, {"name": "work"}).status_code, 400)

    def test_duplicate_project_rejected(self):
        url = reverse("project-list")
        self.assertEqual(self.client.post(url, {"name": "Alpha"}).status_code, 201)
        self.assertEqual(self.client.post(url, {"name": "ALPHA"}).status_code, 400)

    def test_profile_one_per_user_and_phone_validation(self):
        user = User.objects.create_user("bob", password="pass12345")
        url = reverse("profile-list")
        body = {"user": user.id, "phone": "+8801712345678", "bio": "Hi"}
        self.assertEqual(self.client.post(url, body).status_code, 201)
        self.assertEqual(self.client.post(url, body).status_code, 400)  # duplicate
        other = User.objects.create_user("carol", password="pass12345")
        bad_phone = {"user": other.id, "phone": "abc"}
        self.assertEqual(self.client.post(url, bad_phone).status_code, 400)

    def test_str_methods(self):
        user = User.objects.create_user("dave", password="pass12345")
        project = Project.objects.create(name="P1")
        tag = Tag.objects.create(name="T1")
        task = Task.objects.create(title="Do it", project=project)
        self.assertEqual(str(UserProfile.objects.create(user=user)), "Profile of dave")
        self.assertEqual(str(project), "P1")
        self.assertEqual(str(tag), "T1")
        self.assertEqual(str(task), "Do it [Pending]")
