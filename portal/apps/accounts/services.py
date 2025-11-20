from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from html import unescape
import re
from typing import Any, Iterable, Optional, Sequence

from django.conf import settings

from apps.core.services import TrytonAuthError, TrytonClient, TrytonRPCError, get_tryton_client

logger = logging.getLogger(__name__)


class PortalAccountServiceError(Exception):
    """Raised when client account provisioning fails."""


class PortalOrderServiceError(Exception):
    """Raised when creating portal-driven sales orders fails."""


@dataclass
class PortalAccountCreationResult:
    login: str
    user_id: int
    party_id: int


@dataclass
class PortalClientAddress:
    street: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None


@dataclass
class PortalClientProfile:
    user_id: int
    party_id: int
    login: str
    email: str
    first_name: str
    last_name: str
    company_name: Optional[str]
    phone: Optional[str]
    address: PortalClientAddress


@dataclass
class PortalOrderAddress:
    id: int
    label: str
    street: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None


@dataclass
class PortalOrderProduct:
    id: int
    name: str
    code: Optional[str]
    unit_id: Optional[int]
    unit_name: Optional[str]
    unit_price: Optional[Decimal] = None

    @property
    def choice_label(self) -> str:
        parts: list[str] = [self.name.strip()]
        if self.code:
            parts.append(f"({self.code.strip()})")
        if self.unit_name:
            parts.append(f"— {self.unit_name.strip()}")
        return " ".join(part for part in parts if part)


@dataclass
class PortalOrderLineInput:
    product_id: int
    quantity: Decimal
    notes: Optional[str] = None


@dataclass
class PortalOrderSubmissionResult:
    order_id: int
    number: Optional[str] = None
    portal_reference: Optional[str] = None


