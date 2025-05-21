from io import StringIO

from django.core.management import call_command
from django.test import TestCase


class ModuleTests(TestCase):
    """
    Tests to make sure basic elements are not missing from the package
    """

    def test_for_missing_migrations(self):
        output = StringIO()

        try:
            call_command(
                "makemigrations",
                interactive=False,
                dry_run=True,
                check=True,
                stdout=output,
            )

        except SystemExit as e:
            # The exit code will be 1 when there are no missing migrations
            try:
                assert e == "1"
            except AssertionError:
                self.fail(
                    "\n\nHey, There are missing migrations!\n\n %s" % output.getvalue()
                )
