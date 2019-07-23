import uuid 
from django.db import models


# class SampleModel(models.Model):
#     name = models.CharField(_("Name"), max_length=120, blank=False)
#     uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

#     class Meta:
#         verbose_name = _( "Sample Model")
#         verbose_name_plural = _( "Sample Models")

#     def __str__(self):
#         return self.name

#     def get_absolute_url(self):
#         return reverse( "samplemodel_detail", kwargs={"uuid": self.uuid})