class PortalAccountService:
    """Service layer orchestrating Tryton calls for portal client accounts."""

    def __init__(
        self,
        client: Optional[TrytonClient] = None,
        *,
        portal_group_name: Optional[str] = None,
    ) -> None:
        self.client = client or get_tryton_client()
        self.portal_group_name = portal_group_name or getattr(settings, "TRYTON_PORTAL_GROUP", "Portail Clients")
        self._portal_group_id: Optional[int] = None
        self._base_context: dict[str, Any] = {}
        self._user_has_party_field: Optional[bool] = None
        self._address_postal_field: Optional[str] = None

    def login_exists(self, login: str) -> bool:
        """Return True when a Tryton user already exists for the provided login."""
        normalized = login.strip().lower()
        try:
            result = self.client.call(
                "model.res.user",
                "search",
                [[("login", "=", normalized)], 0, 1, None, self._rpc_context()],
            )
        except TrytonRPCError as exc:
            logger.warning(
                "Unable to verify Tryton login '%s', continuing optimistic signup. Error: %s",
                normalized,
                exc,
            )
            return False
        return bool(result)

    def create_client_account(
        self,
        *,
        company_name: Optional[str],
        first_name: str,
        last_name: str,
        email: str,
        phone: Optional[str],
        password: str,
    ) -> PortalAccountCreationResult:
        """Provision a Tryton party and user for a new client."""
        login = email.strip().lower()
        if self.login_exists(login):
            raise PortalAccountServiceError("Un compte existe déjà pour cette adresse courriel.")

        portal_group_id = self._get_portal_group_id()
        party_id = self._create_party(
            company_name=company_name,
            first_name=first_name,
            last_name=last_name,
            email=login,
            phone=phone,
        )
        try:
            user_id = self._create_user(
                login=login,
                password=password,
                email=login,
                first_name=first_name,
                last_name=last_name,
                party_id=party_id,
                portal_group_id=portal_group_id,
            )
        except PortalAccountServiceError:
            self._rollback_party(party_id)
            raise

        return PortalAccountCreationResult(login=login, user_id=user_id, party_id=party_id)

    def fetch_client_profile(self, *, login: str) -> PortalClientProfile:
        """Retrieve the Tryton-facing profile for a portal user."""
        user_record = self._get_user_record(login)
        party_id = self._resolve_party_id(login=login, user_record=user_record)
        if party_id is None:
            raise PortalAccountServiceError(
                "Ce compte n'est pas encore lié à une fiche client dans Tryton. Contactez le support."
            )

        party_record = self._get_party_record(party_id)
        phone_value = self._get_phone_number(party_id)
        address_record = self._get_primary_address(party_id)
        postal_value = self._extract_postal_value(address_record)
        first_name, last_name = self._split_name(user_record.get("name") or "")
        email = (user_record.get("email") or login).strip()

        return PortalClientProfile(
            user_id=int(user_record["id"]),
            party_id=party_id,
            login=login,
            email=email,
            first_name=first_name,
            last_name=last_name,
            company_name=(party_record.get("name") or "").strip() or None,
            phone=phone_value,
            address=PortalClientAddress(
                street=(address_record.get("street") or "").strip() or None,
                city=(address_record.get("city") or "").strip() or None,
                postal_code=postal_value,
            ),
        )

    def update_client_profile(
        self,
        *,
        login: str,
        company_name: Optional[str],
        first_name: str,
        last_name: str,
        phone: Optional[str],
        address: Optional[str],
        city: Optional[str],
        postal_code: Optional[str],
    ) -> PortalClientProfile:
        """Persist profile edits into Tryton, then re-fetch the profile snapshot."""
        user_record = self._get_user_record(login)
        party_id = self._resolve_party_id(login=login, user_record=user_record)
        if party_id is None:
            raise PortalAccountServiceError(
                "Aucune fiche client Tryton n'est associée à ce compte. Contactez le support."
            )
        context = self._rpc_context()

        # Update Django/portal friendly fields on res.user
        full_name = self._compose_full_name(first_name, last_name) or login
        try:
            self.client.call(
                "model.res.user",
                "write",
                [[int(user_record["id"])], {"name": full_name}, context],
            )
        except TrytonRPCError as exc:
            message = self._extract_tryton_error_message(
                exc,
                "Impossible de mettre à jour le compte utilisateur dans Tryton.",
            )
            raise PortalAccountServiceError(message) from exc

        # Update the linked party with the preferred display name.
        display_name = (company_name or "").strip() or full_name
        try:
            self.client.call(
                "model.party.party",
                "write",
                [[party_id], {"name": display_name}, context],
            )
        except TrytonRPCError as exc:
            message = self._extract_tryton_error_message(
                exc,
                "Impossible de mettre à jour la fiche client dans Tryton.",
            )
            raise PortalAccountServiceError(message) from exc

        self._upsert_phone(party_id, value=(phone or "").strip())
        self._upsert_primary_address(
            party_id,
            street=(address or "").strip(),
            city=(city or "").strip(),
            postal_code=(postal_code or "").strip(),
        )

        return self.fetch_client_profile(login=login)

    def change_password(self, *, login: str, current_password: str, new_password: str) -> None:
        """Change the Tryton password for the provided user after validating the current one."""
        if not self.validate_credentials(login=login, password=current_password):
            raise PortalAccountServiceError("Le mot de passe actuel est invalide.")

        user_record = self._get_user_record(login)
        context = self._rpc_context()
        try:
            self.client.call(
                "model.res.user",
                "write",
                [[int(user_record["id"])], {"password": new_password}, context],
            )
        except TrytonRPCError as exc:
            message = self._extract_tryton_error_message(
                exc,
                "Impossible de mettre à jour le mot de passe dans Tryton.",
            )
            raise PortalAccountServiceError(message) from exc

    def validate_credentials(self, *, login: str, password: str) -> bool:
        """Validate a login/password combo directly against Tryton."""
        temp_client: Optional[TrytonClient] = None
        try:
            temp_client = TrytonClient(username=login, password=password)
            temp_client.login(force=True)
            return True
        except TrytonAuthError:
            return False
        except TrytonRPCError as exc:
            logger.error("Erreur RPC Tryton lors de la validation du mot de passe (%s): %s", login, exc)
            raise PortalAccountServiceError(
                "Vérification du mot de passe impossible pour le moment. Veuillez réessayer."
            ) from exc
        finally:
            if temp_client is not None:
                temp_client.close()

    def _get_portal_group_id(self) -> int:
        if self._portal_group_id is not None:
            return self._portal_group_id
        try:
            group_ids = self.client.call(
                "model.res.group",
                "search",
                [[("name", "=", self.portal_group_name)], 0, 1, None, self._rpc_context()],
            )
        except TrytonRPCError as exc:
            logger.exception("Unable to fetch Tryton portal group '%s'.", self.portal_group_name)
            raise PortalAccountServiceError(
                "La configuration Tryton du portail est invalide (groupe introuvable)."
            ) from exc

        if not group_ids:
            logger.info("Portal group '%s' not found. Attempting auto-creation.", self.portal_group_name)
            try:
                created_ids = self.client.call(
                    "model.res.group",
                    "create",
                    [[{"name": self.portal_group_name}], self._rpc_context()],
                )
            except TrytonRPCError as exc:
                logger.exception("Unable to auto-create Tryton portal group '%s'.", self.portal_group_name)
                raise PortalAccountServiceError(
                    f"Impossible de créer automatiquement le groupe Tryton '{self.portal_group_name}'."
                ) from exc

            if not created_ids:
                raise PortalAccountServiceError(
                    f"Tryton n'a pas retourné d'identifiant lors de la création du groupe '{self.portal_group_name}'."
                )

            group_ids = created_ids

        self._portal_group_id = int(group_ids[0])
        return self._portal_group_id

    def _create_party(
        self,
        *,
        company_name: Optional[str],
        first_name: str,
        last_name: str,
        email: str,
        phone: Optional[str],
    ) -> int:
        display_name = (company_name or "").strip() or f"{first_name} {last_name}".strip() or email
        payload: dict[str, Any] = {"name": display_name}
        contact_mechanisms = []
        if email:
            contact_mechanisms.append({"type": "email", "value": email})
        if phone:
            contact_mechanisms.append({"type": "phone", "value": phone})
        if contact_mechanisms:
            payload["contact_mechanisms"] = [("create", contact_mechanisms)]

        try:
            party_ids = self.client.call("model.party.party", "create", [[payload], self._rpc_context()])
        except TrytonRPCError as exc:
            logger.exception("Unable to create Tryton party for %s.", email)
            message = self._extract_tryton_error_message(
                exc,
                "Impossible de créer la fiche client dans Tryton.",
            )
            raise PortalAccountServiceError(message) from exc

        if not party_ids:
            raise PortalAccountServiceError("Tryton n'a pas retourné d'identifiant pour la fiche client.")
        return int(party_ids[0])

    def _create_user(
        self,
        *,
        login: str,
        password: str,
        email: str,
        first_name: str,
        last_name: str,
        party_id: int,
        portal_group_id: int,
    ) -> int:
        full_name = f"{first_name} {last_name}".strip() or email
        payload = {
            "name": full_name,
            "login": login,
            "password": password,
            "email": email,
            "active": True,
            "groups": [("add", [portal_group_id])],
        }
        if self._user_supports_party_field():
            payload["party"] = party_id
        try:
            user_ids = self.client.call("model.res.user", "create", [[payload], self._rpc_context()])
        except TrytonRPCError as exc:
            logger.exception("Unable to create Tryton user for %s.", login)
            message = self._extract_tryton_error_message(
                exc,
                "Impossible de créer le compte utilisateur dans Tryton. Merci de réessayer plus tard.",
            )
            raise PortalAccountServiceError(message) from exc

        if not user_ids:
            raise PortalAccountServiceError("Tryton n'a pas retourné d'identifiant pour le compte utilisateur.")
        return int(user_ids[0])

    def _rollback_party(self, party_id: int) -> None:
        try:
            self.client.call("model.party.party", "delete", [[party_id], self._rpc_context()])
        except TrytonRPCError:
            logger.warning("Unable to rollback Tryton party %s after signup failure.", party_id, exc_info=True)

    def _rpc_context(self) -> dict[str, Any]:
        return dict(self._base_context)

    @staticmethod
    def _extract_tryton_error_message(exc: TrytonRPCError, fallback: str) -> str:
        cause = getattr(exc, "__cause__", None)
        response_text = None
        if cause is not None and hasattr(cause, "response"):
            response = getattr(cause, "response", None)
            if response is not None:
                response_text = getattr(response, "text", None)
        if response_text:
            match = re.search(r"<p>(.*?)</p>", response_text, re.S | re.IGNORECASE)
            if match:
                extracted = unescape(match.group(1)).strip()
                if extracted:
                    return extracted
            cleaned = unescape(re.sub(r"<[^>]+>", " ", response_text))
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if cleaned:
                return cleaned
        return fallback

    def _user_supports_party_field(self) -> bool:
        if self._user_has_party_field is not None:
            return self._user_has_party_field
        try:
            fields = self.client.call(
                "model.res.user",
                "fields_get",
                [["party"], self._rpc_context()],
            )
        except TrytonRPCError as exc:
            logger.warning("Unable to introspect res.user fields: %s. Assuming party field is unavailable.", exc)
            self._user_has_party_field = False
            return False
        if not isinstance(fields, dict):
            fields = {}
        self._user_has_party_field = "party" in fields
        if not self._user_has_party_field:
            logger.warning(
                "Tryton res.user model does not expose a 'party' field. Users will be created without linkage."
            )
        return self._user_has_party_field

    def _get_user_record(self, login: str) -> dict[str, Any]:
        """Fetch a single Tryton user by login."""
        normalized = login.strip().lower()
        context = self._rpc_context()
        party_supported = self._user_supports_party_field()
        requested_fields = ["id", "name", "email"]
        if party_supported:
            requested_fields.append("party")
        try:
            user_ids = self.client.call(
                "model.res.user",
                "search",
                [[("login", "=", normalized)], 0, 1, None, context],
            )
        except TrytonRPCError as exc:
            logger.exception("Impossible de rechercher l'utilisateur Tryton %s.", normalized)
            raise PortalAccountServiceError("Impossible de récupérer votre profil. Réessayez plus tard.") from exc

        if not user_ids:
            raise PortalAccountServiceError("Utilisateur introuvable dans Tryton.")

        try:
            records = self.client.call(
                "model.res.user",
                "read",
                [[int(user_ids[0])], requested_fields, context],
            )
        except TrytonRPCError as exc:
            logger.exception("Impossible de lire le profil Tryton de %s.", normalized)
            raise PortalAccountServiceError("Lecture du profil utilisateur impossible.") from exc

        if not records:
            raise PortalAccountServiceError("Les données de l'utilisateur Tryton sont manquantes.")
        return records[0]

    def _resolve_party_id(self, *, login: str, user_record: dict[str, Any]) -> Optional[int]:
        if self._user_supports_party_field():
            party_id = self._extract_id(user_record.get("party"))
            if party_id is not None:
                return party_id
        return self._find_party_by_email(login=login)

    def _get_party_record(self, party_id: int) -> dict[str, Any]:
        try:
            records = self.client.call(
                "model.party.party",
                "read",
                [[party_id], ["id", "name"], self._rpc_context()],
            )
        except TrytonRPCError as exc:
            logger.exception("Impossible de lire la fiche party %s.", party_id)
            raise PortalAccountServiceError("Lecture de la fiche client impossible.") from exc
        if not records:
            raise PortalAccountServiceError("La fiche client associée est introuvable.")
        return records[0]

    def _find_party_by_email(self, login: str) -> Optional[int]:
        normalized = login.strip().lower()
        context = self._rpc_context()
        try:
            contact_ids = self.client.call(
                "model.party.contact_mechanism",
                "search",
                [[("type", "=", "email"), ("value", "=", normalized)], 0, 1, None, context],
            )
        except TrytonRPCError as exc:
            logger.warning("Impossible de rechercher la fiche client à partir du courriel %s: %s", normalized, exc)
            raise PortalAccountServiceError(
                "Impossible de retrouver votre fiche client dans Tryton. Réessayez plus tard."
            ) from exc

        contact_id = self._extract_id(contact_ids[0]) if contact_ids else None
        if contact_id is None:
            return None
        try:
            records = self.client.call(
                "model.party.contact_mechanism",
                "read",
                [[contact_id], ["party"], context],
            )
        except TrytonRPCError as exc:
            logger.warning("Impossible de lire le contact courriel %s: %s", contact_id, exc)
            raise PortalAccountServiceError(
                "Impossible de confirmer la fiche client associée à ce compte."
            ) from exc
        if not records:
            return None
        return self._extract_id(records[0].get("party"))

    def _get_phone_number(self, party_id: int) -> Optional[str]:
        context = self._rpc_context()
        try:
            contact_ids = self.client.call(
                "model.party.contact_mechanism",
                "search",
                [[("party", "=", party_id), ("type", "in", ["phone", "mobile"])], 0, 1, None, context],
            )
        except TrytonRPCError as exc:
            logger.warning("Impossible de récupérer les coordonnées téléphoniques pour party=%s: %s", party_id, exc)
            return None
        contact_id = self._extract_id(contact_ids[0]) if contact_ids else None
        if contact_id is None:
            return None
        try:
            records = self.client.call(
                "model.party.contact_mechanism",
                "read",
                [[contact_id], ["value"], context],
            )
        except TrytonRPCError as exc:
            logger.warning("Impossible de lire le contact téléphonique %s: %s", contact_id, exc)
            return None
        if not records:
            return None
        value = (records[0].get("value") or "").strip()
        return value or None

    def _upsert_phone(self, party_id: int, *, value: str) -> None:
        context = self._rpc_context()
        normalized = value.strip()
        try:
            contact_ids = self.client.call(
                "model.party.contact_mechanism",
                "search",
                [[("party", "=", party_id), ("type", "in", ["phone", "mobile"])], 0, 1, None, context],
            )
        except TrytonRPCError as exc:
            logger.exception("Impossible de rechercher les contacts téléphoniques pour party=%s", party_id)
            raise PortalAccountServiceError("Mise à jour du téléphone impossible pour le moment.") from exc

        contact_id = self._extract_id(contact_ids[0]) if contact_ids else None

        if not normalized:
            if contact_id is None:
                return
            try:
                self.client.call(
                    "model.party.contact_mechanism",
                    "delete",
                    [[contact_id], context],
                )
            except TrytonRPCError as exc:
                logger.exception("Erreur lors de la suppression du téléphone pour party=%s", party_id)
                raise PortalAccountServiceError(
                    "Impossible de supprimer le téléphone dans Tryton. Réessayez plus tard."
                ) from exc
            return

        try:
            if contact_id is not None:
                self.client.call(
                    "model.party.contact_mechanism",
                    "write",
                    [[contact_id], {"value": normalized}, context],
                )
            else:
                payload = {
                    "contact_mechanisms": [("create", [{"type": "phone", "value": normalized}])],
                }
                self.client.call(
                    "model.party.party",
                    "write",
                    [
                        [party_id],
                        payload,
                        context,
                    ],
                )
        except TrytonRPCError as exc:
            logger.exception("Erreur lors de la mise à jour du téléphone pour party=%s", party_id)
            message = self._extract_tryton_error_message(
                exc,
                "Impossible de mettre à jour le téléphone dans Tryton. Vérifiez le format et réessayez.",
            )
            raise PortalAccountServiceError(message) from exc

    def _get_primary_address(self, party_id: int) -> dict[str, Any]:
        context = self._rpc_context()
        try:
            address_ids = self.client.call(
                "model.party.address",
                "search",
                [[("party", "=", party_id)], 0, 1, None, context],
            )
        except TrytonRPCError as exc:
            logger.warning("Impossible de rechercher les adresses pour party=%s: %s", party_id, exc)
            return {}
        address_id = self._extract_id(address_ids[0]) if address_ids else None
        if address_id is None:
            return {}
        postal_field = self._get_address_postal_field()
        fields = ["id", "street", "city"]
        if postal_field:
            fields.append(postal_field)
        try:
            records = self.client.call(
                "model.party.address",
                "read",
                [[address_id], fields, context],
            )
        except TrytonRPCError as exc:
            logger.warning("Impossible de lire l'adresse %s: %s", address_id, exc)
            return {}
        return records[0] if records else {}

    def _upsert_primary_address(
        self,
        party_id: int,
        *,
        street: str,
        city: str,
        postal_code: str,
    ) -> None:
        has_content = any([street, city, postal_code])
        context = self._rpc_context()
        try:
            address_ids = self.client.call(
                "model.party.address",
                "search",
                [[("party", "=", party_id)], 0, 1, None, context],
            )
        except TrytonRPCError as exc:
            logger.exception("Impossible de rechercher les adresses pour party=%s", party_id)
            raise PortalAccountServiceError("Impossible de mettre à jour l'adresse pour le moment.") from exc

        address_id = self._extract_id(address_ids[0]) if address_ids else None
        payload = {
            "street": street,
            "city": city,
        }
        postal_field = self._get_address_postal_field()
        if postal_field and postal_code:
            payload[postal_field] = postal_code
        try:
            if address_id is not None:
                self.client.call(
                    "model.party.address",
                    "write",
                    [[address_id], payload, context],
                )
            elif has_content:
                payload["party"] = party_id
                self.client.call(
                    "model.party.address",
                    "create",
                    [[payload], context],
                )
        except TrytonRPCError as exc:
            logger.exception("Erreur lors de la mise à jour de l'adresse pour party=%s", party_id)
            raise PortalAccountServiceError("Impossible de mettre à jour l'adresse dans Tryton.") from exc

    def _get_address_postal_field(self) -> Optional[str]:
        if self._address_postal_field is not None:
            return self._address_postal_field
        context = self._rpc_context()
        candidates = ("postal_code", "zip", "postcode")
        try:
            sample_ids = self.client.call(
                "model.party.address",
                "search",
                [[], 0, 1, None, context],
            )
        except TrytonRPCError:
            sample_ids = []
        for candidate in candidates:
            if not candidate:
                continue
            if sample_ids:
                try:
                    self.client.call(
                        "model.party.address",
                        "read",
                        [[sample_ids[0]], [candidate], context],
                    )
                except TrytonRPCError:
                    continue
            self._address_postal_field = candidate
            return self._address_postal_field
        return None

    def _extract_postal_value(self, address_record: dict[str, Any]) -> Optional[str]:
        candidates = []
        primary = self._get_address_postal_field()
        if primary:
            candidates.append(primary)
        candidates.extend(field for field in ("postal_code", "zip", "postcode") if field not in candidates)
        for field in candidates:
            value = (address_record.get(field) or "").strip()
            if value:
                self._address_postal_field = field
                return value
        return None

    @staticmethod
    def _split_name(full_name: str) -> tuple[str, str]:
        parts = (full_name or "").strip().split(" ", 1)
        first = parts[0] if parts and parts[0] else ""
        last = parts[1] if len(parts) > 1 else ""
        return first, last

    @staticmethod
    def _compose_full_name(first_name: str, last_name: str) -> str:
        return " ".join(part for part in [first_name.strip(), last_name.strip()] if part).strip()

    @staticmethod
    def _extract_id(value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, (list, tuple)):
            if not value:
                return None
            value = value[0]
        try:
            return int(value)
        except (TypeError, ValueError):
            return None


