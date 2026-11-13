"""Django Admin customization (http://127.0.0.1:8000/admin/)."""
from django.contrib import admin

from .models import Project, Tag, Task, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone")                 # columns in the list page
    search_fields = ("user__username", "phone")      # search box
    ordering = ("user__username",)


class TaskInline(admin.TabularInline):
    """Lets you add/edit a project's tasks directly on the project page."""

    model = Task
    extra = 1
    fields = ("title", "status", "priority", "due_date")
    show_change_link = True


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name", "description")
    ordering = ("name",)
    readonly_fields = ("created_at",)                # shown but not editable
    inlines = [TaskInline]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "status", "priority", "due_date", "assigned_to")
    list_filter = ("status", "priority", "project")  # right-hand filter sidebar
    search_fields = ("title", "description")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    filter_horizontal = ("tags",)                    # nicer widget for ManyToMany
