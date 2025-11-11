from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from .forms import (
    ClientPasswordForm,
    ClientProfileForm,
    ClientSignupForm,
    EmailAuthenticationForm,
)
from .services import (
    PortalAccountService,
    PortalAccountServiceError,
    PortalClientProfile,
)


class ClientLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True
    extra_context = {
        "page_title": "Espace client",
        "signup_url_name": "accounts:signup",
    }

    def form_valid(self, form):
        response = super().form_valid(form)
        session_payload = getattr(form.get_user(), "_tryton_session", None)
        if session_payload:
            self.request.session["tryton_session"] = session_payload
        return response


class ClientLogoutView(LogoutView):
    next_page = reverse_lazy("core:home")

    def dispatch(self, request, *args, **kwargs):
        request.session.pop("tryton_session", None)
        return super().dispatch(request, *args, **kwargs)


class ClientDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/dashboard.html"
    login_url = reverse_lazy("accounts:login")


class ClientSignupView(FormView):
    template_name = "accounts/signup.html"
    form_class = ClientSignupForm
    success_url = reverse_lazy("accounts:dashboard")
    service_class = PortalAccountService
    extra_context = {"page_title": "Créer un compte client"}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["account_service"] = self.service_class()
        return kwargs

    def form_valid(self, form):
        try:
            result = form.save()
        except PortalAccountServiceError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        user = authenticate(
            self.request,
            username=result.login,
            password=form.cleaned_data["password1"],
        )
        if user is not None:
            auth_login(self.request, user)
            session_payload = getattr(user, "_tryton_session", None)
            if session_payload:
                self.request.session["tryton_session"] = session_payload
            messages.success(self.request, "Votre compte a été créé et vous êtes connecté.")
            return redirect(self.get_success_url())

        messages.success(
            self.request,
            "Votre compte a été créé. Vous pouvez maintenant vous connecter avec vos identifiants.",
        )
        return redirect("accounts:login")


class ClientProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"
    login_url = reverse_lazy("accounts:login")
    service_class = PortalAccountService

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.account_service = self.service_class()

    def get(self, request, *args, **kwargs):
        profile = self._load_profile()
        if profile is None:
            return redirect("accounts:dashboard")
        return self.render_to_response(self.get_context_data(profile=profile))

    def post(self, request, *args, **kwargs):
        profile = self._load_profile()
        if profile is None:
            return redirect("accounts:dashboard")
        action = request.POST.get("form_name")

        if action == "profile":
            profile_form = ClientProfileForm(request.POST)
            if profile_form.is_valid():
                cleaned = profile_form.cleaned_data
                try:
                    self.account_service.update_client_profile(
                        login=self._current_login(),
                        company_name=cleaned.get("company_name"),
                        first_name=cleaned["first_name"],
                        last_name=cleaned["last_name"],
                        phone=cleaned.get("phone"),
                        address=cleaned.get("address"),
                        city=cleaned.get("city"),
                        postal_code=cleaned.get("postal_code"),
                    )
                except PortalAccountServiceError as exc:
                    profile_form.add_error(None, str(exc))
                else:
                    messages.success(request, "Votre profil a été mis à jour avec succès.")
                    return redirect("accounts:profile")
            return self.render_to_response(
                self.get_context_data(profile=profile, profile_form=profile_form),
            )

        if action == "password":
            password_form = ClientPasswordForm(
                request.POST,
                account_service=self.account_service,
                login=self._current_login(),
            )
            if password_form.is_valid():
                try:
                    password_form.save()
                except PortalAccountServiceError as exc:
                    password_form.add_error(None, str(exc))
                else:
                    messages.success(request, "Votre mot de passe a été mis à jour.")
                    return redirect("accounts:profile")
            return self.render_to_response(
                self.get_context_data(profile=profile, password_form=password_form),
            )

        messages.error(request, "Action non reconnue.")
        return redirect("accounts:profile")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = kwargs.get("profile")
        if profile is None:
            profile = self._load_profile()
        if profile is None:
            return context
        context["profile"] = profile
        context.setdefault("profile_form", self._build_profile_form(profile))
        context.setdefault(
            "password_form",
            ClientPasswordForm(
                account_service=self.account_service,
                login=self._current_login(),
            ),
        )
        return context

    def _load_profile(self) -> PortalClientProfile | None:
        try:
            return self.account_service.fetch_client_profile(login=self._current_login())
        except PortalAccountServiceError as exc:
            messages.error(self.request, str(exc))
            return None

    def _build_profile_form(self, profile: PortalClientProfile) -> ClientProfileForm:
        address = profile.address
        initial = {
            "company_name": profile.company_name or "",
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "email": profile.email,
            "phone": profile.phone or "",
            "address": (address.street if address else "") or "",
            "city": (address.city if address else "") or "",
            "postal_code": (address.postal_code if address else "") or "",
        }
        return ClientProfileForm(initial=initial)

    def _current_login(self) -> str:
        return (self.request.user.username or "").strip().lower()
