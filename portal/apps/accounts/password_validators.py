from __future__ import annotations

import string

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


SYMBOL_CHARACTERS = set(string.punctuation)


@deconstructible
class ComplexitePortailValidator:
    """Valide qu'un mot de passe contient un minimum de classes de caractères."""

    message = (
        "Le mot de passe doit inclure au moins trois des catégories suivantes : "
        "lettres minuscules, lettres majuscules, chiffres, symboles."
    )
    code = "password_complexity"

    def __init__(self, required_categories: int = 3):
        self.required_categories = required_categories

    def __call__(self, value: str) -> None:
        if value is None:
            return

        category_count = sum(
            (
                any(ch.islower() for ch in value),
                any(ch.isupper() for ch in value),
                any(ch.isdigit() for ch in value),
                any(ch in SYMBOL_CHARACTERS for ch in value),
            )
        )

        if category_count < self.required_categories:
            raise ValidationError(self.message, code=self.code)

    def validate(self, password: str, user=None) -> None:
        self.__call__(password)

    def get_help_text(self) -> str:
        return (
            "Utilisez au moins trois catégories (minuscules, majuscules, chiffres, symboles) "
            "pour sécuriser votre mot de passe."
        )
