"""Pagination settings shared by every list endpoint."""
from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Page-number pagination with 10 items per page.

    Use ?page=2 to get the next page. The response always looks like:
    {"count": 30, "next": "...?page=2", "previous": null, "results": [...]}
    """

    page_size = 10