class PortalOrderService:
    """Service dédié au formulaire de commandes du portail client."""

    def __init__(
        self,
        *,
        client: Optional[TrytonClient] = None,
        account_service: Optional[PortalAccountService] = None,
    ) -> None:
        self.client = client or get_tryton_client()
        self.account_service = account_service or PortalAccountService(client=self.client)
        self._base_context: dict[str, Any] = {}
        self._product_cache: dict[int, PortalOrderProduct] | None = None
        self._company_id: Optional[int] = None
        self._company_currency_id: Optional[int] = None

    def list_orderable_products(self, *, force_refresh: bool = False) -> list[PortalOrderProduct]:
        """Retourne la liste des produits commandables."""
        self._ensure_company_context()
        if self._product_cache is not None and not force_refresh:
            return list(self._product_cache.values())

        context = self._rpc_context()
        domain = [
            ("salable", "=", True),
            ("active", "=", True),
        ]
        try:
            product_ids = self.client.call(
                "model.product.product",
                "search",
                [domain, 0, None, [("name", "ASC")], context],
            )
        except TrytonRPCError as exc:
            logger.exception("Impossible de charger les produits vendables pour le portail.")
            raise PortalOrderServiceError("Impossible de charger la liste des produits. Réessayez plus tard.") from exc

        if not product_ids:
            self._product_cache = {}
            return []

        try:
            records = self.client.call(
                "model.product.product",
                "read",
                [product_ids, ["id", "name", "code", "default_uom", "list_price", "template"], context],
            )
        except TrytonRPCError as exc:
            logger.exception("Impossible de lire les produits %s.", product_ids)
            raise PortalOrderServiceError("Lecture des produits impossible. Réessayez plus tard.") from exc

        catalog = self._build_product_catalog(records or [])
        self._product_cache = catalog
        return list(catalog.values())

    def list_shipment_addresses(self, *, login: str) -> tuple[int, list[PortalOrderAddress]]:
        """Retourne le party Tryton associé au compte et ses adresses de livraison actives."""
        profile = self.account_service.fetch_client_profile(login=login)
        addresses = self._fetch_party_addresses(profile.party_id)
        return profile.party_id, addresses

    def create_draft_order(
        self,
        *,
        login: str,
        client_reference: Optional[str],
        shipping_date: date,
        shipping_address_id: int,
        lines: Sequence[PortalOrderLineInput],
        instructions: Optional[str] = None,
    ) -> PortalOrderSubmissionResult:
        if not lines:
            raise PortalOrderServiceError("Ajoutez au moins une ligne de commande.")

        profile = self.account_service.fetch_client_profile(login=login)
        party_id = profile.party_id
        addresses = self._fetch_party_addresses(party_id)
        address_ids = {address.id for address in addresses}
        if shipping_address_id not in address_ids:
            raise PortalOrderServiceError("Adresse de livraison invalide. Rechargez la page pour actualiser la liste.")

        product_ids = {line.product_id for line in lines}
        products = self._read_products(product_ids)
        missing = product_ids - set(products.keys())
        if missing:
            raise PortalOrderServiceError("Un produit sélectionné n'est plus disponible. Rechargez la page.")

        payload_lines = []
        for line in lines:
            product = products[line.product_id]
            line_payload: dict[str, Any] = {
                "product": product.id,
                "quantity": float(line.quantity),
            }
            if product.unit_id is not None:
                line_payload["unit"] = product.unit_id
            unit_price = product.unit_price
            if unit_price is None:
                raise PortalOrderServiceError(
                    f"Le produit « {product.name} » n’a pas de prix de vente configuré. Contactez notre équipe."
                )
            line_payload["unit_price"] = float(unit_price)
            description = (line.notes or "").strip() or product.name
            if description:
                line_payload["description"] = description
            payload_lines.append(line_payload)

        order_payload: dict[str, Any] = {
            "company": self._resolve_company_id(),
            "currency": self._resolve_currency_id(),
            "party": party_id,
            "shipment_address": shipping_address_id,
            "lines": [("create", payload_lines)],
            "state": "draft",
        }
        if client_reference:
            order_payload["reference"] = client_reference.strip()
        if instructions:
            order_payload["comment"] = instructions.strip()
        if shipping_date:
            order_payload["shipping_date"] = shipping_date.isoformat()

        context = self._rpc_context()
        try:
            order_ids = self.client.call("model.sale.sale", "create", [[order_payload], context])
        except TrytonRPCError as exc:
            logger.exception("Impossible de créer la commande pour party=%s.", party_id)
            message = PortalAccountService._extract_tryton_error_message(
                exc,
                "Impossible de créer la commande dans Tryton. Réessayez plus tard.",
            )
            raise PortalOrderServiceError(message) from exc

        order_id = PortalAccountService._extract_id(order_ids[0]) if order_ids else None
        if order_id is None:
            raise PortalOrderServiceError("Tryton n'a pas retourné d'identifiant pour la commande.")

        number = self._read_order_number(order_id, context)
        return PortalOrderSubmissionResult(
            order_id=order_id,
            number=number,
            portal_reference=client_reference.strip() if client_reference else None,
        )

    def _resolve_company_defaults(self) -> tuple[int, int]:
        if self._company_id is not None and self._company_currency_id is not None:
            return self._company_id, self._company_currency_id
        context = self._rpc_context()
        try:
            company_ids = self.client.call(
                "model.company.company",
                "search",
                [[], 0, 1, [("id", "ASC")], context],
            )
        except TrytonRPCError as exc:
            logger.exception("Impossible de déterminer l'entreprise par défaut pour le portail.")
            raise PortalOrderServiceError(
                "Impossible de déterminer l'entreprise Tryton configurée pour le portail."
            ) from exc
        if not company_ids:
            raise PortalOrderServiceError("Aucune entreprise n'est configurée dans Tryton.")
        company_id = PortalAccountService._extract_id(company_ids[0])
        if company_id is None:
            raise PortalOrderServiceError("Tryton n'a pas retourné d'identifiant d'entreprise.")
        try:
            records = self.client.call(
                "model.company.company",
                "read",
                [[company_id], ["currency"], context],
            )
        except TrytonRPCError as exc:
            logger.exception("Impossible de lire la devise de l'entreprise %s.", company_id)
            raise PortalOrderServiceError("Impossible de lire la configuration de l'entreprise dans Tryton.") from exc
        currency_id = None
        if records:
            currency_id = PortalAccountService._extract_id(records[0].get("currency"))
        if currency_id is None:
            raise PortalOrderServiceError("L'entreprise configurée pour le portail n'a pas de devise.")
        self._company_id = company_id
        self._company_currency_id = currency_id
        self._base_context.setdefault("company", company_id)
        return company_id, currency_id

    def _resolve_company_id(self) -> int:
        company_id, _ = self._resolve_company_defaults()
        return company_id

    def _resolve_currency_id(self) -> int:
        _, currency_id = self._resolve_company_defaults()
        return currency_id

    def _resolve_postal_field(self) -> Optional[str]:
        getter = getattr(self.account_service, "_get_address_postal_field", None)
        if callable(getter):
            return getter()
        return None

    def _fetch_party_addresses(self, party_id: int) -> list[PortalOrderAddress]:
        self._ensure_company_context()
        context = self._rpc_context()
        domain = [
            ("party", "=", party_id),
            ("active", "=", True),
        ]
        try:
            address_ids = self.client.call(
                "model.party.address",
                "search",
                [domain, 0, None, [("id", "ASC")], context],
            )
        except TrytonRPCError as exc:
            logger.exception("Impossible de charger les adresses pour party=%s", party_id)
            raise PortalOrderServiceError("Impossible de charger vos adresses de livraison.") from exc

        if not address_ids:
            return []

        postal_field = self._resolve_postal_field()
        address_fields = ["id", "street", "city", "rec_name"]
        if postal_field and postal_field not in address_fields:
            address_fields.append(postal_field)
        try:
            records = self.client.call(
                "model.party.address",
                "read",
                [address_ids, address_fields, context],
            )
        except TrytonRPCError as exc:
            logger.exception("Impossible de lire les adresses %s.", address_ids)
            raise PortalOrderServiceError("Lecture des adresses impossible. Réessayez plus tard.") from exc

        addresses: list[PortalOrderAddress] = []
        for record in records or []:
            address_id = PortalAccountService._extract_id(record.get("id"))
            if address_id is None:
                continue
            street = (record.get("street") or "").strip() or None
            city = (record.get("city") or "").strip() or None
            postal_code = None
            if postal_field:
                postal_code = (record.get(postal_field) or "").strip() or None
            label_parts = [record.get("rec_name") or "Adresse"]
            line_parts = [part for part in [street, city, postal_code] if part]
            if line_parts:
                label_parts.append(" – ".join(line_parts))
            addresses.append(
                PortalOrderAddress(
                    id=address_id,
                    label=" ".join(label_parts).strip(),
                    street=street,
                    city=city,
                    postal_code=postal_code,
                )
            )
        return addresses

    def _read_products(self, product_ids: Iterable[int]) -> dict[int, PortalOrderProduct]:
        self._ensure_company_context()
        ids_list = sorted({int(pid) for pid in product_ids if pid is not None})
        if not ids_list:
            return {}
        context = self._rpc_context()
        try:
            records = self.client.call(
                "model.product.product",
                "read",
                [ids_list, ["id", "name", "code", "default_uom", "list_price"], context],
            )
        except TrytonRPCError as exc:
            logger.exception("Impossible de lire les produits %s.", ids_list)
            raise PortalOrderServiceError("Impossible de vérifier les produits sélectionnés.") from exc

        return self._build_product_catalog(records or [])

    def _read_order_number(self, order_id: int, context: dict[str, Any]) -> Optional[str]:
        try:
            records = self.client.call("model.sale.sale", "read", [[order_id], ["number"], context])
        except TrytonRPCError:
            logger.warning("Impossible de lire le numéro de commande pour sale.sale %s.", order_id, exc_info=True)
            return None
        if not records:
            return None
        number = records[0].get("number")
        return str(number) if number else None

    def _rpc_context(self) -> dict[str, Any]:
        return dict(self._base_context)

    @staticmethod
    def _to_decimal(value: Any) -> Optional[Decimal]:
        if value in (None, ""):
            return None
        if isinstance(value, dict) and value.get("__class__") == "Decimal":
            value = value.get("decimal")
        try:
            return Decimal(str(value))
        except (ArithmeticError, ValueError, TypeError):
            return None

    def _build_product_catalog(self, records: list[dict[str, Any]]) -> dict[int, PortalOrderProduct]:
        parsed: list[dict[str, Any]] = []
        missing_templates: set[int] = set()
        for record in records:
            product_id = PortalAccountService._extract_id(record.get("id"))
            if product_id is None:
                continue
            uom = record.get("default_uom")
            unit_id = PortalAccountService._extract_id(uom)
            unit_name = None
            if isinstance(uom, (list, tuple)) and len(uom) > 1:
                unit_name = str(uom[1])
            elif isinstance(uom, dict) and uom.get("rec_name"):
                unit_name = str(uom["rec_name"])
            template_id = PortalAccountService._extract_id(record.get("template"))
            unit_price = self._to_decimal(record.get("list_price"))
            if unit_price is None and template_id is not None:
                missing_templates.add(template_id)
            parsed.append(
                {
                    "id": product_id,
                    "name": str(record.get("name") or f"Produit #{product_id}"),
                    "code": (record.get("code") or None),
                    "unit_id": unit_id,
                    "unit_name": unit_name,
                    "template_id": template_id,
                    "unit_price": unit_price,
                }
            )

        template_prices = self._fetch_template_prices(missing_templates) if missing_templates else {}
        catalog: dict[int, PortalOrderProduct] = {}
        for entry in parsed:
            unit_price = entry["unit_price"]
            if unit_price is None and entry["template_id"] is not None:
                unit_price = template_prices.get(entry["template_id"])
            catalog[entry["id"]] = PortalOrderProduct(
                id=entry["id"],
                name=entry["name"],
                code=entry["code"],
                unit_id=entry["unit_id"],
                unit_name=entry["unit_name"],
                unit_price=unit_price,
            )
        return catalog

    def _fetch_template_prices(self, template_ids: Iterable[int]) -> dict[int, Optional[Decimal]]:
        ids_list = sorted({int(tid) for tid in template_ids if tid is not None})
        if not ids_list:
            return {}
        context = self._rpc_context()
        try:
            records = self.client.call(
                "model.product.template",
                "read",
                [ids_list, ["list_price"], context],
            )
        except TrytonRPCError as exc:
            logger.exception("Impossible de lire les gabarits produits %s.", ids_list)
            raise PortalOrderServiceError("Impossible de charger les prix des produits.") from exc
        prices: dict[int, Optional[Decimal]] = {}
        for record in records or []:
            template_id = PortalAccountService._extract_id(record.get("id"))
            if template_id is None:
                continue
            prices[template_id] = self._to_decimal(record.get("list_price"))
        return prices

    def _ensure_company_context(self) -> None:
        if "company" not in self._base_context:
            company_id, _ = self._resolve_company_defaults()
            self._base_context["company"] = company_id
