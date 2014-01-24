import cPickle

from django.db import models
from django.core.exceptions import ValidationError

from tools import to_string
from tools import safe_loads


class SmartCacheQuerySet(models.query.QuerySet):
    def filter(self, *args, **kwargs):
        kwargs.pop('valid', '')
        only_valid = kwargs.pop('only_valid', True)
        if only_valid:
            q = super(SmartCacheQuerySet, self).filter(valid=True)
        else:
            q = self
        for k,v in kwargs.items():
            q = super(SmartCacheQuerySet, q).filter(param_set__name=k,
                                                    param_set__value=to_string(v))
        return q.distinct()

    def _filter_all(self, *args, **kwargs):
        kwargs['only_valid'] = False
        return self.filter(*args, **kwargs)

    def get(self, *args, **kwargs):
        return super(SmartCacheQuerySet, self).get(*args, **kwargs)

    def all(self):
        return super(SmartCacheQuerySet, self).filter(valid=True)


class SmartCacheManager(models.Manager):
    def get_query_set(self):
        return SmartCacheQuerySet(self.model, using=self._db)

    def invalidate(self, *args, **kwargs):
        self._filter_all(*args, **kwargs).update(valid=False)

    def create(self, value, *args, **kwargs):
        if 'type' not in kwargs.keys():
            raise ValidationError('Type parameter must be included '
                                  'to successfully create a cache.')

        pickle = kwargs.pop('pickle', False)
        if pickle:
            value = cPickle.dumps(value)

        caches = SmartCache.objects._filter_all(*args, **kwargs)
        if caches.exists():
            smart_cache = caches[0]
            smart_cache.valid = True
            smart_cache.value = value
            smart_cache.save()
            return

        type_list = SmartCache.type_list()
        cache_type = kwargs['type']

        old_type = True if (cache_type in type_list) else False
        if old_type:
            # New objects of this type must follow the same param format
            type_param_names_set = set(SmartCache.type_param_names(cache_type))
            new_param_names_set = set([k for k in kwargs.keys() if k != 'type'])
            if type_param_names_set != new_param_names_set:
                missing_params = list(type_param_names_set - new_param_names_set)
                if missing_params:
                    raise ValidationError('Cache "%s" objects should have %s '
                        'parameters specified' % (cache_type, missing_params))
                excess_params = list(new_param_names_set - type_param_names_set)
                raise ValidationError('Cache "%s" objects should not have these'
                    ' params specified %s' % (cache_type, excess_params))

        smart_cache = self.model(value=value)
        smart_cache.save()
        for k, v in kwargs.items():
            cache_param = SmartCacheParam(name=k, value=to_string(v),
                                          cache=smart_cache)
            cache_param.save()

    def get(self, *args, **kwargs):
        unpickle = kwargs.pop('unpickle', False)
        cache_object = self.get_query_set().get(*args, **kwargs)
        if unpickle:
            return safe_loads(cache_object.value)
        else:
            return cache_object.value

    def get_many(self, *args, **kwargs):
        unpickle = kwargs.pop('unpickle', False)
        cache_values = self.filter(*args, **kwargs)\
            .values_list('value', flat=True)
        if unpickle:
            loaded_cache_values = [safe_loads(v) for v in cache_values]
            return loaded_cache_values
        else:
            return cache_values

    def all(self):
        return self.get_query_set().all()

    def _filter_all(self, *args, **kwargs):
        return self.get_query_set()._filter_all(*args, **kwargs)


class SmartCache(models.Model):
    value = models.TextField()
    valid = models.BooleanField(default=True)

    objects = SmartCacheManager()
    _objects = models.Manager()

    def __init__(self, *args, **kwargs):
        super(SmartCache, self).__init__(*args, **kwargs)
        # Calling models.Model delete method for instances
        # instead of delete @classmethod
        self.delete = super(SmartCache, self).delete

    @classmethod
    def set(cls, value, *args, **kwargs):
        cls.objects.create(value, *args, **kwargs)

    @classmethod
    def get(cls, *args, **kwargs):
        values = cls.objects.get(*args, **kwargs)
        return values

    @classmethod
    def get_many(cls, *args, **kwargs):
        return cls.objects.get_many(*args, **kwargs)

    @classmethod
    def delete(cls, *args, **kwargs):
        return cls.objects.invalidate(*args, **kwargs)

    @classmethod
    def type_list(cls):
        return SmartCacheParam.objects.filter(name='type').\
            values_list('value', flat=True).distinct()

    @classmethod
    def type_param_names(cls, type):
        if type not in cls.type_list():
            return None

        some_type_cache = cls.objects._filter_all(type=type)[0]
        return some_type_cache.param_names()

    @property
    def unpickled_value(self):
        return safe_loads(self.value)

    def param_names(self):
        return self.param_set.exclude(name='type').values_list('name', flat=True)

    def get_param(self, param_name):
        return self.param_set.get(name=param_name).value

    def __unicode__(self):
        return 'Cache '+ ', '.join(
            ['%s=%s' % (p.name, p.value) for p in self.param_set.all()])


class SmartCacheParam(models.Model):
    name = models.CharField(max_length=500)
    value = models.CharField(max_length=5000)
    cache = models.ForeignKey(SmartCache, related_name='param_set')

    class Meta:
        unique_together = ('name', 'cache')
        index_together = [['name', 'value',], ]

    def __unicode__(self):
        return 'Key Param %s=%s' % (self.name, self.value)