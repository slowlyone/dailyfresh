# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='goods',
            old_name='os_delete',
            new_name='is_delete',
        ),
        migrations.RenameField(
            model_name='goodsimage',
            old_name='os_delete',
            new_name='is_delete',
        ),
        migrations.RenameField(
            model_name='goodssku',
            old_name='os_delete',
            new_name='is_delete',
        ),
        migrations.RenameField(
            model_name='goodstype',
            old_name='os_delete',
            new_name='is_delete',
        ),
        migrations.RenameField(
            model_name='indexgoodsbanner',
            old_name='os_delete',
            new_name='is_delete',
        ),
        migrations.RenameField(
            model_name='indexpromotionbanner',
            old_name='os_delete',
            new_name='is_delete',
        ),
        migrations.RenameField(
            model_name='indextypegoodsbanner',
            old_name='os_delete',
            new_name='is_delete',
        ),
    ]
