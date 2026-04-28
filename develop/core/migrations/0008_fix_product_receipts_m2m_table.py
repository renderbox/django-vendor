from django.db import migrations


def rename_product_receipts_table(apps, schema_editor):
    old_table = "core_product_reciepts"
    new_table = "core_product_receipts"
    existing_tables = schema_editor.connection.introspection.table_names()

    if old_table in existing_tables and new_table not in existing_tables:
        schema_editor.execute(
            schema_editor.sql_rename_table
            % {
                "old_table": schema_editor.quote_name(old_table),
                "new_table": schema_editor.quote_name(new_table),
            }
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_auto_20201208_1828"),
    ]

    operations = [
        migrations.RunPython(rename_product_receipts_table, migrations.RunPython.noop),
    ]
