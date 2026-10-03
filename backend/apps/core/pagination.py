from rest_framework.pagination import PageNumberPagination


class StudyMatePagination(PageNumberPagination):
    """Bounded page-number pagination shared by all API list endpoints."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
