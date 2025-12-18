from django.test import TestCase

from autoslug.models import (
    ModelWithAutoUpdateEnabled,
    ModelWithBooleanInUniqueWith,
    ModelWithUniqueSlug,
    ModelWithUniqueSlugFK,
    SimpleModel,
)


class AutoSlugFieldBehaviourTests(TestCase):
    def test_unique_with_foreign_key(self):
        base = SimpleModel.objects.create(name="owner")
        first = ModelWithUniqueSlugFK.objects.create(name="hello world", simple_model=base)
        second = ModelWithUniqueSlugFK.objects.create(name="hello world", simple_model=base)
        other_owner = SimpleModel.objects.create(name="other")
        third = ModelWithUniqueSlugFK.objects.create(name="hello world", simple_model=other_owner)

        self.assertEqual(first.slug, "hello-world")
        self.assertEqual(second.slug, "hello-world-2")
        self.assertEqual(third.slug, "hello-world")

    def test_always_updates_slug_on_save(self):
        obj = ModelWithAutoUpdateEnabled.objects.create(name="Alpha")
        self.assertEqual(obj.slug, "alpha")

        obj.name = "Beta Release"
        obj.save()
        self.assertEqual(obj.slug, "beta-release")

    def test_boolean_unique_with(self):
        true_obj = ModelWithBooleanInUniqueWith.objects.create(name="flag", bool=True)
        false_obj = ModelWithBooleanInUniqueWith.objects.create(name="flag", bool=False)
        another_true = ModelWithBooleanInUniqueWith.objects.create(name="flag", bool=True)

        self.assertEqual(true_obj.slug, "flag")
        self.assertEqual(false_obj.slug, "flag")
        self.assertEqual(another_true.slug, "flag-2")

    def test_unique_slug_increments(self):
        first = ModelWithUniqueSlug.objects.create(name="hello world")
        second = ModelWithUniqueSlug.objects.create(name="hello world")

        self.assertEqual(first.slug, "hello-world")
        self.assertEqual(second.slug, "hello-world-2")
