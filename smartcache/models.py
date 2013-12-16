from django.db import models
from django.core.exceptions import ValidationError


class SmartCacheQuerySet(models.query.QuerySet):
    def filter(self, *args, **kwargs):
        kwargs.pop('valid', '')
        only_valid = kwargs.pop('only_valid', True)
        mod_kwargs = {}
        for k,v in kwargs.items():
            mod_kwargs['param_set__name'] = k
            mod_kwargs['param_set__value'] = v
        if only_valid:
            mod_kwargs['valid'] = True

        return super(SmartCacheQuerySet, self).\
            filter(*args, **mod_kwargs).distinct()

    def _filter_all(self, *args, **kwargs):
        kwargs['only_valid'] = False
        return self.filter(*args, **kwargs)

    def get(self, *args, **kwargs):
        return super(SmartCacheQuerySet, self).get(*args, **kwargs)


class SmartCacheManager(models.Manager):
    def get_query_set(self):
        return SmartCacheQuerySet(self.model, using=self._db)

    def invalidate(self, *args, **kwargs):
        self._filter_all(*args, **kwargs).update(valid=False)

    def create(self, value, *args, **kwargs):
        if 'type' not in kwargs.keys():
            raise ValidationError('Type parameter must be included '
                                  'to successfully create a cache.')
        smart_cache = self.model(value=value)
        smart_cache.save()
        for k, v in kwargs.items():
            cache_param = SmartCacheParam(name=k, value=v, cache=smart_cache)
            cache_param.save()

    def get(self, *args, **kwargs):
        return self.get_query_set().get(*args, **kwargs).value

    def get_many(self, *args, **kwargs):
        return self.filter(*args, **kwargs).values_list('value', flat=True)

    def _filter_all(self, *args, **kwargs):
        return self.get_query_set()._filter_all(*args, **kwargs)


class SmartCache(models.Model):
    value = models.TextField()
    valid = models.BooleanField(default=True)

    objects = SmartCacheManager()
    _objects = models.Manager()

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

    def param_names(self):
        return self.param_set.exclude(name='type').values_list('name', flat=True)

    def __unicode__(self):
        return 'Cache '+ ', '.join(
            ['%s=%s' % (p.name, p.value) for p in self.param_set.all()])


class SmartCacheParam(models.Model):
    name = models.CharField(max_length=500)
    value = models.CharField(max_length=500)
    cache = models.ForeignKey(SmartCache, related_name='param_set')

    class Meta:
        unique_together = ('name', 'cache')
        index_together = [['name', 'value',], ]

    def __unicode__(self):
        return 'Key Param %s=%s' % (self.name, self.value)