from django.db import models


class Domain(models.Model):
    name = models.CharField(max_length=500)
    zone = models.CharField(max_length=10, null=True)
    length = models.IntegerField(null=True)
    registrar = models.CharField(max_length=100, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.name


class Meta(models.Model):
    n_domains = models.IntegerField()
