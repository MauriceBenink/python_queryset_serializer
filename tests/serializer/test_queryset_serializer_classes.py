import pytest
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.models import User as AuthUser
from django.contrib.contenttypes.models import ContentType
from django.db.models import Prefetch
from queryset_serializer.serializers import DefaultMetaQuerySetSerializer

from .queryset_serializer_classes import (AuthUserSerializer,
                                          BuildingSerializer,
                                          ContentTypeSerializer,
                                          FloorSerializer, GroupSerializer,
                                          ManagerSerializer,
                                          PermissionSerializer,
                                          PositionSerializer, RoomSerializer,
                                          UserSerializer)


class TestQuerySetSerializerClassStructure:
    test_data_database_relations = [
        (BuildingSerializer,
         ['floors', 'floors__room', 'floors__floor_manager', 'floors__floor_manager__position',
          'floors__floor_manager__managers', 'floors__floor_manager__managers__position'], []),
        (FloorSerializer, ['room', 'floor_manager__managers', 'floor_manager__managers__position'],
         ['floor_manager', 'floor_manager__position']),
        (UserSerializer, ['managers', 'managers__position'], ['position']),
        (ManagerSerializer, [], ['position']),
        (RoomSerializer, [], []),
        (PositionSerializer, [], []),
    ]

    @pytest.mark.parametrize('serializer_class,expected_prefetch,expected_selects', test_data_database_relations)
    def test_preparing_database_relations(self, serializer_class, expected_prefetch, expected_selects):
        prefetch = serializer_class.database_relations['prefetch']
        select = serializer_class.database_relations['select']

        assert len(prefetch) == len(expected_prefetch) == len(set(prefetch) & set(expected_prefetch))
        assert len(select) == len(expected_selects) == len(set(select) & set(expected_selects))


class TestQuerySetSerializerWithModels:
    def setup(self):
        self.user_content_type = ContentType.objects.create(app_label='user_label', model='user_class_name')
        self.user_permission = Permission.objects.create(
            name='user_permission', codename='123', content_type=self.user_content_type)
        self.group_content_type = ContentType.objects.create(app_label='group_label', model='group_class_name')
        self.group_permission = Permission.objects.create(
            name='group_permission', codename='321', content_type=self.group_content_type)

        self.group = Group.objects.create(name='some_name')
        self.group.permissions.add(self.group_permission)
        self.user = AuthUser.objects.create(first_name='pietje', username='username', last_name='puk')
        self.user.user_permissions.add(self.user_permission)
        self.user.groups.add(self.group)

        self.user_many = AuthUser.objects.filter(pk=self.user.pk)
        self.group_many = Group.objects.filter(pk=self.group.pk)
        self.permission_many = Permission.objects.filter(
            pk__in=[self.user_permission.pk, self.group_permission.pk]
        ).order_by('pk')
        self.content_type_many = ContentType.objects.filter(pk__in=[
            self.user_content_type.pk, self.group_content_type.pk
        ]).order_by('pk')

    def check_serializer_result_in_depth(self, complex_1, complex_2):
        if isinstance(complex_1, dict) and isinstance(complex_2, dict):
            dict_1_keys = list(complex_1.keys())
            dict_2_keys = list(complex_2.keys())
            assert len(dict_1_keys) == len(dict_2_keys) == len(set(dict_1_keys) & set(dict_2_keys))
            for k in complex_1.keys():
                self.check_serializer_result_in_depth(complex_1[k], complex_2[k])
        elif isinstance(complex_1, list) and isinstance(complex_2, list):
            for val_1, val_2 in zip(complex_1, complex_2):
                self.check_serializer_result_in_depth(val_1, val_2)
        else:
            assert complex_1 == complex_2

    test_data_prefetch_calls = [
        (GroupSerializer, 'group', {
            'name': 'some_name',
            'permissions': [{'name': 'group_permission', 'codename': '321', 'content_type': {
                'app_label': 'group_label', 'model': 'group_class_name'
            }}]
        }, False),
        (GroupSerializer, 'group_many', [{
            'name': 'some_name',
            'permissions': [{'name': 'group_permission', 'codename': '321', 'content_type': {
                'app_label': 'group_label', 'model': 'group_class_name'
            }}]
        }], True),

        (AuthUserSerializer, 'user', {
            'username': 'username',
            'first_name': 'pietje',
            'last_name': 'puk',
            'groups': [{
                'name': 'some_name',
                'permissions': [{'name': 'group_permission', 'codename': '321', 'content_type': {
                    'app_label': 'group_label', 'model': 'group_class_name'
                }}]
            }],
            'user_permissions': [
                {'name': 'user_permission', 'codename': '123', 'content_type': {
                    'app_label': 'user_label', 'model': 'user_class_name'
                }}
            ]
        }, False),

        (AuthUserSerializer, 'user_many', [{
            'username': 'username',
            'first_name': 'pietje',
            'last_name': 'puk',
            'groups': [{
                'name': 'some_name',
                'permissions': [{'name': 'group_permission', 'codename': '321', 'content_type': {
                    'app_label': 'group_label', 'model': 'group_class_name'
                }}]
            }],
            'user_permissions': [
                {'name': 'user_permission', 'codename': '123', 'content_type': {
                    'app_label': 'user_label', 'model': 'user_class_name'
                }}
            ]
        }], True),

        (PermissionSerializer, 'user_permission', {
            'name': 'user_permission',
            'codename': '123',
            'content_type': {'app_label': 'user_label', 'model': 'user_class_name'}
        }, False),

        (PermissionSerializer, 'group_permission', {
            'name': 'group_permission',
            'codename': '321',
            'content_type': {'app_label': 'group_label', 'model': 'group_class_name'}
        }, False),

        (PermissionSerializer, 'permission_many', [
            {
                'name': 'user_permission',
                'codename': '123',
                'content_type': {'app_label': 'user_label', 'model': 'user_class_name'}
            },
            {
                'name': 'group_permission',
                'codename': '321',
                'content_type': {'app_label': 'group_label', 'model': 'group_class_name'}
            },

        ], True),

        (ContentTypeSerializer, 'group_content_type', {
            'app_label': 'group_label',
            'model': 'group_class_name'
        }, False),

        (ContentTypeSerializer, 'user_content_type', {
            'app_label': 'user_label',
            'model': 'user_class_name'
        }, False),

        (ContentTypeSerializer, 'content_type_many', [
            {
                'app_label': 'user_label',
                'model': 'user_class_name'
            },
            {
                'app_label': 'group_label',
                'model': 'group_class_name'
            }
        ], True),
    ]

    @pytest.mark.parametrize('serializer_class,self_attr,result,many', test_data_prefetch_calls)
    @pytest.mark.django_db()
    def test_prefetch_calls(self, serializer_class, self_attr, result, many):
        serializer = serializer_class(getattr(self, self_attr), many=many)
        self.check_serializer_result_in_depth(serializer.data, result)

        if many:
            queryset_prefetch_lookups = {
                q.prefetch_to if isinstance(q, Prefetch) else q: q for q in
                serializer.instance._prefetch_related_lookups
            }
            fetch_keys = list(queryset_prefetch_lookups.keys())
            prefetch = [
                '__'.join([
                    DefaultMetaQuerySetSerializer.prefetch_to_attr_prefix + y for y in x.split('__')
                ]) for x in serializer.child.database_relations['prefetch']
            ]

            assert len(fetch_keys) == len(prefetch) == len(set(fetch_keys) & set(prefetch))
