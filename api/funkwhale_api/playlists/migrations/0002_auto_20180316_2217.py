# Generated by Django 2.0.3 on 2018-03-16 22:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("playlists", "0001_initial")]

    operations = [
        migrations.RemoveField(model_name="playlist", name="is_public"),
        migrations.AddField(
            model_name="playlist",
            name="privacy_level",
            field=models.CharField(
                choices=[
                    ("me", "Only me"),
                    ("followers", "Me and my followers"),
                    ("instance", "Everyone on my instance, and my followers"),
                    ("everyone", "Everyone, including people on other instances"),
                ],
                default="instance",
                max_length=30,
            ),
        ),
    ]
