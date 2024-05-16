# Generated by Django 5.0.4 on 2024-05-08 18:08

import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('local_swap_space_app', '0005_user_latitude_user_longitude'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='location',
            field=django.contrib.gis.db.models.fields.PointField(blank=True, geography=True, null=True, srid=4326, verbose_name='Lokalizacja'),
        ),
    ]