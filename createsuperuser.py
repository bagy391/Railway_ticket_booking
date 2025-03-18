# create_superuser.py

import os
from django.contrib.auth import get_user_model

User = get_user_model()

# Check if a superuser already exists
if not User.objects.filter(is_superuser=True).exists():
    username = "admin"
    email = "admin@admin.com"
    password = "password"

    # Create the superuser
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f'Superuser {username} created')
else:
    print('Superuser already exists, skipping creation')
