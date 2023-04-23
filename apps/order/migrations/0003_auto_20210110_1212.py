# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0002_auto_20210110_1151'),
    ]

    operations = [
        migrations.RenameField(
            model_name='ordergoods',
            old_name='os_delete',
            new_name='is_delete',
        ),
        migrations.RenameField(
            model_name='orderinfo',
            old_name='os_delete',
            new_name='is_delete',
        ),
    ]
