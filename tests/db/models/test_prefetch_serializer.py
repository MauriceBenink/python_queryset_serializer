import pytest
from django.db.models import Prefetch
from django.db.models.query import ModelIterable

from queryset_serializer.db.models import SerializerPrefetch


class MockQueryset:
    _iterable_class = ModelIterable


class TestPrefetchSerializer:
    test_data_prefetch_serializer = [
        ('lookup', 'attr', 'prefix', 'prefixattr', 'prefixattr'),
        ('a', 'attr', 'P_', 'P_attr', 'P_attr'),
        ('a', None, 'P_', 'P_a', 'P_a'),
        ('a__b', 'attr', 'P_', 'P_attr', 'P_a__P_attr'),
        ('a__b', None, 'P_', 'P_b', 'P_a__P_b'),
        ('a__b__c', 'attr', 'P_', 'P_attr', 'P_a__P_b__P_attr'),
        ('a__b__c', None, 'P_', 'P_c', 'P_a__P_b__P_c'),
    ]

    @pytest.mark.parametrize('lookup,attr,prefix,to_attr,prefetch_to', test_data_prefetch_serializer)
    def test_serializer(self, lookup, attr, prefix, to_attr, prefetch_to):
        serializer_prefetch = SerializerPrefetch(lookup, to_attr=attr, prefix=prefix)
        assert serializer_prefetch.to_attr == to_attr
        assert serializer_prefetch.prefetch_to == prefetch_to
        assert serializer_prefetch.prefetch_through == lookup

    test_data_patch_serializer = [
        ('lookup', 'prefix', 'prefixlookup', 'prefixlookup'),
        ('a', 'P_', 'P_a', 'P_a'),
        ('a', 'P_', 'P_a', 'P_a'),
        ('a__b', 'P_', 'P_b', 'P_a__P_b'),
        ('a__b__c', 'P_', 'P_c', 'P_a__P_b__P_c'),
    ]

    @pytest.mark.parametrize('lookup,prefix,to_attr,prefetch_to', test_data_patch_serializer)
    def test_patch_prefetch(self, lookup, prefix, to_attr, prefetch_to):
        queryset = MockQueryset()
        prefetch = Prefetch(lookup, queryset=queryset)
        patched_prefetch = SerializerPrefetch(prefetch.prefetch_to, queryset=prefetch.queryset, prefix=prefix)
        assert patched_prefetch.queryset == prefetch.queryset == queryset
        assert patched_prefetch.to_attr == to_attr
        assert patched_prefetch.prefetch_to == prefetch_to
        assert patched_prefetch.prefetch_through == lookup == prefetch.prefetch_to

    test_data_no_prefix = [
        ('lookup', 'attr'),
        ('a', 'attr'),
        ('a', None),
        ('a__b', 'attr'),
        ('a__b', None),
        ('a__b__c', 'attr'),
        ('a__b__c', None),
    ]

    @pytest.mark.parametrize('lookup,attr', test_data_no_prefix)
    def test_no_prefix(self, lookup, attr):
        prefetch_serializer = SerializerPrefetch(lookup, to_attr=attr)
        prefetch = Prefetch(lookup, to_attr=attr)

        assert prefetch_serializer.to_attr == prefetch.to_attr
        assert prefetch_serializer.prefetch_to == prefetch.prefetch_to
        assert prefetch_serializer.prefetch_through == prefetch.prefetch_through
