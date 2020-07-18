from django import forms
from django.db.models import Q

from django_filters import widgets
from django_filters import rest_framework as filters

from . import fields
from . import models
from . import search


class NoneObject(object):
    def __eq__(self, other):
        return other.__class__ == NoneObject


NONE = NoneObject()
BOOLEAN_CHOICES = [
    (True, True),
    ("true", True),
    ("True", True),
    ("1", True),
    ("yes", True),
    (False, False),
    ("false", False),
    ("False", False),
    ("0", False),
    ("no", False),
]
NULL_BOOLEAN_CHOICES = BOOLEAN_CHOICES + [
    ("None", NONE),
    ("none", NONE),
    ("Null", NONE),
    ("null", NONE),
]


class CoerceChoiceField(forms.ChoiceField):
    """
    Same as forms.ChoiceField but will return the second value
    in the choices tuple instead of the user provided one
    """

    def clean(self, value):
        if value is None:
            return value
        v = super().clean(value)
        try:
            return [b for a, b in self.choices if v == a][0]
        except IndexError:
            raise forms.ValidationError("Invalid value {}".format(value))


class NullBooleanFilter(filters.ChoiceFilter):
    field_class = CoerceChoiceField

    def __init__(self, *args, **kwargs):
        self.choices = NULL_BOOLEAN_CHOICES
        kwargs["choices"] = self.choices
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value in ["", None]:
            return qs
        if value == NONE:
            value = None
        qs = self.get_method(qs)(
            **{"%s__%s" % (self.field_name, self.lookup_expr): value}
        )
        return qs.distinct() if self.distinct else qs


def clean_null_boolean_filter(v):
    v = CoerceChoiceField(choices=NULL_BOOLEAN_CHOICES).clean(v)
    if v == NONE:
        v = None

    return v


def clean_boolean_filter(v):
    return CoerceChoiceField(choices=BOOLEAN_CHOICES).clean(v)


def get_null_boolean_filter(name):
    return {"handler": lambda v: Q(**{name: clean_null_boolean_filter(v)})}


def get_boolean_filter(name):
    return {"handler": lambda v: Q(**{name: clean_boolean_filter(v)})}


def get_generic_relation_filter(relation_name, choices):
    return {
        "handler": lambda v: fields.get_generic_filter_query(
            v, relation_name=relation_name, choices=choices
        )
    }


class DummyTypedMultipleChoiceField(forms.TypedMultipleChoiceField):
    def valid_value(self, value):
        return True


class QueryArrayWidget(widgets.QueryArrayWidget):
    """
    Until https://github.com/carltongibson/django-filter/issues/1047 is fixed
    """

    def value_from_datadict(self, data, files, name):
        data = data.copy()
        return super().value_from_datadict(data, files, name)


class MultipleQueryFilter(filters.TypedMultipleChoiceFilter):
    field_class = DummyTypedMultipleChoiceField

    def __init__(self, *args, **kwargs):
        kwargs["widget"] = QueryArrayWidget()
        super().__init__(*args, **kwargs)


def filter_target(value):

    config = {
        "artist": ["artist", "target_id", int],
        "album": ["album", "target_id", int],
        "track": ["track", "target_id", int],
    }
    parts = value.lower().split(" ")
    if parts[0].strip() not in config:
        raise forms.ValidationError("Improper target")

    conf = config[parts[0].strip()]

    query = Q(target_content_type__model=conf[0])
    if len(parts) > 1:
        _, lookup_field, validator = conf
        try:
            lookup_value = validator(parts[1].strip())
        except TypeError:
            raise forms.ValidationError("Imparsable target id")
        return query & Q(**{lookup_field: lookup_value})

    return query


class MutationFilter(filters.FilterSet):
    is_approved = NullBooleanFilter("is_approved")
    q = fields.SmartSearchFilter(
        config=search.SearchConfig(
            search_fields={
                "summary": {"to": "summary"},
                "fid": {"to": "fid"},
                "type": {"to": "type"},
            },
            filter_fields={
                "domain": {"to": "created_by__domain__name__iexact"},
                "is_approved": get_null_boolean_filter("is_approved"),
                "target": {"handler": filter_target},
                "is_applied": get_boolean_filter("is_applied"),
            },
        )
    )

    class Meta:
        model = models.Mutation
        fields = ["is_approved", "is_applied", "type"]


class ActorScopeFilter(filters.CharFilter):
    def __init__(self, *args, **kwargs):
        self.actor_field = kwargs.pop("actor_field")
        super().__init__(*args, **kwargs)

    def filter(self, queryset, value):
        from funkwhale_api.federation import models as federation_models

        if not value:
            return queryset

        request = getattr(self.parent, "request", None)
        if not request:
            return queryset.none()

        user = getattr(request, "user", None)
        qs = queryset
        if value.lower() == "me":
            qs = self.filter_me(user=user, queryset=queryset)
        elif value.lower() == "all":
            return queryset
        elif value.lower().startswith("actor:"):
            full_username = value.split("actor:", 1)[1]
            username, domain = full_username.split("@")
            try:
                actor = federation_models.Actor.objects.get(
                    preferred_username=username, domain_id=domain,
                )
            except federation_models.Actor.DoesNotExist:
                return queryset.none()

            return queryset.filter(**{self.actor_field: actor})
        elif value.lower().startswith("domain:"):
            domain = value.split("domain:", 1)[1]
            return queryset.filter(**{"{}__domain_id".format(self.actor_field): domain})
        else:
            return queryset.none()

        if self.distinct:
            qs = qs.distinct()
        return qs

    def filter_me(self, user, queryset):
        actor = getattr(user, "actor", None)
        if not actor:
            return queryset.none()

        return queryset.filter(**{self.actor_field: actor})
