from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class NRRDImage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    image = models.FileField(upload_to='nrrd_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name