from datetime import date
from decimal import Decimal
from math import ceil
from typing import Optional
from html import unescape

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView, TemplateView, View

from .forms import (
    ClientPasswordForm,
    ClientProfileForm,
    ClientSignupForm,
    EmailAuthenticationForm,
    OrderDraftForm,
    OrderLineFormSet,
    ORDER_LINES_FORMSET_PREFIX,
)
from .services import (
    PortalAccountService,
    PortalAccountServiceError,
    PortalClientProfile,
    PortalInvoiceService,
    PortalInvoiceServiceError,
    PortalInvoiceSummary,
    PortalInvoiceListResult,
    PortalOrderLineInput,
    PortalOrderListResult,
    PortalOrderProduct,
    PortalOrderService,
    PortalOrderServiceError,
    PortalOrderSummary,
)
from apps.core.utils.notifications import sanitize_error_message

class MissingAddressError(Exception):
    """Levée quand aucune adresse de livraison n'est disponible."""
    pass


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
    invoice_service_class = PortalInvoiceService
    order_service_class = PortalOrderService
    recent_limit = 5
    order_period_days = PortalOrderService.DEFAULT_PERIOD_DAYS

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.invoice_service = self.invoice_service_class()
        self.order_service = self.order_service_class()

    def get(self, request, *args, **kwargs):
        login = self._current_login()
        invoices_result = self._safe_load_invoices(login)
        orders_result = self._safe_load_orders(login)

        summary = self._build_summary(invoices_result, login)
        activity = self._build_activity_feed(
            invoices=invoices_result.invoices if invoices_result else [],
            orders=orders_result.orders if orders_result else [],
        )

        return self.render_to_response(
            self.get_context_data(
                greeting_name=self._greeting_name(),
                summary=summary,
                recent_invoices=invoices_result.invoices[: self.recent_limit] if invoices_result else [],
                recent_orders=orders_result.orders if orders_result else [],
                activity_items=activity,
            )
        )

    def _greeting_name(self) -> str:
        """Return a clean display name for the dashboard hero."""
        first_name = (getattr(self.request.user, "first_name", "") or "").strip()
        if first_name and "{{" not in first_name and "}}" not in first_name:
            return first_name
        fallback = (getattr(self.request.user, "email", "") or getattr(self.request.user, "username", "") or "").strip()
        return fallback

    def _safe_load_invoices(self, login: str) -> PortalInvoiceListResult | None:
        try:
            return self.invoice_service.list_invoices(
                login=login,
                page=1,
                page_size=self.recent_limit,
            )
        except PortalInvoiceServiceError as exc:
            messages.error(self.request, sanitize_error_message(str(exc)))
            return None

    def _safe_load_orders(self, login: str) -> PortalOrderListResult | None:
        try:
            return self.order_service.list_orders(
                login=login,
                period_days=self.order_period_days,
                page=1,
                page_size=self.recent_limit,
            )
        except PortalOrderServiceError as exc:
            messages.error(self.request, sanitize_error_message(str(exc)))
            return None

    def _build_summary(self, invoices_result: PortalInvoiceListResult | None, login: str) -> dict[str, object]:
        summary: dict[str, object] = {
            "invoices_due_count": 0,
            "invoices_due_total": None,
            "invoices_currency": None,
            "orders_active_count": 0,
            "orders_to_complete_count": 0,
            "orders_to_complete_label": "0 commande",
            "invoices_breakdown": [],
            "orders_breakdown": [],
        }

        # Invoices stats
        inv_draft = self.invoice_service.count_invoices(login=login, statuses=["draft"])
        inv_posted = self.invoice_service.count_invoices(login=login, statuses=["posted"])
        inv_validated = self.invoice_service.count_invoices(login=login, statuses=["validated"])
        inv_waiting = self.invoice_service.count_invoices(login=login, statuses=["waiting_payment"])
        summary["invoices_breakdown"] = [
            {"label": "Brouillon", "count": inv_draft},
            {"label": "Comptabilisées", "count": inv_posted},
            {"label": "Validées", "count": inv_validated},
            {"label": "En attente", "count": inv_waiting},
        ]
        summary["invoices_due_count"] = inv_posted + inv_validated + inv_waiting + inv_draft

        # Orders stats
        ord_draft = self._count_orders(login=login, statuses=("draft",))
        ord_quotation = self._count_orders(login=login, statuses=("quotation",))
        ord_confirmed = self._count_orders(login=login, statuses=("confirmed",))
        ord_processing = self._count_orders(login=login, statuses=("processing", "sent"))
        summary["orders_breakdown"] = [
            {"label": "Brouillon", "count": ord_draft},
            {"label": "Soumission", "count": ord_quotation},
            {"label": "Confirmées", "count": ord_confirmed},
            {"label": "En traitement", "count": ord_processing},
        ]
        summary["orders_active_count"] = ord_draft + ord_quotation + ord_confirmed + ord_processing

        # Keep total amount from recent list for now (best effort without backend sum)
        if invoices_result:
            due_total = Decimal("0")
            currency = None
            for invoice in invoices_result.invoices:
                if invoice.amount_due is not None and invoice.amount_due > 0:
                    due_total += invoice.amount_due
                if not currency and invoice.currency_label:
                    currency = invoice.currency_label
            summary["invoices_due_total"] = due_total
            summary["invoices_currency"] = currency

        summary["orders_to_complete_count"] = self._count_orders(
            login=login,
            statuses=("draft", "quotation"),
        )
        count = summary["orders_to_complete_count"]
        plural = "s" if count != 1 else ""
        summary["orders_to_complete_label"] = f"{count} commande{plural}"
        return summary

    def _count_orders(self, *, login: str, statuses: tuple[str, ...]) -> int:
        try:
            result = self.order_service.list_orders(
                login=login,
                statuses=statuses,
                period_days=self.order_period_days,
                page=1,
                page_size=1,
            )
        except PortalOrderServiceError as exc:
            messages.error(self.request, sanitize_error_message(str(exc)))
            return 0
        return result.pagination.total

    def _build_activity_feed(
        self,
        *,
        invoices: list[PortalInvoiceSummary],
        orders: list[PortalOrderSummary],
    ) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []

        for invoice in invoices:
            items.append(
                {
                    "type": "invoice",
                    "title": invoice.number or "Facture",
                    "date": invoice.issue_date or invoice.due_date,
                    "amount": invoice.amount_due if invoice.amount_due is not None else invoice.total_amount,
                    "currency": invoice.currency_label,
                    "status_label": self._status_label("invoice", invoice.state_label, invoice.state),
                    "status_style": self._status_style("invoice", invoice.state),
                    "url": reverse("accounts:invoices-list"),
                }
            )

        for order in orders:
            items.append(
                {
                    "type": "order",
                    "title": order.number or order.reference or "Commande",
                    "date": order.create_date or order.shipping_date,
                    "amount": order.total_amount,
                    "currency": order.currency_label,
                    "status_label": self._status_label("order", order.state_label, order.state),
                    "status_style": self._status_style("order", order.state),
                    "url": reverse("accounts:orders-detail", kwargs={"order_id": order.id}),
                }
            )

        items.sort(key=lambda item: self._sort_date(item.get("date")), reverse=True)
        return items[: self.recent_limit]

    @staticmethod
    def _sort_date(value: date | None) -> date:
        if isinstance(value, date):
            return value
        return date.min

    @staticmethod
    def _status_label(kind: str, label: str | None, state: str | None) -> str:
        state_key = unescape((state or "")).strip().lower()
        mapping = None
        if "{{" in state_key or "}}" in state_key:
            state_key = ""
        if kind == "invoice":
            from .services import PortalInvoiceService

            mapping = PortalInvoiceService.STATE_LABELS.get(state_key)
        else:
            from .services import PortalOrderService

            mapping = PortalOrderService.STATE_LABELS.get(state_key)

        if mapping:
            return mapping

        value = unescape((label or "").strip())
        invalid = (not value) or ("{{" in value) or ("}}" in value) or ("item.status_label" in value.lower())
        if not invalid:
            return value

        return state_key.capitalize() or "Inconnu"

    @staticmethod
    def _status_style(kind: str, state: str | None) -> str:
        normalized = (state or "").strip().lower()
        if kind == "invoice":
            if normalized in {"waiting_payment", "validated"}:
                return "warning"
            if normalized == "paid":
                return "success"
            if normalized in {"cancelled", "draft"}:
                return "muted"
            return "info"
        # Orders
        if normalized in {"draft", "quotation"}:
            return "warning"
        if normalized in {"confirmed", "processing", "sent"}:
            return "info"
        if normalized == "done":
            return "success"
        if normalized == "cancelled":
            return "muted"
        return "info"

    def _current_login(self) -> str:
        return (self.request.user.username or "").strip().lower()


