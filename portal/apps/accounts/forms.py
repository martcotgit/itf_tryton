from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .services import (
    PortalAccountCreationResult,
    PortalAccountService,
    PortalAccountServiceError,
)


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Identifiant",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Identifiant Tryton",
                "autocomplete": "username",
                "class": "form-input",
            }
        ),
    )
    password = forms.CharField(
        label="Mot de passe",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Mot de passe",
                "autocomplete": "current-password",
                "class": "form-input",
            }
        ),
    )


class ClientSignupForm(forms.Form):
    company_name = forms.CharField(
        label="Entreprise",
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Nom de votre entreprise",
                "class": "form-input",
                "autocapitalize": "words",
            }
        ),
    )
    first_name = forms.CharField(
        label="Prénom",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Prénom du contact principal",
                "class": "form-input",
                "autocapitalize": "words",
            }
        ),
    )
    last_name = forms.CharField(
        label="Nom",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Nom du contact principal",
                "class": "form-input",
                "autocapitalize": "words",
            }
        ),
    )
    email = forms.EmailField(
        label="Adresse courriel",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "prenom.nom@entreprise.ca",
                "class": "form-input",
                "autocomplete": "email",
            }
        ),
    )
    phone = forms.CharField(
        label="Téléphone",
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Numéro de téléphone du contact (facultatif)",
                "class": "form-input",
                "autocomplete": "tel",
            }
        ),
    )
    password1 = forms.CharField(
        label="Mot de passe",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Choisissez un mot de passe sécuritaire",
                "class": "form-input",
                "autocomplete": "new-password",
            }
        ),
        help_text="8 caractères minimum avec au moins trois catégories : minuscules, majuscules, chiffres ou symboles.",
    )
    password2 = forms.CharField(
        label="Confirmation du mot de passe",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Confirmez le mot de passe",
                "class": "form-input",
                "autocomplete": "new-password",
            }
        ),
        help_text="Les deux mots de passe doivent être identiques.",
    )
    accept_terms = forms.BooleanField(
        label="J’accepte les conditions d’utilisation et la politique de confidentialité",
        error_messages={"required": "Vous devez accepter les conditions d’utilisation pour créer un compte."},
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )

    def __init__(self, *args, account_service: PortalAccountService | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.account_service = account_service or PortalAccountService()

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        try:
            if self.account_service.login_exists(email):
                raise forms.ValidationError("Un compte existe déjà pour cette adresse courriel.")
        except PortalAccountServiceError as exc:
            raise forms.ValidationError(str(exc))
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Les mots de passe ne correspondent pas.")

        if password1:
            try:
                validate_password(password1)
            except ValidationError as exc:
                self.add_error("password1", exc)

        for field_name in ("company_name", "first_name", "last_name", "phone"):
            value = cleaned_data.get(field_name)
            if isinstance(value, str):
                cleaned_data[field_name] = value.strip()

        return cleaned_data

    def save(self) -> PortalAccountCreationResult:
        if not self.is_valid():
            raise ValueError("Cannot save an invalid form.")

        cleaned = self.cleaned_data
        try:
            return self.account_service.create_client_account(
                company_name=cleaned.get("company_name"),
                first_name=cleaned["first_name"],
                last_name=cleaned["last_name"],
                email=cleaned["email"],
                phone=cleaned.get("phone"),
                password=cleaned["password1"],
            )
        except PortalAccountServiceError:
            # Propagate the error so the view can surface it as a non-field error.
            raise


class ClientProfileForm(forms.Form):
    company_name = forms.CharField(
        label="Entreprise",
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Nom de votre organisation",
                "class": "form-input",
            }
        ),
    )
    first_name = forms.CharField(
        label="Prénom",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Prénom",
                "class": "form-input",
                "autocapitalize": "words",
            }
        ),
    )
    last_name = forms.CharField(
        label="Nom",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Nom",
                "class": "form-input",
                "autocapitalize": "words",
            }
        ),
    )
    email = forms.EmailField(
        label="Courriel (identifiant)",
        required=False,
        disabled=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-input",
                "readonly": "readonly",
            }
        ),
    )
    phone = forms.CharField(
        label="Téléphone",
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Ex.: 418 555-1234",
                "class": "form-input",
                "autocomplete": "tel",
            }
        ),
    )
    address = forms.CharField(
        label="Adresse",
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "No civique et rue",
                "class": "form-input",
            }
        ),
    )
    city = forms.CharField(
        label="Ville",
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Ville",
                "class": "form-input",
            }
        ),
    )
    postal_code = forms.CharField(
        label="Code postal",
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "A1A 1A1",
                "class": "form-input",
                "autocomplete": "postal-code",
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        for field in (
            "company_name",
            "first_name",
            "last_name",
            "phone",
            "address",
            "city",
            "postal_code",
        ):
            value = cleaned_data.get(field)
            if isinstance(value, str):
                cleaned_data[field] = value.strip()
        return cleaned_data


class ClientPasswordForm(forms.Form):
    current_password = forms.CharField(
        label="Mot de passe actuel",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Mot de passe actuel",
                "class": "form-input",
                "autocomplete": "current-password",
            }
        ),
    )
    new_password1 = forms.CharField(
        label="Nouveau mot de passe",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Nouveau mot de passe",
                "class": "form-input",
                "autocomplete": "new-password",
            }
        ),
        help_text="8 caractères minimum avec complexité renforcée.",
    )
    new_password2 = forms.CharField(
        label="Confirmation",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Confirmez le nouveau mot de passe",
                "class": "form-input",
                "autocomplete": "new-password",
            }
        ),
    )

    def __init__(
        self,
        *args,
        account_service: PortalAccountService | None = None,
        login: str | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.account_service = account_service or PortalAccountService()
        self.login = (login or "").strip()

    def clean_current_password(self):
        current_password = self.cleaned_data.get("current_password") or ""
        if not self.login:
            raise forms.ValidationError("Authentification invalide. Veuillez réessayer.")
        try:
            is_valid = self.account_service.validate_credentials(login=self.login, password=current_password)
        except PortalAccountServiceError as exc:
            raise forms.ValidationError(str(exc))
        if not is_valid:
            raise forms.ValidationError("Le mot de passe actuel est incorrect.")
        return current_password

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("new_password1")
        password2 = cleaned_data.get("new_password2")
        if password1 and password2 and password1 != password2:
            self.add_error("new_password2", "Les mots de passe ne correspondent pas.")
        if password1:
            try:
                validate_password(password1)
            except ValidationError as exc:
                self.add_error("new_password1", exc)
        return cleaned_data

    def save(self) -> None:
        if not self.is_valid():
            raise ValueError("Impossible de sauvegarder un formulaire invalide.")
        try:
            self.account_service.change_password(
                login=self.login,
                current_password=self.cleaned_data["current_password"],
                new_password=self.cleaned_data["new_password1"],
            )
        except PortalAccountServiceError:
            raise
