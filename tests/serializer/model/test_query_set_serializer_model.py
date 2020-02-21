import pytest
from django.db.models import Prefetch
from queryset_serializer.db.models import SerializerPrefetch
from queryset_serializer.serializers import DefaultMetaQuerySetSerializer
from queryset_serializer.serializers.model import (PrefetchSerializerList,
                                                   PrefetchToAttrSerializerList,
                                                   _BasePrefetchSerializerList)


class MockQuerySet:
    def __init__(self, queryset_prefetch_lookups=[]):
        self._prefetch_related_lookups = tuple(queryset_prefetch_lookups)


class MockMeta:
    def __init__(self, **kwargs):
        self.__dict__ = kwargs


class MockSerializer:
    source = None
    _kwargs = {}

    def __init__(self, source=None, **kwargs):
        self.source = source
        self._kwargs = kwargs
        self._kwargs.setdefault('source', self.source)


class TestBasePrefetchSerializerList:
    def test_not_implemented(self):
        serializer_list = _BasePrefetchSerializerList(
            ['a', 'a__b'], MockQuerySet(), MockMeta(), DefaultMetaQuerySetSerializer
        )
        with pytest.raises(NotImplementedError):
            serializer_list.prefetch_list()
        with pytest.raises(NotImplementedError):
            _BasePrefetchSerializerList.set_serializer_sources(['a', 'a__b'], ['a', 'b', 'c', 'd'], 'P_')


class TestPrefetchSerializerListModel:
    test_data_queryset_prefetch_lookups = [
        (['a', 'a__b', 'a__c', Prefetch('a__d'), Prefetch('x')], ['a', 'a__b', 'a__c', 'a__d', 'x']),
        ([Prefetch('x')], ['x']),
        (['a'], ['a']),
        ([], [])
    ]

    @pytest.mark.parametrize('values,keys', test_data_queryset_prefetch_lookups)
    def test_queryset_prefetch_lookups(self, values, keys):

        for model in [_BasePrefetchSerializerList, PrefetchSerializerList, PrefetchToAttrSerializerList]:
            model_instance = model([], MockQuerySet(values), MockMeta(), DefaultMetaQuerySetSerializer)
            prefetch_keys = model_instance.queryset_prefetch_lookups.keys()
            prefetch_values = model_instance.queryset_prefetch_lookups.values()
            assert len(set(prefetch_values)) == len(set(values)) == len(set(values) & set(prefetch_values))
            assert len(set(prefetch_keys)) == len(set(keys)) == len(set(keys) & set(prefetch_keys))

    def test_queryset_prefetch_lookups_no_queryset(self):
        for model in [_BasePrefetchSerializerList, PrefetchSerializerList, PrefetchToAttrSerializerList]:
            model_instance = model([], None, MockMeta(), DefaultMetaQuerySetSerializer)
            assert model_instance.queryset_prefetch_lookups == {}

    test_data_set_serializer_sources = [
        (
            PrefetchToAttrSerializerList,
            'P_',
            ['a', 'a__b', 'a__b__c'],
            {'a': MockSerializer(), 'a__b': MockSerializer(), 'a__b__c': MockSerializer(), 'd': None, 'e': None},
            {'a': 'P_a', 'a__b': 'P_a__b', 'a__b__c': 'P_a__b__c'},
            [],
            {'d': None, 'e': None}
        ), (
            PrefetchToAttrSerializerList,
            'PREF_',
            ['a', 'a__b'],
            {'a': MockSerializer(), 'a__b': MockSerializer(), 'a__b__c': MockSerializer(), 'z': None},
            {'a': 'PREF_a', 'a__b': 'PREF_a__b', 'a__b__c': None},
            [],
            {'z': None}
        ), (
            PrefetchToAttrSerializerList,
            'P_',
            [],
            {'a': MockSerializer(), 'a__b': MockSerializer(), 'a__b__c': MockSerializer(), 'z': None},
            {'a': None, 'a__b': None, 'a__b__c': None},
            [],
            {'z': None}
        ), (
            PrefetchToAttrSerializerList,
            'P_',
            ['a', 'a__b', 'g__k__h'],
            {'a': MockSerializer(), 'a__b': MockSerializer('x__y'), 'a__b__c': MockSerializer('a'), 'z': None},
            {'a': 'P_a', 'a__b': 'x__y', 'a__b__c': 'a'},
            ['g__k__h'],
            {'z': None}
        ), (
            PrefetchToAttrSerializerList,
            'P_',
            ['a', 'a__b', 'a__b__c'],
            {'d': None, 'e': None},
            {},
            ['a', 'a__b', 'a__b__c'],
            {'d': None, 'e': None}
        ), (
            PrefetchSerializerList,
            'P_',
            ['a', 'b', 'c', 'a__b', 'b__c'],
            {'a': MockSerializer('x__y'), 'b': MockSerializer(), 'c': MockSerializer(), 'd': 'some_field', 'e': None},
            {'a': 'x__y', 'b': None, 'c': None},
            ['a__b', 'b__c'],
            {'d': 'some_field', 'e': None}
        ),

    ]

    @pytest.mark.parametrize('model_class,prefix,prefetch,fields,serializers_result,ignored,fields_result',
                             test_data_set_serializer_sources)
    def test_set_serializer_sources(self, model_class, prefix, prefetch, fields,
                                    serializers_result, ignored, fields_result):

        model_class.set_serializer_sources(prefetch, fields, prefix)

        for key, value in serializers_result.items():
            if key in ignored:
                assert fields[key] is None
                continue
            assert fields[key].source == value
            assert fields[key]._kwargs['source'] == value

        for key, value in fields_result.items():
            assert key in fields_result
            assert fields_result[key] == value

        tot_list = list(fields_result.keys()) + list(serializers_result.keys())
        fields_list = list(fields.keys())
        combined_set = set(tot_list) & set(fields_list)

        assert len(tot_list) == len(fields_list) == len(combined_set)


