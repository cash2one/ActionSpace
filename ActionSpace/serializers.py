# coding=utf-8
from django.contrib.auth.models import User, Group
from rest_framework import serializers
from om.models import Computer, Entity
from switch.models import Machine


# Serializers define the API representation.
class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'is_staff')


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')


class EntitySerializer(serializers.ModelSerializer):
    system = serializers.StringRelatedField(many=False)

    class Meta:
        model = Entity
        fields = ('name', 'system')


class ServerSerializer(serializers.ModelSerializer):
    entity = EntitySerializer(many=True, read_only=True)

    class Meta:
        model = Computer
        fields = ('entity', 'env', 'ip', 'host', 'installed_agent')
        #  depth = 2


class MachineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Machine
        fields = ('ip', 'mac_hex', 'entity_name', 'switch_ip', 'if_name')
