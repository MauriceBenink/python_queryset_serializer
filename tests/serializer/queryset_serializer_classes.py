from django.contrib.auth.models import Group, Permission
from django.contrib.auth.models import User as AuthUser
from django.contrib.contenttypes.models import ContentType
from django.db import models
from rest_framework import serializers

from queryset_serializer.serializers import QuerySetSerializer


class Position(models.Model):
    position = models.CharField()

    class Meta:
        abstract = True


class PositionSerializer(QuerySetSerializer):
    position = serializers.CharField()

    class Meta:
        abstract = True
        model = Position
        fields = ('position',)


class Manager(models.Model):
    position = models.ForeignKey(Position, on_delete=models.CASCADE)

    class Meta:
        abstract = True


class ManagerSerializer(QuerySetSerializer):
    position = PositionSerializer()

    class Meta:
        model = Manager
        fields = ('position',)


class User(models.Model):
    name = models.CharField()
    tel = models.IntegerField()
    position = models.ForeignKey(Position, on_delete=models.CASCADE)
    managers = models.ManyToManyField(Manager)

    class Meta:
        abstract = True


class UserSerializer(QuerySetSerializer):
    position = PositionSerializer()
    managers = ManagerSerializer(many=True)

    class Meta:
        model = User
        fields = ('name', 'tel', 'position', 'managers')


class Building(models.Model):
    class Meta:
        abstract = True


class Floor(models.Model):
    floor_manager = models.ForeignKey(User, on_delete=models.CASCADE)
    floor_num = models.IntegerField()
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='floors')

    class Meta:
        abstract = True


class Room(models.Model):
    room_num = models.IntegerField()
    chairs = models.IntegerField()
    floor = models.ForeignKey(Floor, on_delete=models.CASCADE, related_name='room')

    class Meta:
        abstract = True


class RoomSerializer(QuerySetSerializer):
    class Meta:
        model = Room
        fields = ('room_num', 'chairs')


class FloorSerializer(QuerySetSerializer):
    room = RoomSerializer(many=True)
    floor_manager = UserSerializer()

    class Meta:
        model = Floor
        fields = ('room', 'floor_manager', 'floor_num')


class BuildingSerializer(QuerySetSerializer):
    floors = FloorSerializer(many=True)

    class Meta:
        model = Building
        fields = ('floors',)


class ContentTypeSerializer(QuerySetSerializer):
    class Meta:
        model = ContentType
        fields = ('app_label', 'model')


class PermissionSerializer(QuerySetSerializer):
    content_type = ContentTypeSerializer()

    class Meta:
        model = Permission
        fields = ('name', 'codename', 'content_type')


class GroupSerializer(QuerySetSerializer):
    permissions = PermissionSerializer(many=True)

    class Meta:
        model = Group
        fields = ('name', 'permissions')


class AuthUserSerializer(QuerySetSerializer):
    groups = GroupSerializer(many=True)
    user_permissions = PermissionSerializer(many=True)

    class Meta:
        model = AuthUser
        fields = ('username', 'first_name', 'last_name', 'groups', 'user_permissions')
