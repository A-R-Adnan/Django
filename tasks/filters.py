"""Filtering and ordering helpers for the Task endpoint."""
import django_filters
from django.db.models import Case, IntegerField, Value, When
from rest_framework.filters import OrderingFilter

from .models import Task

# Priority is stored as text ("Low", "Medium", "High"). Sorting text would give
# High, Low, Medium (alphabetical), so we turn it into a number 1/2/3 first.
PRIORITY_RANK = Case(
    When(priority="Low", then=Value(1)),
    When(priority="Medium", then=Value(2)),
    When(priority="High", then=Value(3)),
    default=Value(0),
    output_field=IntegerField(),
)


class TaskFilter(django_filters.FilterSet):
    """Exact-match filters: /api/tasks/?status=Pending&priority=High&project=1

    django-filter builds each filter from the model field, so an invalid
    value (e.g. ?status=Done) automatically returns a 400 error.
    """

    class Meta:
        model = Task
        fields = ["status", "priority", "project", "assigned_to"]


class PriorityOrderingFilter(OrderingFilter):
    """OrderingFilter that sorts priority as Low < Medium < High.

    ?ordering=priority  -> Low first      ?ordering=-priority -> High first
    """

    def get_ordering(self, request, queryset, view):
        ordering = super().get_ordering(request, queryset, view)
        if not ordering:
            return ordering
        mapping = {"priority": "priority_rank", "-priority": "-priority_rank"}
        return [mapping.get(field, field) for field in ordering]