class InvoiceListView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/invoices_list.html"
    login_url = reverse_lazy("accounts:login")
    service_class = PortalInvoiceService
    default_page_size = PortalInvoiceService.DEFAULT_PAGE_SIZE

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.invoice_service = self.service_class()

    def get(self, request, *args, **kwargs):
        page = self._safe_positive_int(request.GET.get("page"), default=1)
        result = None
        try:
            result = self.invoice_service.list_invoices(
                login=self._current_login(),
                page=page,
                page_size=self.default_page_size,
            )
        except PortalInvoiceServiceError as exc:
            messages.error(request, sanitize_error_message(str(exc)))

        invoices = result.invoices if result else []
        pagination = result.pagination if result else None
        summary = self._build_summary(invoices)
        return self.render_to_response(
            self.get_context_data(
                invoices=invoices,
                pagination=pagination,
                summary=summary,
            )
        )

    @staticmethod
    def _safe_positive_int(raw_value, *, default: int = 1) -> int:
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            return default
        return value if value > 0 else default

    def _current_login(self) -> str:
        return (self.request.user.username or "").strip().lower()

    @staticmethod
    def _build_summary(invoices: list) -> dict[str, object]:
        due_total = Decimal("0")
        currency = None
        for invoice in invoices:
            if invoice.amount_due:
                due_total += invoice.amount_due
            if not currency and invoice.currency_label:
                currency = invoice.currency_label
        return {
            "count": len(invoices),
            "due_total": due_total,
            "currency": currency,
        }


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
            messages.error(self.request, sanitize_error_message(str(exc)))
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


