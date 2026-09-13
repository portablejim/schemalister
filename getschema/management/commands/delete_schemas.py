from django.core.management.base import BaseCommand
from django.utils import timezone

from getschema.models import Schema
import datetime

class Command(BaseCommand):

    def handle(self, **options):
        
        one_hour_ago = timezone.now() - datetime.timedelta(minutes=60)
        schemas = Schema.objects.filter(finished_date__lt = one_hour_ago)
        schemas.delete()

        one_day_ago = timezone.now() - datetime.timedelta(hours=24)
        schemas = Schema.objects.filter(created_date__lt=one_day_ago)
        schemas.delete()
