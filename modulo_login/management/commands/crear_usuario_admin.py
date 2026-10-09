import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Configura el usuario administrador para el entorno local o de demostración desde variables de entorno.'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default=None, help='Nombre de usuario del administrador')
        parser.add_argument('--password', type=str, default=None, help='Contraseña del administrador')

    def handle(self, *args, **options):
        User = get_user_model()
        admin_user = options.get('username') or os.environ.get('ADMIN_USERNAME', 'admin')
        admin_pass = options.get('password') or os.environ.get('ADMIN_PASSWORD', 'admin1234')
        
        user, created = User.objects.get_or_create(username=admin_user)
        user.set_password(admin_pass)
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.save()
        
        if created:
            self.stdout.write(self.style.SUCCESS(f"Usuario '{admin_user}' creado exitosamente."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Usuario '{admin_user}' actualizado exitosamente."))

