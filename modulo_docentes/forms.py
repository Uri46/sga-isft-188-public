"""Formularios del módulo de docentes."""
import re
import datetime
from typing import Any, Optional
from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError

from core.formularios import PersonaBaseForm, INPUT_CLASS, SELECT_CLASS
from modulo_base_datos.models import Persona, Docente


NACIONALIDAD_CHOICES = [
    ('Argentina', 'Argentina'),
    ('Boliviana', 'Boliviana'),
    ('Brasileña', 'Brasileña'),
    ('Chilena', 'Chilena'),
    ('Colombiana', 'Colombiana'),
    ('Ecuatoriana', 'Ecuatoriana'),
    ('Española', 'Española'),
    ('Italiana', 'Italiana'),
    ('Paraguaya', 'Paraguaya'),
    ('Peruana', 'Peruana'),
    ('Uruguaya', 'Uruguaya'),
    ('Venezolana', 'Venezolana'),
    ('Otra', 'Otra'),
]

LOCALIDAD_CHOICES = [
    ('General Rodríguez', 'General Rodríguez'),
    ('Moreno', 'Moreno'),
    ('Luján', 'Luján'),
    ('Pilar', 'Pilar'),
    ('Mercedes', 'Mercedes'),
    ('San Miguel', 'San Miguel'),
    ('Marcos Paz', 'Marcos Paz'),
    ('Merlo', 'Merlo'),
    ('Morón', 'Morón'),
    ('Ituzaingó', 'Ituzaingó'),
    ('Hurlingham', 'Hurlingham'),
    ('José C. Paz', 'José C. Paz'),
    ('Malvinas Argentinas', 'Malvinas Argentinas'),
    ('Jáuregui', 'Jáuregui'),
    ('Navarro', 'Navarro'),
    ('CABA', 'CABA (Ciudad Autónoma de Buenos Aires)'),
    ('Otra Localidad', 'Otra Localidad'),
]


class DocenteForm(PersonaBaseForm):
    """
    Formulario unificado para Alta y Edición de Docentes.
    Reutiliza la base de Persona y gestiona 'titulo_mn', 'nacionalidad' y 'localidad'.
    """
    nacionalidad = forms.ChoiceField(
        choices=[('', '-- Seleccionar Nacionalidad --')] + NACIONALIDAD_CHOICES,
        widget=forms.Select(attrs={
            'id': 'id_nacionalidad',
            'class': SELECT_CLASS,
            'onchange': 'alternarOtraNacionalidad(this.value)',
        }),
        label='Nacionalidad',
        required=False,
    )
    nacionalidad_otra = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={
            'id': 'id_nacionalidad_otra',
            'class': INPUT_CLASS,
            'placeholder': 'Escribí la nacionalidad...',
            'list': 'lista-nacionalidades-mundo',
            'autocomplete': 'off',
        })
    )
    localidad = forms.ChoiceField(
        choices=[('', '-- Seleccionar Localidad --')] + LOCALIDAD_CHOICES,
        widget=forms.Select(attrs={
            'id': 'id_localidad',
            'class': SELECT_CLASS,
        }),
        label='Localidad',
        required=False,
    )
    titulo_mn = forms.CharField(
        max_length=150,
        required=False,
        label="Título / Matrícula Nacional",
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej. Prof. en Informática / MN 12345'})
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            try:
                docente_profile = getattr(self.instance, 'docente_profile', None)
                if docente_profile and docente_profile.titulo_mn:
                    self.fields['titulo_mn'].initial = docente_profile.titulo_mn
            except Exception:
                pass

        if self.is_bound and 'nacionalidad' in self.fields:
            post_nac = self.data.get('nacionalidad')
            if post_nac and post_nac not in [opt[0] for opt in self.fields['nacionalidad'].choices]:
                self.fields['nacionalidad'].choices = list(self.fields['nacionalidad'].choices) + [(post_nac, post_nac)]

        val_nac = self.initial.get('nacionalidad')
        if val_nac and 'nacionalidad' in self.fields:
            opciones_nombres = [opt[0] for opt in NACIONALIDAD_CHOICES]
            if val_nac not in opciones_nombres:
                self.fields['nacionalidad'].choices = list(self.fields['nacionalidad'].choices) + [(val_nac, val_nac)]
                self.initial['nacionalidad'] = 'Otra'
                self.initial['nacionalidad_otra'] = val_nac

        if self.is_bound and 'localidad' in self.fields:
            post_loc = self.data.get('localidad')
            if post_loc and post_loc not in [opt[0] for opt in self.fields['localidad'].choices]:
                self.fields['localidad'].choices = list(self.fields['localidad'].choices) + [(post_loc, post_loc)]

        val_loc = self.initial.get('localidad')
        if val_loc and 'localidad' in self.fields:
            opciones_loc = [opt[0] for opt in LOCALIDAD_CHOICES]
            if val_loc not in opciones_loc:
                self.fields['localidad'].choices = list(self.fields['localidad'].choices) + [(val_loc, val_loc)]

    def clean_nacionalidad(self) -> str:
        nac = str(self.cleaned_data.get('nacionalidad', '')).strip()
        if nac == 'Otra':
            otra = str(self.data.get('nacionalidad_otra', '')).strip()
            return otra.title() if otra else ''
        return nac

    def save(self, commit: bool = True) -> Persona:
        persona = super().save(commit=commit)
        titulo_val = self.cleaned_data.get('titulo_mn', '').strip()
        if commit:
            Docente.objects.update_or_create(
                persona=persona,
                defaults={'titulo_mn': titulo_val or None}
            )
        return persona
