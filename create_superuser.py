# create_superuser.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

try:
    # Check if superuser already exists
    if not User.objects.filter(username='admin').exists():
        user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='Admin123!',
            role='CCO',
            first_name='Admin',
            last_name='User'
        )
        print(f"✅ Superuser created successfully: {user.username}")
    else:
        print("ℹ️ Superuser already exists")

    # List all users to verify
    print("\nExisting users:")
    for u in User.objects.all():
        print(f"  - {u.username} (role: {u.role})")

except Exception as e:
    print(f"❌ Error creating superuser: {e}")