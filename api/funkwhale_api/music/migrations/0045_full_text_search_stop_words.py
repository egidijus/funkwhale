# Generated by Django 2.2.7 on 2019-12-16 15:06

import django.contrib.postgres.search
import django.contrib.postgres.indexes
from django.db import migrations, models
import django.db.models.deletion
from django.db import connection

FIELDS = {
    "music.Artist": {
        "fields": [
            'name',
        ],
        "trigger_name": "music_artist_update_body_text"
    },
    "music.Track": {
        "fields": ['title', 'copyright'],
        "trigger_name": "music_track_update_body_text"
    },
    "music.Album": {
        "fields": ['title'],
        "trigger_name": "music_album_update_body_text"
    },
}

def populate_body_text(apps, schema_editor):
    for label, search_config in FIELDS.items():
        model = apps.get_model(*label.split('.'))
        print('Updating search index for {}…'.format(model.__name__))
        vector = django.contrib.postgres.search.SearchVector(*search_config['fields'], config="public.english_nostop")
        model.objects.update(body_text=vector)

def rewind(apps, schema_editor):
    pass

def setup_dictionary(apps, schema_editor):
    cursor = connection.cursor()
    statements = [
        """
        CREATE TEXT SEARCH DICTIONARY english_stem_nostop (
            Template = snowball
            , Language = english
        );
        """,
        "CREATE TEXT SEARCH CONFIGURATION public.english_nostop ( COPY = pg_catalog.english );",
        "ALTER TEXT SEARCH CONFIGURATION public.english_nostop ALTER MAPPING FOR asciiword, asciihword, hword_asciipart, hword, hword_part, word WITH english_stem_nostop;",
    ]
    print('Create non stopword dictionary and search configuration…')
    for statement in statements:
        cursor.execute(statement)

    for label, search_config in FIELDS.items():
        model = apps.get_model(*label.split('.'))
        table = model._meta.db_table
        print('Dropping database trigger {} on {}…'.format(search_config['trigger_name'], table))
        sql = """
            DROP TRIGGER IF EXISTS {trigger_name} ON {table}
        """.format(
            trigger_name=search_config['trigger_name'],
            table=table,
        )

        cursor.execute(sql)
        print('Creating database trigger {} on {}…'.format(search_config['trigger_name'], table))
        sql = """
            CREATE TRIGGER {trigger_name}
                BEFORE INSERT OR UPDATE
                ON {table}
                FOR EACH ROW
                EXECUTE PROCEDURE
                    tsvector_update_trigger(body_text, 'public.english_nostop', {fields})
        """.format(
            trigger_name=search_config['trigger_name'],
            table=table,
            fields=', '.join(search_config['fields']),
        )
        cursor.execute(sql)

def rewind_dictionary(apps, schema_editor):
    cursor = connection.cursor()
    for label, search_config in FIELDS.items():
        model = apps.get_model(*label.split('.'))
        table = model._meta.db_table

class Migration(migrations.Migration):

    dependencies = [
        ('music', '0044_full_text_search'),
    ]

    operations = [
        migrations.RunPython(setup_dictionary, rewind_dictionary),
        migrations.RunPython(populate_body_text, rewind),
    ]