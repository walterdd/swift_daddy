from django.db import models

class Domain(models.Model):
    name = models.CharField(max_length=500)
    registrar = models.CharField(max_length=100, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.name