class TestPrefetchSerializerList:
    test_data_prefetch_list = [
        (['a', 'a__b'], MockQuerySet(), ['a', 'a__b']),
        (['a', 'b', 'c'], MockQuerySet(['a', 'a__b', 'd__f']), ['b', 'c']),
        (['a', 'b', 'c'], MockQuerySet(['a', 'b', 'c']), []),
        ([], MockQuerySet(), []),
    ]

    @pytest.mark.parametrize('prefetch,queryset,result_list', test_data_prefetch_list)
    def test_prefetch_list(self, prefetch, queryset, result_list):
        serializer = PrefetchSerializerList(prefetch, queryset, MockMeta(), DefaultMetaQuerySetSerializer)
        prefetch_list = serializer.prefetch_list()
        assert len(prefetch_list) == len(result_list) == len(set(prefetch_list) & set(result_list))


class TestPrefetchToAttrSerializerList:
    test_data_prefetch_list = [
        (
            ['a', 'b', 'a__b'],
            MockQuerySet(),
            MockMeta(prefetch_to_attr_prefix='P_'), {
                'a': SerializerPrefetch('a', prefix='P_'),
                'b': SerializerPrefetch('b', prefix='P_'),
                'a__b': SerializerPrefetch('a__b', prefix='P_')
            }, {
            }
        ),
        (
            ['a', 'b', 'a__b', 'x__y'],
            MockQuerySet([Prefetch('a'), Prefetch('x__y', to_attr='attr')]),
            MockMeta(prefetch_to_attr_prefix='P_'), {
                'b': SerializerPrefetch('b', prefix='P_'),
                'a__b': SerializerPrefetch('a__b', prefix='P_'),
                'x__y': SerializerPrefetch('x__y', prefix='P_'),
            }, {
                'a': SerializerPrefetch('a', prefix='P_'),
            }
        ),
        (
            ['a', 'a__b', 'a__b__c'],
            MockQuerySet([Prefetch('a'), Prefetch('a__b'), Prefetch('a__b__c')]),
            MockMeta(prefetch_to_attr_prefix='P_'), {
            }, {
                'a': SerializerPrefetch('a', prefix='P_'),
                'a__b': SerializerPrefetch('a__b', prefix='P_'),
                'a__b__c': SerializerPrefetch('a__b__c', prefix='P_'),
            }
        ),
        (
            [],
            MockQuerySet([Prefetch('a'), Prefetch('x__y', to_attr='attr')]),
            MockMeta(prefetch_to_attr_prefix='P_'), {
            }, {
            }
        ),
        (
            [],
            None,
            MockMeta(prefetch_to_attr_prefix='P_'), {
            }, {
            }
        ),
        (
            ['a', 'a__b', 'a__b__c'],
            None,
            MockMeta(prefetch_to_attr_prefix='P_'), {
                'a': SerializerPrefetch('a', prefix='P_'),
                'a__b': SerializerPrefetch('a__b', prefix='P_'),
                'a__b__c': SerializerPrefetch('a__b__c', prefix='P_'),
            }, {
            }
        ),
    ]

    @pytest.mark.parametrize('prefetch,queryset,meta,result_list,patch_result', test_data_prefetch_list)
    def test_prefetch_list(self, prefetch, queryset, meta, result_list, patch_result):
        serializer = PrefetchToAttrSerializerList(
            prefetch, queryset=queryset, meta=meta, default_meta=DefaultMetaQuerySetSerializer
        )

        prefetch_list = serializer.prefetch_list()
        for prefetch_obj in prefetch_list:
            resulting_prefetch = result_list[prefetch_obj.prefetch_through]
            assert resulting_prefetch.to_attr == prefetch_obj.to_attr
            assert resulting_prefetch.prefetch_through == prefetch_obj.prefetch_through
            assert resulting_prefetch.prefetch_to == prefetch_obj.prefetch_to

        for key, resulting_prefetch in patch_result.items():
            prefetch_obj = serializer.queryset_prefetch_lookups[key]
            assert prefetch_obj.to_attr is None
            assert serializer.prefix in resulting_prefetch.to_attr
            assert resulting_prefetch.prefetch_through == prefetch_obj.prefetch_through == prefetch_obj.prefetch_to
            assert serializer.prefix in resulting_prefetch.prefetch_to

        tot_list = list(result_list.keys()) + list(patch_result.keys())
        combined_set = set(tot_list) & set(prefetch)

        assert len(tot_list) == len(prefetch) == len(combined_set)
