from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from .forms import EmailAuthenticationForm


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


class ClientSignupPlaceholderView(TemplateView):
    template_name = "accounts/signup_placeholder.html"
