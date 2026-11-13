"""
Serializers convert model objects to JSON (and JSON back to model objects)
and validate incoming data. Every model has one ModelSerializer, which
builds its fields automatically from the model.

Validation happens in layers:
1. Field-level  : validate_<field_name>() checks ONE field.
2. Object-level : validate() checks several fields together.
3. Model-level  : model.clean() (used by the admin, see models.py).
"""
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import PHONE_PATTERN, Project, Tag, Task, UserProfile

User = get_user_model()


class UserSummarySerializer(serializers.ModelSerializer):
    """Small read-only view of a user, nested inside other serializers.

    Only safe fields are exposed (never the password).
    """

    class Meta:
        model = User
        fields = ["id", "username", "email"]


class ProjectSummarySerializer(serializers.ModelSerializer):
    """Small view of a project, nested inside TaskSerializer."""

    class Meta:
        model = Project
        fields = ["id", "name"]


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile.

    `user` (an id) is used when writing; `user_detail` is a read-only nested
    object that shows the user's details when reading.
    """

    user_detail = UserSummarySerializer(source="user", read_only=True)

    class Meta:
        model = UserProfile
        fields = ["id", "user", "user_detail", "phone", "bio"]
        extra_kwargs = {
            "user": {
                # Duplicate prevention: one profile per user (OneToOne).
                "validators": [
                    UniqueValidator(
                        queryset=UserProfile.objects.all(),
                        message="This user already has a profile.",
                    )
                ],
                "error_messages": {
                    "does_not_exist": "User with id {pk_value} does not exist.",
                    "required": "A profile must belong to a user.",
                },
            }
        }

    def validate_phone(self, value):
        """Field-level validation: the phone number format."""
        if value and not PHONE_PATTERN.fullmatch(value):
            raise serializers.ValidationError(
                "Enter 7-15 digits, optionally starting with '+'."
            )
        return value


class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for Project. `task_count` is calculated and read-only."""

    task_count = serializers.IntegerField(source="tasks.count", read_only=True)

    class Meta:
        model = Project
        fields = ["id", "name", "description", "created_at", "task_count"]
        read_only_fields = ["created_at"]  # set by the server, not the client
        extra_kwargs = {
            "name": {"error_messages": {"blank": "Project name cannot be empty.",
                                        "required": "Project name is required."}}
        }

    def validate_name(self, value):
        """Field-level validation: project names must be unique (any case)."""
        duplicates = Project.objects.filter(name__iexact=value)
        if self.instance:  # when updating, ignore the project itself
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError(f"A project named '{value}' already exists.")
        return value


class TagSerializer(serializers.ModelSerializer):
    """Serializer for Tag."""

    class Meta:
        model = Tag
        fields = ["id", "name"]
        extra_kwargs = {
            "name": {
                "validators": [],  # we do our own (case-insensitive) check below
                "error_messages": {"blank": "Tag name cannot be empty.",
                                   "required": "Tag name is required."},
            }
        }

    def validate_name(self, value):
        """Field-level validation: tag names must be unique (any case)."""
        duplicates = Tag.objects.filter(name__iexact=value)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError(f"Tag '{value}' already exists.")
        return value


class TaskSerializer(serializers.ModelSerializer):
    """Serializer for Task.

    Reading shows rich nested data (project, user, tags).
    Writing uses simple ids:
        "project": 1, "assigned_to": 2, "tag_ids": [1, 2]
    """

    # Read-only nested objects (what the client SEES).
    project_detail = ProjectSummarySerializer(source="project", read_only=True)
    assigned_to_detail = UserSummarySerializer(source="assigned_to", read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    # Write-only field: tags are assigned by sending a list of tag ids.
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        source="tags",
        write_only=True,
        required=False,
    )

    class Meta:
        model = Task
        fields = [
            "id", "title", "description", "status", "priority", "due_date",
            "project", "project_detail", "assigned_to", "assigned_to_detail",
            "tags", "tag_ids", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
        extra_kwargs = {
            "title": {"error_messages": {"blank": "Task title cannot be empty.",
                                         "required": "Task title is required."}},
            "project": {"error_messages": {"required": "A task must belong to a project.",
                                           "null": "A task must belong to a project.",
                                           "does_not_exist": "Project with id {pk_value} does not exist."}},
            "assigned_to": {"error_messages": {"does_not_exist": "User with id {pk_value} does not exist."}},
        }

    def validate_due_date(self, value):
        """Field-level validation: no past due dates when CREATING a task."""
        if self.instance is None and value and value < timezone.localdate():
            raise serializers.ValidationError("Due date cannot be in the past.")
        return value

    def validate(self, attrs):
        """Object-level validation: rules that involve several fields.

        On PATCH only some fields are sent, so missing values are taken from
        the existing task (self.instance).
        """
        current = self.instance
        title = attrs.get("title", current.title if current else None)
        project = attrs.get("project", current.project if current else None)
        priority = attrs.get("priority", current.priority if current else "Medium")
        due_date = attrs.get("due_date", current.due_date if current else None)

        # Business rule: urgent work needs a deadline.
        if priority == "High" and not due_date:
            raise serializers.ValidationError(
                {"due_date": "High priority tasks must have a due date."}
            )

        # Duplicate prevention: same title twice in the same project.
        if title and project:
            duplicates = Task.objects.filter(project=project, title__iexact=title)
            if current:
                duplicates = duplicates.exclude(pk=current.pk)
            if duplicates.exists():
                raise serializers.ValidationError(
                    {"title": "This project already has a task with this title."}
                )
        return attrs
