from django.db import models

from queryset_serializer.db.models import SerializerPrefetch
from queryset_serializer.serializers.model import PrefetchToAttrSerializerList
from rest_framework import serializers


def get_meta(cls):
    """
    Will try and find the serializer class PrefetchMeta
    :param cls:
    :return:
    """
    if isinstance(cls, dict):
        return cls.get('Meta', Config.meta_class)
    else:
        return getattr(cls, 'Meta', Config.meta_class)


def get_meta_val(meta, variable):
    """
    Will return the variable from the given class (Should be PrefetchMeta class)
    :param meta:
    :param variable:
    :return:
    """
    return getattr(meta, variable, getattr(Config.meta_class, variable))


class _QuerySetSerializer(serializers.ModelSerializer):
    """
    This class exists to inherit from. Trough inheritance default_meta_class can check the instance
    of the class. This cannot be defined lower in the file because
    default_meta_class / QuerySetMetaSerializer depend on it statically
    """
    pass


class DefaultMetaQuerySetSerializer:
    """
    Class with default values for PrefetchMeta in case values/class aren't specified
    """
    # Prefix that will be used to give fields a unique name (Cannot start with a _, this will mess up __ relations)
    prefetch_to_attr_prefix = 'PREF_'

    # Special Perfecting class with support for prefetching trough the to_attr fields
    prefetch_class = SerializerPrefetch

    # List serializer class
    list_serializer_class = serializers.ListSerializer

    # if it is a instance of this class then Prefetching can be applied
    base_serializer_class = _QuerySetSerializer

    # Class which will make sure everything gets prefetched. the default class will also apply relations
    # from Prefetch(to_attr=) to Serializer(source=). This tends to speedup resolving serializer.data .
    # If you don't want this use the class PrefetchSerializerList instead (this will only prefetch
    prefetch_listing = PrefetchToAttrSerializerList


class Config:
    meta_class = DefaultMetaQuerySetSerializer


class QuerySetMetaSerializer(serializers.SerializerMetaclass):
    """
    Meta class for the serializers, this class will prepare fields and initiate relations
    """

    def __new__(cls, name, bases, attrs):
        attrs['_declared_fields'] = cls._get_declared_fields(bases, attrs)

        # if any values are specified in the class or in on of its parents then use this (copied) value
        # if there is nothing specified then default to {'select': [], 'prefetch': []}
        attrs['database_relations'] = {key: value[::] for key, value in (
            attrs.get('database_relations') or
            attrs['_declared_fields'].get('database_relations') or
            {'select': [], 'prefetch': []}
        ).items()}

        cls._set_prefetch_fields(attrs)
        cls._set_source_prefetch_serializers(attrs)
        return super(serializers.SerializerMetaclass, cls).__new__(cls, name, bases, attrs)

    @classmethod
    def _set_source_prefetch_serializers(mcs, attrs) -> None:
        """
        Trigger for changing child serializers
        :param attrs:
        :return:
        """
        meta = get_meta(attrs)
        prefix = get_meta_val(meta, 'prefetch_to_attr_prefix')
        # getting the class that will modify the serializers
        prefetch_listing = get_meta_val(meta, 'prefetch_listing')
        prefetch_listing.set_serializer_sources(
            attrs['database_relations']['prefetch'][::], attrs['_declared_fields'], prefix
        )

    @classmethod
    def _set_prefetch_fields(mcs, attrs):
        """
        Collect all fields that need to be prefetched / selected and populate attrs['database_relations'] with them
        :param attrs: dict[str, object]
        :return: dict[str, list]
        """

        # the meta class gets triggered on load order of the serializers because of this
        # we can be certain the child serializer has already done this method for itself and its children
        # meaning we can read all the child serializer its relations from its obj.database_relations
        # this will work for any amount of depth. (Could be an issue with Serializers mentioning each other / itself)

        # could possibly also be done with Prefetch object and then in the queryset parameter selecting / prefetching
        # the child its parameters. Not sure about outcome and if that will prefetch everything in one go or chuncks
        for has_many, field_name, obj in mcs._get_related_prefetches(attrs):
            if not has_many:
                # if the relations has `to one` then we can copy its relations in the same way
                attrs['database_relations']['select'] += (
                    [field_name] + [f'{field_name}__{rel}' for rel in obj.database_relations['select']]
                )
                attrs['database_relations']['prefetch'] += (
                    [f'{field_name}__{rel}' for rel in obj.database_relations['prefetch']]
                )
            else:
                # if the relations is `to many` then even the selects need to be moved to prefetch since now it will
                # result into multiple fields
                attrs['database_relations']['prefetch'] += (
                    [field_name] + [f'{field_name}__{rel}' for rel in (
                        obj.database_relations['select'] + obj.database_relations['prefetch']
                    )]
                )
        return attrs['database_relations']

    @classmethod
    def _get_related_prefetches(mcs, attrs):
        """
        Method for getting all fields that need prefetching from the _declared_fields
        :param attrs: dict[str, object]
        :return: list[tuple[bool, str, serializers.Serializer]]
        """
        fields = []
        meta = get_meta(attrs)
        list_serializer = get_meta_val(meta, 'list_serializer_class')
        base_serializer = get_meta_val(meta, 'base_serializer_class')

        for field_name, obj in attrs['_declared_fields'].items():
            if isinstance(obj, base_serializer):
                # in this case it will return a single model. so we can assume the relations is `to one`
                fields += [(False, field_name, obj)]
            if isinstance(obj, list_serializer):
                if not isinstance(obj.child, base_serializer):
                    continue
                fields += [(True, field_name, obj.child)]
        return fields


