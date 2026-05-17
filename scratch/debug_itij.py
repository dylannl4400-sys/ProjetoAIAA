import os
import django
import sys

# Setup Django environment
sys.path.append(r'c:\Users\dylan\PROJETO26\reunioes\semana1')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aiaa.settings') # Change this if needed
# Need to find the actual settings module name. 
# Let's check the project root for manage.py or settings.py location.
