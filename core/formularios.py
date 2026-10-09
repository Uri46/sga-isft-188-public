"""Formularios base reutilizables entre módulos (datos de Persona)."""
import re
import datetime
from typing import Any, Optional
from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError

from modulo_base_datos.models import Persona
from core.validaciones import validar_cuil_detallado


INPUT_CLASS = (
    "w-full px-4 py-3 rounded-2xl text-sm font-medium border theme-border "
    "transition-all shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
)
SELECT_CLASS = (
    "w-full px-4 py-3 rounded-2xl text-sm font-medium border theme-border "
    "transition-all shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 cursor-pointer"
)


class PersonaBaseForm(forms.ModelForm):
    """
    Formulario base modular para datos personales (Persona).
    Compartido y reutilizado entre Alumnos y Docentes.
    """

    class Meta:
        model = Persona
        fields = [
            'dni',
            'cuil',
            'nombre',
            'apellido',
            'fecha_nacimiento',
            'identidad',
            'nacionalidad',
            'localidad',
            'domicilio',
            'telefono',
            'mail',
        ]
        widgets = {
            'dni': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej. 12345678', 'autocomplete': 'off'}),
            'cuil': forms.TextInput(attrs={'class': INPUT_CLASS + ' font-mono', 'placeholder': 'Ej. 20-12345678-6', 'autocomplete': 'off'}),
            'nombre': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Nombres'}),
            'apellido': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Apellidos'}),
            'fecha_nacimiento': forms.DateInput(attrs={'class': INPUT_CLASS, 'type': 'date'}),
            'identidad': forms.Select(attrs={'class': SELECT_CLASS}),
            'nacionalidad': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej. Argentina'}),
            'localidad': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej. General Rodríguez'}),
            'domicilio': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Calle, número, piso/depto'}),
            'telefono': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej. +54 9 11 1234-5678'}),
            'mail': forms.EmailInput(attrs={'class': INPUT_CLASS, 'placeholder': 'correo@ejemplo.com'}),
        }

    def clean_dni(self) -> str:
        dni_raw = str(self.cleaned_data.get('dni', '')).strip()
        if not dni_raw:
            raise ValidationError("El DNI es obligatorio.")

        dni_limpio = re.sub(r'[^\d]', '', dni_raw)
        if len(dni_limpio) < 6 or len(dni_limpio) > 9:
            raise ValidationError("El DNI debe tener entre 6 y 9 dígitos numéricos.")

        qs = Persona.objects.filter(dni=dni_limpio)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f"Ya existe una persona registrada en el sistema con este DNI ({dni_limpio}).")

        return dni_limpio

    def clean_cuil(self) -> str:
        cuil_raw = str(self.cleaned_data.get('cuil', '')).strip()
        dni_val = self.cleaned_data.get('dni', '')

        cuil_formateado, error_msg = validar_cuil_detallado(cuil_raw, dni_val=dni_val)
        if error_msg:
            raise ValidationError(error_msg)

        cuil_limpio = re.sub(r'[^\d]', '', cuil_formateado)
        qs = Persona.objects.filter(cuil__in=[cuil_formateado, cuil_limpio])
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f"Ya existe una persona registrada en el sistema con este CUIL ({cuil_formateado}).")

        return cuil_formateado

    def clean_nombre(self) -> str:
        nombre = str(self.cleaned_data.get('nombre', '')).strip()
        if not nombre or len(nombre) < 2:
            raise ValidationError("Ingresá el nombre completo.")
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s'\-]+$", nombre):
            raise ValidationError("Ingresá solo letras en el nombre.")
        return nombre.title()

    def clean_apellido(self) -> str:
        apellido = str(self.cleaned_data.get('apellido', '')).strip()
        if not apellido or len(apellido) < 2:
            raise ValidationError("Ingresá el apellido completo.")
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s'\-]+$", apellido):
            raise ValidationError("Ingresá solo letras en el apellido.")
        return apellido.title()

    def clean_fecha_nacimiento(self) -> Optional[datetime.date]:
        fecha = self.cleaned_data.get('fecha_nacimiento')
        if not fecha:
            return None
        hoy = datetime.date.today()
        edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
        if edad < 15:
            raise ValidationError("La edad mínima para registrarse es de 15 años.")
        if edad > 110:
            raise ValidationError("La fecha de nacimiento ingresada no parece válida.")
        return fecha

