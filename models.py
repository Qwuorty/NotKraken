from django.db import models


class User(models.Model):
    mail = models.CharField(max_length=200)
    password = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.mail


class Photo(models.Model):
    image = models.URLField()

# Create your models here.
