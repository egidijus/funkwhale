# Generated by Django 2.2.10 on 2020-02-06 15:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audio', '0002_channel_metadata'),
    ]

    operations = [
        migrations.AddField(
            model_name='channel',
            name='rss_url',
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
    ]