class OrderCreateView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/orders_form.html"
    login_url = reverse_lazy("accounts:login")
    form_class = OrderDraftForm
    line_formset_class = OrderLineFormSet
    service_class = PortalOrderService

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.order_service = self.service_class()
        self._product_options: list[tuple[int, str]] | None = None
        self._addresses_cache: list[tuple[int, str]] | None = None

    def get(self, request, *args, **kwargs):
        try:
            form = self.form_class(address_choices=self._address_choices())
            formset = self._build_line_formset()
        except MissingAddressError:
            messages.warning(
                request,
                "Veuillez compléter votre profil avec une adresse de livraison avant de passer commande.",
            )
            return redirect("accounts:profile")
        except PortalOrderServiceError as exc:
            messages.error(request, sanitize_error_message(str(exc)))
            return redirect("accounts:dashboard")
        return self.render_to_response(
            self.get_context_data(
                form=form,
                line_formset=formset,
                product_choices=self._product_choices(),
                address_choices=self._address_choices(),
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("catalog_url", reverse("accounts:orders-catalog"))
        return context

    def post(self, request, *args, **kwargs):
        try:
            address_choices = self._address_choices()
            product_choices = self._product_choices()
        except MissingAddressError:
            messages.warning(
                request,
                "Veuillez compléter votre profil avec une adresse de livraison avant de passer commande.",
            )
            return redirect("accounts:profile")
        except PortalOrderServiceError as exc:
            messages.error(request, sanitize_error_message(str(exc)))
            return redirect("accounts:dashboard")

        form = self.form_class(request.POST, address_choices=address_choices)
        formset = self._build_line_formset(data=request.POST)

        if form.is_valid() and formset.is_valid():
            lines = self._prepare_lines(formset)
            try:
                result = self.order_service.create_draft_order(
                    login=self._current_login(),
                    client_reference=form.cleaned_data.get("client_reference"),
                    shipping_date=form.cleaned_data["shipping_date"],
                    shipping_address_id=form.cleaned_data["shipping_address"],
                    lines=lines,
                    instructions=form.cleaned_data.get("notes"),
                )
            except PortalOrderServiceError as exc:
                messages.error(request, sanitize_error_message(str(exc)))
            else:
                success_message = "Votre commande a été transmise."
                if result.portal_reference:
                    success_message += f" Référence: {result.portal_reference}."
                elif result.number:
                    success_message += f" Numéro Tryton: {result.number}."
                messages.success(request, success_message)
                return redirect("accounts:dashboard")

        return self.render_to_response(
            self.get_context_data(
                form=form,
                line_formset=formset,
                product_choices=self._product_choices(),
                address_choices=self._address_choices(),
            )
        )

    def _prepare_lines(self, formset: OrderLineFormSet) -> list[PortalOrderLineInput]:
        lines: list[PortalOrderLineInput] = []
        for form in formset:
            if not hasattr(form, "cleaned_data"):
                continue
            data = form.cleaned_data
            if data.get("DELETE"):
                continue
            if data.get("is_empty"):
                continue
            product_id = data.get("product")
            quantity = data.get("quantity")
            if product_id is None or quantity is None:
                continue
            lines.append(
                PortalOrderLineInput(
                    product_id=product_id,
                    quantity=quantity,
                    notes=data.get("notes"),
                )
            )
        return lines

    def _build_line_formset(self, data=None):
        return self.line_formset_class(
            data=data,
            prefix=ORDER_LINES_FORMSET_PREFIX,
            form_kwargs={"product_choices": self._product_choices()},
        )

    def _product_choices(self) -> list[tuple[int, str]]:
        if self._product_options is None:
            products = self.order_service.list_orderable_products()
            if not products:
                raise PortalOrderServiceError(
                    "Aucun produit n’est disponible pour le portail. Contactez notre équipe pour activer le catalogue."
                )
            self._product_options = [(product.id, product.choice_label) for product in products]
        return self._product_options

    def _address_choices(self) -> list[tuple[int, str]]:
        if self._addresses_cache is None:
            _, addresses = self.order_service.list_shipment_addresses(login=self._current_login())
            if not addresses:
                raise MissingAddressError(
                    "Aucune adresse de livraison n’est configurée pour votre compte."
                )
            self._addresses_cache = [(addr.id, addr.label) for addr in addresses]
        return self._addresses_cache

    def _current_login(self) -> str:
        return (self.request.user.username or "").strip().lower()


class OrderListView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/orders_list.html"
    login_url = reverse_lazy("accounts:login")
    service_class = PortalOrderService
    default_page_size = PortalOrderService.DEFAULT_PAGE_SIZE
    default_period_days = PortalOrderService.DEFAULT_PERIOD_DAYS

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.order_service = self.service_class()

    def get(self, request, *args, **kwargs):
        filters = self._parse_filters()
        result = None
        try:
            result = self.order_service.list_orders(
                login=self._current_login(),
                statuses=filters["statuses"],
                period_days=filters["period_days"],
                search=filters["search"],
                page=filters["page"],
                page_size=filters["page_size"],
            )
        except PortalOrderServiceError as exc:
            messages.error(request, sanitize_error_message(str(exc)))

        orders = result.orders if result else []
        pagination = result.pagination if result else None
        return self.render_to_response(
            self.get_context_data(
                orders=orders,
                pagination=pagination,
                filters=filters,
                status_options=self._build_status_options(filters["statuses"]),
                period_options=self._build_period_options(filters["period_days"]),
            )
        )

    def _parse_filters(self) -> dict[str, object]:
        request = self.request
        statuses = [value for value in request.GET.getlist("statut") if value]
        period_raw = request.GET.get("periode")
        period_days = (
            self._safe_positive_int(period_raw, default=self.default_period_days)
            if period_raw
            else self.default_period_days
        )
        search = (request.GET.get("recherche") or "").strip()
        page = self._safe_positive_int(request.GET.get("page"), default=1)
        page_size = self.default_page_size
        return {
            "statuses": statuses,
            "period_days": period_days,
            "search": search,
            "page": page,
            "page_size": page_size,
        }

    def _build_status_options(self, selected: list[str]) -> list[dict[str, object]]:
        normalized_selected = {value.strip().lower() for value in selected}
        options = []
        for key, label in self.order_service.STATE_LABELS.items():
            options.append(
                {
                    "value": key,
                    "label": label,
                    "selected": key in normalized_selected,
                }
            )
        return options

    def _build_period_options(self, selected_period: Optional[int]) -> list[dict[str, object]]:
        selected = selected_period if selected_period is not None else self.default_period_days
        candidates = [30, 90, 180]
        options = []
        for value in candidates:
            options.append(
                {
                    "value": value,
                    "label": f"Derniers {value} jours",
                    "selected": value == selected,
                }
            )
        return options

    @staticmethod
    def _safe_positive_int(raw_value, *, default: int = 1) -> int:
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            return default
        return value if value > 0 else default

    def _current_login(self) -> str:
        return (self.request.user.username or "").strip().lower()


class OrderDetailView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/order_detail.html"
    login_url = reverse_lazy("accounts:login")
    service_class = PortalOrderService

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.order_service = self.service_class()

    def get(self, request, *args, **kwargs):
        order_id = kwargs.get("order_id")
        detail = None
        try:
            detail = self.order_service.get_order_detail(
                login=self._current_login(),
                order_id=order_id,
            )
        except PortalOrderServiceError as exc:
            messages.error(request, sanitize_error_message(str(exc)))
            return redirect("accounts:orders-list")
        return self.render_to_response(
            self.get_context_data(
                order=detail,
            )
        )

    def _current_login(self) -> str:
        return (self.request.user.username or "").strip().lower()


class OrderCatalogView(LoginRequiredMixin, View):
    """Retour JSON paginé pour le catalogue de produits."""

    login_url = reverse_lazy("accounts:login")
    service_class = PortalOrderService
    http_method_names = ["get"]

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.order_service = self.service_class()

    def get(self, request, *args, **kwargs):
        try:
            products = self.order_service.list_orderable_products()
        except PortalOrderServiceError as exc:
            return JsonResponse({"error": str(exc)}, status=503)

        query = (request.GET.get("q") or "").strip()
        matches = self._apply_query_filter(products, query)
        unit_param = (request.GET.get("unit") or "").strip()
        unit_filters = self._build_unit_filters(matches)
        filtered = self._apply_unit_filter(matches, unit_param)
        page = self._parse_positive_int(request.GET.get("page"), default=1)
        page_size = self._sanitize_page_size(request.GET.get("page_size"))
        page_slice, pagination = self._paginate(filtered, page, page_size)

        payload = {
            "results": [self._serialize_product(product) for product in page_slice],
            "pagination": pagination,
            "filters": {"unit": unit_filters},
            "query": query,
            "active_filters": {"unit": unit_param},
        }
        return JsonResponse(payload)

    @staticmethod
    def _serialize_product(product: PortalOrderProduct) -> dict[str, object]:
        return {
            "id": product.id,
            "name": product.name,
            "code": product.code,
            "unit_id": product.unit_id,
            "unit_name": product.unit_name,
            "choice_label": product.choice_label,
            "summary": product.choice_label,
        }

    @staticmethod
    def _apply_query_filter(products: list[PortalOrderProduct], query: str) -> list[PortalOrderProduct]:
        normalized = query.strip().lower()
        if not normalized:
            return list(products)
        filtered: list[PortalOrderProduct] = []
        for product in products:
            haystack = " ".join(
                part
                for part in [product.name, product.code or "", product.unit_name or ""]
                if part
            ).lower()
            if normalized in haystack:
                filtered.append(product)
        return filtered

    @staticmethod
    def _apply_unit_filter(
        products: list[PortalOrderProduct],
        unit_param: str,
    ) -> list[PortalOrderProduct]:
        if not unit_param:
            return list(products)
        if unit_param == "none":
            return [product for product in products if product.unit_id is None]
        try:
            unit_id = int(unit_param)
        except (TypeError, ValueError):
            return list(products)
        return [product for product in products if product.unit_id == unit_id]

    @staticmethod
    def _build_unit_filters(products: list[PortalOrderProduct]) -> list[dict[str, object]]:
        counts: dict[str, dict[str, object]] = {}
        for product in products:
            key = "none" if product.unit_id is None else str(product.unit_id)
            label = product.unit_name.strip() if product.unit_name else "Sans unité"
            entry = counts.get(key)
            if entry is None:
                entry = {"value": key, "label": label, "count": 0}
                counts[key] = entry
            if not entry["label"] and label:
                entry["label"] = label
            entry["count"] += 1
        options = list(counts.values())
        options.sort(key=lambda item: str(item["label"]).lower())
        return options

    def _paginate(
        self,
        products: list[PortalOrderProduct],
        page: int,
        page_size: int,
    ) -> tuple[list[PortalOrderProduct], dict[str, object]]:
        total = len(products)
        if total == 0:
            pagination = {
                "page": 1,
                "pages": 1,
                "page_size": page_size,
                "total": 0,
                "has_next": False,
                "has_previous": False,
            }
            return [], pagination

        pages = max(1, ceil(total / page_size))
        current_page = max(1, min(page, pages))
        start = (current_page - 1) * page_size
        end = start + page_size
        subset = products[start:end]
        pagination = {
            "page": current_page,
            "pages": pages,
            "page_size": page_size,
            "total": total,
            "has_next": current_page < pages,
            "has_previous": current_page > 1,
        }
        return subset, pagination

    @staticmethod
    def _parse_positive_int(raw_value, *, default: int) -> int:
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            return default
        return value if value > 0 else default

    def _sanitize_page_size(self, raw_value) -> int:
        value = self._parse_positive_int(raw_value, default=15)
        return max(1, min(50, value))
