from django.db import models


class RICCode(models.Model):
	code = models.CharField(max_length=100)


class Daily(models.Model):
	ric_code = models.ForeignKey(RICCode, on_delete=models.CASCADE)
	datetime = models.DateTimeField()
	value = models.CharField(max_length=20)


class Realtime(models.Model):
	ric_code = models.ForeignKey(RICCode, on_delete=models.CASCADE)
	datetime = models.DateTimeField(null=True, blank=True)
	value = models.CharField(max_length=20, null=True, blank=True)
