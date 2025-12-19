import pytest


@pytest.fixture(autouse=True)
def add_test_apps(settings):
    extra_apps = ["siteconfigs", "stripe"]
    settings.INSTALLED_APPS += [
        app for app in extra_apps if app not in settings.INSTALLED_APPS
    ]
