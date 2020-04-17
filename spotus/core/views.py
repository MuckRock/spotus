# Django
from django.db.models.expressions import F
from django.views import generic


class OrderedSortMixin:
    """Sorts and orders a queryset given some inputs."""

    default_sort = "id"
    default_order = "asc"
    sort_map = {}

    def sort_queryset(self, queryset):
        """
        Sorts a queryset of objects.

        We need to make sure the field to sort by is allowed.
        If the field isn't allowed, return the default order queryset.
        """
        sort = self.request.GET.get("sort", self.default_sort)
        order = self.request.GET.get("order", self.default_order)
        sort = self.sort_map.get(sort, self.default_sort)
        if order == "desc":
            sort = F(sort).desc(nulls_last=True)
        else:
            sort = F(sort).asc(nulls_last=True)
        return queryset.order_by(sort)

    def get_queryset(self):
        """Sorts the queryset before returning it."""
        return self.sort_queryset(super().get_queryset())

    def get_context_data(self, **kwargs):
        """Adds sort and order data to the context."""
        context = super().get_context_data(**kwargs)
        context["sort"] = self.request.GET.get("sort", self.default_sort)
        context["order"] = self.request.GET.get("order", self.default_order)
        return context


class ModelFilterMixin:
    """
    The ModelFilterMixin gives the ability to filter a list
    of objects with the help of the django_filters library.

    It requires a filter_class be defined.
    """

    filter_class = None

    def get_filter(self):
        """Initializes and returns the filter, if a filter_class is defined."""
        if self.filter_class is None:
            raise ValueError("Missing a filter class.")
        return self.filter_class(
            self.request.GET, queryset=self.get_queryset(), request=self.request
        )

    def get_context_data(self, **kwargs):
        """
        Adds the filter to the context and overrides the
        object_list value with the filter's queryset.
        We also apply pagination to the filter queryset.
        """
        context = super().get_context_data(**kwargs)
        filter_ = self.get_filter()
        queryset = filter_.qs
        if any(filter_.data.values()):
            queryset = queryset.distinct()
        try:
            page_size = self.get_paginate_by(queryset)
        except AttributeError:
            page_size = 0
        if page_size:
            paginator, page, queryset, is_paginated = self.paginate_queryset(
                queryset, page_size
            )
            context.update(
                {
                    "filter": filter_,
                    "paginator": paginator,
                    "page_obj": page,
                    "is_paginated": is_paginated,
                    "object_list": queryset,
                }
            )
        else:
            context.update(
                {
                    "filter": filter_,
                    "paginator": None,
                    "page_obj": None,
                    "is_paginated": False,
                    "object_list": queryset,
                }
            )
        return context


class PaginationMixin:
    """
    The PaginationMixin provides pagination support on a generic ListView,
    but also allows the per_page value to be adjusted with URL arguments.
    """

    paginate_by = 25
    min_per_page = 5
    max_per_page = 100

    def get_paginate_by(self, queryset):
        """Allows paginate_by to be set by a query argument."""
        # pylint:disable=unused-argument
        try:
            per_page = int(self.request.GET.get("per_page"))
            return max(min(per_page, self.max_per_page), self.min_per_page)
        except (ValueError, TypeError):
            return self.paginate_by

    def get_context_data(self, **kwargs):
        """Adds per_page to the context"""
        context = super().get_context_data(**kwargs)
        context["per_page"] = self.get_paginate_by(self.get_queryset())
        return context


class ListView(PaginationMixin, generic.ListView):
    """Defines a title and base template for our list views."""

    title = ""
    template_name = "base_list.html"

    def get_context_data(self, **kwargs):
        """Adds title to the context data."""
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        return context


class FilterListView(OrderedSortMixin, ModelFilterMixin, ListView):
    """Adds ordered sorting and filtering to our ListView."""
