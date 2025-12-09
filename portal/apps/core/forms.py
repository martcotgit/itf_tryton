from django import forms

class ContactForm(forms.Form):
    name = forms.CharField(
        label="Nom complet",
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "ex: Jean Tremblay"
        }),
        required=True
    )
    email = forms.EmailField(
        label="Courriel",
        widget=forms.EmailInput(attrs={
            "class": "form-input",
            "placeholder": "ex: jean@entreprise.ca"
        }),
        required=True
    )
    subject = forms.CharField(
        label="Objet",
        max_length=200,
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "ex: Demande de devis pour 50 palettes"
        }),
        required=True
    )
    message = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={
            "class": "form-textarea",
            "rows": 5,
            "placeholder": "Comment pouvons-nous vous aider ?"
        }),
        required=True
    )
