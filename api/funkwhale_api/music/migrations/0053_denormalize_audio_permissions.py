# -*- coding: utf-8 -*-
"""
This migration is disabled until settings.MUSIC_USE_DENORMALIZATION is set to default=True
"""
from __future__ import unicode_literals

from django.db import migrations
from funkwhale_api.music.utils import guess_mimetype


def denormalize(apps, schema_editor):
    Upload = apps.get_model("music", "Upload")
    if not Upload.objects.count():
        print('Skipping…')

    from funkwhale_api.music.models import TrackActor, Library
    libraries = Library.objects.all()
    objs = []
    total_libraries = len(libraries)
    for i, library in enumerate(libraries):
        print('[{}/{}] Populating permission table for library {}'.format(i+1, total_libraries, library.pk))
        objs += TrackActor.get_objs(
            library=library,
            actor_ids=[],
            upload_and_track_ids=[],
        )
    print('Commiting changes…')
    TrackActor.objects.bulk_create(objs, batch_size=5000, ignore_conflicts=True)



def rewind(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [("music", "0052_auto_20200505_0810")]

    operations = [migrations.RunPython(denormalize, rewind)]
