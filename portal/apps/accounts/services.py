from __future__ import annotations

import logging
from dataclasses import dataclass
from html import unescape
import re
from typing import Any, Optional

from django.conf import settings

from apps.core.services import TrytonAuthError, TrytonClient, TrytonRPCError, get_tryton_client

logger = logging.getLogger(__name__)


class PortalAccountServiceError(Exception):
    """Raised when client account provisioning fails."""


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
                postal_code=(address_record.get("zip") or "").strip() or None,
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
                self.client.call(
                    "model.party.party",
                    "write",
                    [
                        [party_id],
                        {"contact_mechanisms": [("create", [{"type": "phone", "value": normalized}])]},
                        context,
                    ],
                )
        except TrytonRPCError as exc:
            logger.exception("Erreur lors de la mise à jour du téléphone pour party=%s", party_id)
            raise PortalAccountServiceError(
                "Impossible de mettre à jour le téléphone dans Tryton. Vérifiez le format et réessayez."
            ) from exc

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
        try:
            records = self.client.call(
                "model.party.address",
                "read",
                [[address_id], ["id", "street", "city", "zip"], context],
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
            "zip": postal_code,
        }
        try:
            if address_id is not None:
                self.client.call(
                    "model.party.address",
                    "write",
                    [[address_id], payload, context],
                )
            elif has_content:
                payload["party"] = party_id
                payload.setdefault("name", "Adresse principale")
                self.client.call(
                    "model.party.address",
                    "create",
                    [[payload], context],
                )
        except TrytonRPCError as exc:
            logger.exception("Erreur lors de la mise à jour de l'adresse pour party=%s", party_id)
            raise PortalAccountServiceError("Impossible de mettre à jour l'adresse dans Tryton.") from exc

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