class QuerySetSerializer(_QuerySetSerializer, metaclass=QuerySetMetaSerializer):
    # attribute that stores the relations of the serializer
    database_relations = {'select': [], 'prefetch': []}

    @classmethod
    def _check_value(cls, value, multi_model=True):
        """
        If the value is a queryset then apply the prefetches and select related.
        if the value is not a queryset then return the value itself
        :param value:
        :return:
        """

        # in case it is a single model and not a queryset, then prefetches can be applied in this way to the model
        # itself. The queryset being None makes sure everything returns as if the queryset has no prefetches at all
        if (not multi_model) and isinstance(value, models.Model):
            models.prefetch_related_objects([value], *cls._prepare_prefetch_list())

        if not isinstance(value, (models.QuerySet, models.Manager)):
            return value

        queryset = value.all() if isinstance(value, models.Manager) else value

        prefetch_list = cls._prepare_prefetch_list(queryset)
        select = cls.database_relations['select'][::]

        return queryset.select_related(
            *select
        ).prefetch_related(
            *prefetch_list
        )

    @classmethod
    def _prepare_prefetch_list(cls, queryset=None):
        """
        initiate the class to get all the prefetch_list
        :param queryset: models.QuerySet
        :return: list[str | SerializerPrefetch]
        """
        meta = get_meta(cls)
        prefetch_listing = get_meta_val(meta, 'prefetch_listing')
        # initiate the model for populating the prefetch_list, this model will return your prefetch_list
        prefetch_listing = prefetch_listing(
            cls.database_relations['prefetch'][::], queryset, meta, Config.meta_class
        )

        return prefetch_listing.prefetch_list()

    @classmethod
    def many_init(cls, *args, **kwargs):
        """
        Method got overwritten to make sure the ListSerializer could be overwritten in the same way as the rest of
        the values can be overwritten
        rest of the code is copied from the parent class
        :param args:
        :param kwargs:
        :return:
        """
        allow_empty = kwargs.pop('allow_empty', None)
        child_serializer = cls(*args, **kwargs)
        list_kwargs = {
            'child': child_serializer,
        }
        if allow_empty is not None:
            list_kwargs['allow_empty'] = allow_empty
        list_kwargs.update({
            key: value for key, value in kwargs.items()
            if key in serializers.LIST_SERIALIZER_KWARGS
        })

        meta = get_meta(cls)
        list_serializer_class = get_meta_val(meta, 'list_serializer_class')
        return list_serializer_class(*args, **list_kwargs)

    def __new__(cls, *args, **kwargs):
        """
        Check all the arguments / keyword arguments to find any value where a queryset might live
        :param args:
        :param kwargs:
        :return:
        """

        many = kwargs.get('many', False)

        args = list(args)
        if len(args) > 0:
            args[0] = cls._check_value(args[0], many)
        if 'data' in kwargs:
            kwargs['data'] = cls._check_value(kwargs['data'], many)
        if 'instance' in kwargs:
            kwargs['instance'] = cls._check_value(kwargs['instance'], many)

        return super().__new__(cls, *args, **kwargs)
