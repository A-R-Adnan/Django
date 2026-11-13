"""
API views.

ModelViewSet is used because one small class gives us ALL the CRUD actions:

    POST   /api/tasks/       create        -> 201 Created
    GET    /api/tasks/       list          -> 200 OK (paginated)
    GET    /api/tasks/1/     retrieve      -> 200 OK (404 if not found)
    PUT    /api/tasks/1/     full update   -> 200 OK
    PATCH  /api/tasks/1/     partial update-> 200 OK
    DELETE /api/tasks/1/     delete        -> 204 No Content

Invalid data automatically returns 400 Bad Request with the serializer's
error messages.

Filtering / searching / ordering (backends are set in settings.py):
    filterset_class / filterset_fields -> ?status=Pending  (exact match)
    search_fields                      -> ?search=text     (contains, any listed field)
    ordering_fields                    -> ?ordering=-created_at  ("-" = descending)
Pagination (StandardPagination, 10 per page) is applied to every list.
"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import SearchFilter

from .filters import PRIORITY_RANK, PriorityOrderingFilter, TaskFilter
from .models import Project, Tag, Task, UserProfile
from .serializers import (
    ProjectSerializer,
    TagSerializer,
    TaskSerializer,
    UserProfileSerializer,
)


class UserProfileViewSet(viewsets.ModelViewSet):
    """CRUD for user profiles: /api/profiles/"""

    queryset = UserProfile.objects.select_related("user")
    serializer_class = UserProfileSerializer
    filterset_fields = ["user"]
    search_fields = ["user__username", "phone", "bio"]
    ordering_fields = ["id", "phone"]


class ProjectViewSet(viewsets.ModelViewSet):
    """CRUD for projects: /api/projects/"""

    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]


class TagViewSet(viewsets.ModelViewSet):
    """CRUD for tags: /api/tags/"""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    search_fields = ["name"]
    ordering_fields = ["id", "name"]


class TaskViewSet(viewsets.ModelViewSet):
    """CRUD for tasks: /api/tasks/ (with filtering, searching, ordering)."""

    # select_related / prefetch_related load related rows in few queries
    # instead of one extra query per task. priority_rank is used for sorting.
    queryset = (
        Task.objects.select_related("project", "assigned_to")
        .prefetch_related("tags")
        .annotate(priority_rank=PRIORITY_RANK)
    )
    serializer_class = TaskSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, PriorityOrderingFilter]
    filterset_class = TaskFilter                      # status, priority, project, assigned_to
    search_fields = ["title", "description"]          # ?search=
    ordering_fields = ["created_at", "due_date", "priority"]  # ?ordering=
    ordering = ["-created_at"]                        # default: newest first
