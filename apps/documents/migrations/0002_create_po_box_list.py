# apps/documents/migrations/0002_create_po_box_list.py
from django.db import migrations
import json


def create_po_box_list(apps, schema_editor):
    Document = apps.get_model('documents', 'Document')

    po_box_data = {
        "columns": ["PO Box", "Company Name", "Address", "City", "State", "ZIP Code"],
        "rows": [
            ["PO BOX 390915", "RADIUS GLOBAL SOLUTIONS LLC", "PO BOX 390915", "Minneapolis", "MN", "55439-0905"],
            ["PO BOX 390905", "RADIUS GLOBAL SOLUTIONS LLC", "PO BOX 390905", "Minneapolis", "MN", "55439-0905"],
            ["PO BOX 390916", "RADIUS GLOBAL SOLUTIONS LLC", "PO BOX 390916", "Minneapolis", "MN", "55439-0916"],
            ["PO BOX 390912", "RADIUS GLOBAL SOLUTIONS LLC", "PO BOX 390912", "Minneapolis", "MN", "55439-0912"],
            ["PO BOX 390914", "RADIUS GLOBAL SOLUTIONS LLC", "PO BOX 390914", "Minneapolis", "MN", "55439-0914"],
            ["PO BOX 15118", "RADIUS GLOBAL SOLUTIONS LLC", "PO BOX 15118", "Jacksonville", "FL", "32239-5118"],
            ["PO BOX 390913", "RADIUS GLOBAL SOLUTIONS LLC", "PO BOX 390913", "Minneapolis", "MN", "55439-0913"],
            ["PO BOX 357", "RADIUS GLOBAL SOLUTIONS LLC", "PO BOX 357", "Ramsey", "NJ", "07446-0357"],
            ["PO BOX 390846", "RADIUS GLOBAL SOLUTIONS LLC", "PO BOX 390846", "Minneapolis", "MN", "55439-0846"],
            ["PO BOX 358", "RADIUS GLOBAL SOLUTIONS LLC", "PO BOX 358", "Ramsey", "NJ", "07446-0358"],
        ]
    }

    Document.objects.create(
        title="PO Box List",
        description="Complete list of RADIUS GLOBAL SOLUTIONS LLC PO Boxes for mail processing",
        document_type="po_box",
        is_active=True,
        is_public=True,
        table_data=po_box_data,
        version="1.0"
    )


def reverse_migration(apps, schema_editor):
    Document = apps.get_model('documents', 'Document')
    Document.objects.filter(document_type="po_box", title="PO Box List").delete()


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_po_box_list, reverse_migration),
    ]