from django.db import models


class _BasePrefetchSerializerList:
    """
    Baseclass from which can be inherited from with exceptions to mimic the behaviour of a Interface/abstract class
    """
    @staticmethod
    def set_serializer_sources(prefetches, declared_fields, prefix) -> None:
        """
        Method in which the serializer can be modified, if you simply pass this method then serializers will be
        unchanged
        :param prefetches: list[str]
        :param declared_fields: dict[str, object]
        :param prefix: str
        :return: None
        """
        raise NotImplementedError('This class should not be called directly, if inherited overwrite this method')

    def __init__(self, initial_prefetch_list, queryset, meta, default_meta):
        """

        :param initial_prefetch_list: list[str]
        :param queryset: models.QuerySet
        :param meta: object
        :param default_meta: object
        """
        self.prefetch = initial_prefetch_list
        self.queryset = queryset
        # Create a lookup map based on field_name: field / Prefetch_object
        self.queryset_prefetch_lookups: dict[str, str | models.Prefetch] = {
            q.prefetch_to if isinstance(q, models.Prefetch) else q: q for q in self.queryset._prefetch_related_lookups
        } if self.queryset is not None else {}

    def prefetch_list(self):
        """
        Method in which the prefetch_list will be created
        :return: list[str | models.Prefetch]
        """
        raise NotImplementedError('This class should not be called directly, if inherited overwrite this method')


class PrefetchSerializerList(_BasePrefetchSerializerList):
    @staticmethod
    def set_serializer_sources(prefetches, declared_fields, prefix) -> None:
        """
        With this class we dont want to make to_attr / source relations. so we skip this to leave the serializers
        unaffected
        :param prefetches: list[str]
        :param declared_fields: dict[str, object]
        :param prefix: str
        :return: None
        """
        pass

    def prefetch_list(self):
        """
        We can simply return all prefetch relations that are missing in the prefetch_related_lookups
        if it is already there it can be ignored
        :return: list[str]
        """
        return [prefetch for prefetch in self.prefetch if prefetch not in self.queryset_prefetch_lookups.keys()]


class PrefetchToAttrSerializerList(_BasePrefetchSerializerList):
    @staticmethod
    def set_serializer_sources(prefetches, declared_fields, prefix) -> None:
        """
        We want to set the source of all serializers with a `many` relation to have its source changed to
        the field name with the prefix, this should match with the models.Prefetch(to_attr='{should_match}')
        This way we can keep serializer names the same but still store results in a to_attr in prefetch
        :param prefetches: list[str]
        :param declared_fields: dict[str, object]
        :param prefix: str
        :return: None
        """
        for prefetch in prefetches:
            # only get the fields that are in prefetch and in the declared_fields
            if prefetch in declared_fields:
                # the name that should match the to_attr on models.Prefetch
                source = f'{prefix}{prefetch}'
                if declared_fields[prefetch].source is None:
                    # We have to set the _kwargs value. otherwise the deepcopy (see serializer.Serializer.get_fields)
                    # will not initiate the class with the source field on the copied model
                    declared_fields[prefetch]._kwargs['source'] = source
                    declared_fields[prefetch].source = source

    def __init__(self, initial_prefetch_list, queryset, meta, default_meta):
        super().__init__(initial_prefetch_list, queryset, meta, default_meta)
        # Two extra values we need for initiating the prefetch classes with the right prefix
        self.prefix = getattr(meta, 'prefetch_to_attr_prefix', getattr(default_meta, 'prefetch_to_attr_prefix'))
        self.prefetch_class = getattr(meta, 'prefetch_class', getattr(default_meta, 'prefetch_class'))

    def _create_prefetch_obj(self, prefetch):
        """
        create the (SerializerPrefetch) Prefetch class with an prefix
        :param prefetch: str
        :return: Prefetch
        """
        return self.prefetch_class(prefetch, prefix=self.prefix)

    def _patch_prefetch_obj(self, prefetch):
        """
        Get an already existing Prefetch object and replace it with a new (SerializerPrefetch) Prefetch class
        this makes sure the queryset on this Prefetch object will remain intact.
        :param prefetch: str
        :return: None
        """
        prefetch_obj = self.queryset_prefetch_lookups[prefetch]
        prefetch_index = self.queryset._prefetch_related_lookups.index(self.queryset_prefetch_lookups[prefetch])
        self.queryset._prefetch_related_lookups[prefetch_index] = self.prefetch_class(
            prefetch_obj.prefetch_to, queryset=prefetch_obj.queryset, prefix=self.prefix
        )

    def _edit_related_lookups(self, queryset):
        """
        Method to easily change the _prefetch_related_lookups tuple to a list temporary so it can be changed and edited
        :param queryset: models.QuerySet
        :return:
        """
        class WithEditRelatedLookup:
            def __init__(self, qs):
                self.qs = qs

            def __enter__(self):
                self.qs._prefetch_related_lookups = list(self.qs._prefetch_related_lookups)

            def __exit__(self, exc_type, exc_val, exc_tb):
                self.qs._prefetch_related_lookups = tuple(self.qs._prefetch_related_lookups)

        return WithEditRelatedLookup(queryset)

    def prefetch_list(self):
        """
        Get all the prefetch models with to_attr set and with to_attr patched in the queryset
        :return: list[models.Prefetch]
        """
        if self.queryset is None:
            return [self._create_prefetch_obj(prefetch) for prefetch in self.prefetch]

        prefetch_list = []
        with self._edit_related_lookups(self.queryset):
            for prefetch in self.prefetch:
                if prefetch not in self.queryset_prefetch_lookups.keys():
                    prefetch_list += [self._create_prefetch_obj(prefetch)]
                    continue
                # if a object has the same name as a prefetch and has a to_attr set. then it means there is a naming
                # violation (same field mentioned twice) so this should be impossible / an error
                self._patch_prefetch_obj(prefetch)
                continue

        return prefetch_list
