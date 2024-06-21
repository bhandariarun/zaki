from django.db import models

class Log(models.Model):
    logGroupName = models.CharField(max_length=100)
    logStreamName = models.CharField(max_length=100)
    owner = models.IntegerField()
    timestamp = models.DateTimeField()
    message = models.TextField()
    ingestionTime = models.BigIntegerField()

def __str__(self):
    return f"Log {self.id} - {self.logGroupName} - {self.logStreamName} - {self.message}"


class LogCount(models.Model):
    log = models.OneToOneField(Log, on_delete=models.CASCADE, related_name='log_count')
    info_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    warn_count = models.IntegerField(default=0)
