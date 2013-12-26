from django.db import models


def to_string(obj):
    if isinstance(obj, basestring):
        return obj
    if isinstance(obj, models.Model):
        # django model instance
        return '%s.%s.%s' % (obj.__class__, obj.pk, obj)
    if isinstance(obj, (list, tuple)):
        string_list = [to_string(o) for o in obj]
        if isinstance(obj, tuple):
            string_list = tuple(string_list)
        return str(string_list)
    return str(obj)

