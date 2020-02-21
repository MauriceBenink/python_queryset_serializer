## QuerysetSerializer

This package adds a serializer to ensure all models in the serializers get properly prefetched or selected

## Usage

Simply install the package into your project and import the serializer

```python
from queryset_serializer import QuerySetSerializer

class MyModelSerializer(QuerySetSerializer):
    ... 
    class Meta:
        ...

```

In order to prefetch/select everything make sure all serializers used are of QuerySetSerializer

Note : You cannot mix `restframework.serializer.ModelSerializer` with this class 
(However all instance of ModelSerializer should be replaceable)


##Config
configurations can be changed as following:
```python
from queryset_serializer.serializers import Config
Config.meta_class.{setting} = {new_value}
```

these are the relevant settings : \
- prefetch_to_attr_prefix , What string will be used as prefix.
- prefetch_listing , How the prefetch is done (Options: PrefetchToAttrSerializerList, PrefetchSerializerList)

### prefetch_listing
there are 2 options for the prefetch_listing. (Located in `queryset_serializer.serializers.model`)\
- `PrefetchToAttrSerializerList` will prefetch/select relations and use the `to_attr` attribute of the `Prefetch` class
- `PrefetchSerializerList` will only prefetch/select relations


This package by default makes use PrefetchToAttrSerializerList,
The benefit of this is that the `.all()` calls on the relations are nog longer lazy.

This can significantly speed up performance especially on a queryset with a large amount of results or 
if there are a lot of child (queryset)serializer

This can also be turned off, and instead do a regular prefetch:
```python
from queryset_serializer.serializers import Config
from queryset_serializer.serializers.model import PrefetchSerializerList
Config.meta_class.prefetch_listing = PrefetchSerializerList
```