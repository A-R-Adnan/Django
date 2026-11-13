"""
Database models for the Task Management System.

There are exactly FOUR custom models: UserProfile, Project, Tag and Task.
Django's built-in User model is reused (no custom user model).

Note: the ManyToManyField Task.tags makes Django create a hidden join table
("tasks_task_tags") automatically. That table is NOT a custom model.
"""
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

# A phone number is an optional "+" followed by 7-15 digits.
PHONE_PATTERN = re.compile(r"\+?\d{7,15}")


class UserProfile(models.Model):
    """Extra information about a user (phone, bio) that Django's User lacks.

    OneToOneField: one User has at most one profile, and one profile belongs
    to exactly one User. `user.profile` gives the profile from the user side.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,  # deleting the user deletes the profile
        related_name="profile",
    )
    phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        # __str__ controls how the object is shown in the admin and shell.
        return f"Profile of {self.user.username}"

    def clean(self):
        """Model-level validation (runs in the admin via full_clean())."""
        if self.phone and not PHONE_PATTERN.fullmatch(self.phone):
            raise ValidationError(
                {"phone": "Enter 7-15 digits, optionally starting with '+'."}
            )


class Project(models.Model):
    """A project groups related tasks together."""

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  # set once on creation

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        if not self.name.strip():
            raise ValidationError({"name": "Project name cannot be empty."})


class Tag(models.Model):
    """A label used to categorize tasks (e.g. "Urgent", "Homework")."""

    name = models.CharField(max_length=50, unique=True)  # unique at DB level

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        self.name = self.name.strip()
        if not self.name:
            raise ValidationError({"name": "Tag name cannot be empty."})
        # unique=True is case-sensitive, so we also block "work" vs "Work".
        duplicates = Tag.objects.filter(name__iexact=self.name).exclude(pk=self.pk)
        if duplicates.exists():
            raise ValidationError({"name": f"Tag '{self.name}' already exists."})


class Task(models.Model):
    """A single piece of work. This is the main model of the system.

    Relationships:
    - ForeignKey -> Project: many tasks belong to ONE project.
      `project.tasks.all()` lists a project's tasks.
    - ForeignKey -> User: a task is assigned to ONE user (optional); one user
      can have many tasks. `user.assigned_tasks.all()` lists a user's tasks.
      SET_NULL keeps the task if the user is deleted.
    - ManyToManyField -> Tag: a task can have many tags and a tag can be on
      many tasks. `task.tags.all()` / `tag.tasks.all()`.
    """

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("In Progress", "In Progress"),
        ("Completed", "Completed"),
    ]
    PRIORITY_CHOICES = [
        ("Low", "Low"),
        ("Medium", "Medium"),
        ("High", "High"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="Medium")
    due_date = models.DateField(null=True, blank=True)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="tasks"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="tasks")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # refreshed on every save

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} [{self.status}]"

    def clean(self):
        """Business rules checked at model level (used by the admin)."""
        errors = {}
        if not self.title.strip():
            errors["title"] = "Task title cannot be empty."
        # Only block past dates when CREATING, so old tasks stay editable.
        if self._state.adding and self.due_date and self.due_date < timezone.localdate():
            errors["due_date"] = "Due date cannot be in the past."
        elif self.priority == "High" and not self.due_date:
            errors["due_date"] = "High priority tasks must have a due date."
        if errors:
            raise ValidationError(errors)
