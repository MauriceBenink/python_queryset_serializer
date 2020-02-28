import pytest

from queryset_serializer.db.models import SerializerPrefetch
from queryset_serializer.serializers import (DefaultMetaQuerySetSerializer,
                                             QuerySetMetaSerializer,
                                             QuerySetSerializer, get_meta,
                                             get_meta_val)


class MockClass:
    def __init__(self, **kwargs):
        self.__dict__ = kwargs


class MockListSerializer:
    def __init__(self, child=None, source=None, **kwargs):
        self.child = child
        self.source = source or child.source
        self._kwargs = kwargs
        self._kwargs.setdefault('source', self.source)


class MockBaseSerializer:
    def __init__(self, select=[], prefetch=[], source=None, **kwargs):
        self.database_relations = {'prefetch': prefetch, 'select': select}
        self.source = source
        self._kwargs = kwargs
        self._kwargs.setdefault('source', self.source)


class TestFunctions:
    test_data_get_meta = [
        (MockClass(Meta=object), object),
        (MockClass(Meta='MetaString'), 'MetaString'),
        ({'Meta': object}, object),
        ({'Meta': 'MetaString'}, 'MetaString'),
    ]

    @pytest.mark.parametrize('input,output', test_data_get_meta)
    def test_get_meta(self, input, output):
        assert get_meta(input) == output

    test_data_get_meta_val = [
        (MockClass(prefetch_to_attr_prefix='P_'), 'prefetch_to_attr_prefix', 'P_'),
        (MockClass(), 'prefetch_to_attr_prefix', DefaultMetaQuerySetSerializer.prefetch_to_attr_prefix),

        (MockClass(prefetch_class='prefetch_class'), 'prefetch_class', 'prefetch_class'),
        (MockClass(), 'prefetch_class', DefaultMetaQuerySetSerializer.prefetch_class),

        (MockClass(list_serializer_class='list_serializer_class'), 'list_serializer_class', 'list_serializer_class'),
        (MockClass(), 'list_serializer_class', DefaultMetaQuerySetSerializer.list_serializer_class),

        (MockClass(base_serializer_class='base_serializer_class'), 'base_serializer_class', 'base_serializer_class'),
        (MockClass(), 'base_serializer_class', DefaultMetaQuerySetSerializer.base_serializer_class),

        (MockClass(prefetch_listing='prefetch_listing'), 'prefetch_listing', 'prefetch_listing'),
        (MockClass(), 'prefetch_listing', DefaultMetaQuerySetSerializer.prefetch_listing),
    ]

    @pytest.mark.parametrize('meta,value,output', test_data_get_meta_val)
    def test_get_meta_val(self, meta, value, output):
        assert get_meta_val(meta, value) == output


class TestQuerySetMetaSerializer:

    mock_meta = MockClass(
        list_serializer_class=MockListSerializer,
        base_serializer_class=MockBaseSerializer,
        prefetch_to_attr_prefix='P_'
    )

    test_data__set_prefetch_fields = [
        (
            {
                'a': MockBaseSerializer(
                    select=['x'],
                    prefetch=['y', 'z']
                ),
                'b': MockListSerializer(child=MockBaseSerializer(
                    select=['x'],
                    prefetch=['y']
                )),
                'c': MockBaseSerializer(),
                'd': MockListSerializer(child=MockBaseSerializer()),
                'some_field': None
            },
            ['a__y', 'a__z', 'b', 'b__x', 'b__y', 'd'],
            ['a', 'a__x', 'c']
        ),
        (
            {},
            [],
            []
        ),
        (
            {'some_field': None},
            [],
            []
        )
    ]

    @pytest.mark.parametrize('declared_fields,expected_prefetch,expected_select',
                             test_data__set_prefetch_fields)
    def test__set_prefetch_fields(self, declared_fields, expected_prefetch, expected_select):
        attrs = {
            'Meta': self.mock_meta,
            '_declared_fields': declared_fields,
            'database_relations': {'prefetch': [], 'select': []}
        }
        rels = QuerySetMetaSerializer._set_prefetch_fields(attrs)
        assert len(rels['prefetch']) == len(expected_prefetch) == len(set(rels['prefetch']) & set(expected_prefetch))
        assert len(rels['select']) == len(expected_select) == len(set(rels['select']) & set(expected_select))

    test_data__set_source_prefetch_serializers = [
        (
            {
                'a': MockBaseSerializer(),
                'b': MockListSerializer(child=MockBaseSerializer()),
                'c': MockBaseSerializer(source='SomeSource'),
                'd': MockListSerializer(child=MockBaseSerializer(source='SomeSource')),
                'e': MockListSerializer(child=MockBaseSerializer(), source='SomeSource'),
                'some_field': None
            },
            ['a', 'b', 'c', 'd', 'e'],
            {
                'a': 'P_a',
                'b': 'P_b',
                'c': 'SomeSource',
                'd': 'SomeSource',
                'e': 'SomeSource'
            }
        ),
        (
            {},
            [],
            {}
        ),
        (
            {'some_field': None},
            [],
            {}
        )
    ]

    @pytest.mark.parametrize('declared_fields,prefetch,sources', test_data__set_source_prefetch_serializers)
    def test__set_source_prefetch_serializers(self, declared_fields, prefetch, sources):
        attrs = {
            'Meta': self.mock_meta,
            '_declared_fields': declared_fields,
            'database_relations': {'prefetch': prefetch, 'select': []}
        }
        QuerySetMetaSerializer._set_source_prefetch_serializers(attrs)
        for key, value in sources.items():
            assert attrs['_declared_fields'][key].source == value
            assert attrs['_declared_fields'][key]._kwargs['source'] == value


class TestQuerySetSerializer:
    test_data__prepare_prefetch_list = [
        (['a', 'b', 'c', 'd'], None, {
            'a': SerializerPrefetch('a', prefix='PREF_'),
            'b': SerializerPrefetch('b', prefix='PREF_'),
            'c': SerializerPrefetch('c', prefix='PREF_'),
            'd': SerializerPrefetch('d', prefix='PREF_')
        }),
        (['a', 'a__b', 'a__b__c'], None, {
            'a': SerializerPrefetch('a', prefix='PREF_'),
            'a__b': SerializerPrefetch('a__b', prefix='PREF_'),
            'a__b__c': SerializerPrefetch('a__b__c', prefix='PREF_'),
        })
    ]

    @pytest.mark.parametrize('prefetch,queryset,result_prefetches', test_data__prepare_prefetch_list)
    def test__prepare_prefetch_list(self, prefetch, queryset, result_prefetches):
        serializer = QuerySetSerializer
        serializer.database_relations = {'prefetch': prefetch, 'select': []}
        prefetch_list = serializer._prepare_prefetch_list(queryset)
        for item in prefetch_list:
            result_prefetch = result_prefetches[item.prefetch_through]
            assert result_prefetch.to_attr == item.to_attr
            assert result_prefetch.prefetch_to == item.prefetch_to
