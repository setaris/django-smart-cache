django-smart-cache
==================

Key cache based on any number of parameters so that it can be used and invalidated intelligently based on requests.


SmartCache model has an interface, similar to what is used in regular cache:

```
from smartcache.models import SmartCache
```

Although it stores objects in the database, and is not as fast as real cache, it provides a lot more control for invalidating cache.

As there are typically lots of different object stored in cache, SmartCache uses a special type parameter to group
together objects of same structure.

You can define new type of cache objects just by trying to save a new object

```
SmartCache.set('1.38', type='exchange_rate', cur1='EUR', cur2='USD')
```

This line also creates 'exchange_rate' type, and objects of this type are defined by 2 parameters: cur1 and cur2.
Objects of each type should have similar parameters, and attempt to save object without required parameters will lead to error:

```
# raises ValidationError, because cur2 is not specified
SmartCache.set('0.15', type='exchange_rate', cur1='SEK')

# raises ValidationError, because date is not used for all 'exchange_rate' objects.
SmartCache.set('0.15', type='exchange_rate', cur1='SEK', cur2='USD', date='2013-12-18')
```

The main advantages of SmartCache is ability to perform invalidation and filtering, depending on selected parameters.
All of the following lines are valid:

```
SmartCache.delete(type='exchange_rate', cur1='SEK')

SmartCache.get_many(type='exchange_rate', cur1='USD')

SmartCache.get(type='quarter_earnings', company='Google', year='2013', quarter='3')

SmartCache.objects.filter(type='quarter_earnings', year='2013')

```





