# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='address',
            old_name='os_delete',
            new_name='is_delete',
        ),
        migrations.RemoveField(
            model_name='user',
            name='os_delete',
        ),
        migrations.AddField(
            model_name='user',
            name='is_delete',
            field=models.BooleanField(verbose_name='删除标记', default=False),
        ),
    ]
