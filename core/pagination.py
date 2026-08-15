from rest_framework.pagination import CursorPagination


class CreatedAtCursorPagination(CursorPagination):
    ordering = ("-created_at", "id")


class StartsAtCursorPagination(CursorPagination):
    ordering = ("starts_at", "id")


class IssuedAtCursorPagination(CursorPagination):
    ordering = ("issued_at", "id")


class RequestedAtCursorPagination(CursorPagination):
    ordering = ("requested_at", "id")
