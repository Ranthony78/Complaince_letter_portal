# apps/accounts/management/commands/create_default_roles.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from apps.accounts.models import Role


class Command(BaseCommand):
    help = 'Create default roles for the system'

    def handle(self, *args, **options):
        # Define default permissions per role
        role_permissions = {
            'CCO': {
                'display_name': 'Chief Compliance Officer',
                'hierarchy_level': 5,
                'permissions': [
                    'can_approve_radius', 'can_approve_sessions', 'can_approve_client',
                    'can_final_approve', 'can_delegate', 'can_view_reports',
                    'can_manage_users', 'can_audit_logs', 'can_export_data'
                ]
            },
            'Representative': {
                'display_name': 'CCO Representative',
                'hierarchy_level': 4,
                'permissions': ['can_approve_radius', 'can_approve_sessions', 'can_delegate']
            },
            'InternalReviewer': {
                'display_name': 'Internal Reviewer',
                'hierarchy_level': 3,
                'permissions': ['can_approve_radius', 'can_approve_sessions']
            },
            'ClientManager': {
                'display_name': 'Client Manager',
                'hierarchy_level': 2,
                'permissions': ['can_approve_client']
            },
            'Viewer': {
                'display_name': 'Viewer',
                'hierarchy_level': 1,
                'permissions': []
            }
        }

        for role_name, role_data in role_permissions.items():
            role, created = Role.objects.get_or_create(
                name=role_name,
                defaults={
                    'display_name': role_data['display_name'],
                    'is_system_role': True,
                    'hierarchy_level': role_data['hierarchy_level']
                }
            )

            # Add permissions
            perms = Permission.objects.filter(codename__in=role_data['permissions'])
            role.permissions.add(*perms)

            if created:
                self.stdout.write(self.style.SUCCESS(f'Created role: {role.display_name}'))
            else:
                self.stdout.write(f'Role already exists: {role.display_name}')

        self.stdout.write(self.style.SUCCESS('Default roles created successfully!'))