import logging
from typing import Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend

from apps.core.services import TrytonAuthError, TrytonClient, TrytonRPCError

logger = logging.getLogger(__name__)


class TrytonBackend(BaseBackend):
    """Authenticate Django users against Tryton credentials."""

    def authenticate(
        self,
        request,
        username: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs,
    ):
        if not username or not password:
            return None

        UserModel = get_user_model()
        client = None
        try:
            client = TrytonClient(username=username, password=password)
        except ValueError:
            logger.warning("Tryton backend misconfigured: missing credentials for authentication.")
            return None

        try:
            client.login(force=True)
            session_context = client.get_session_context()
            full_name = username
            email = username
            try:
                preferences = client.call(
                    "model.res.user",
                    "get_preferences",
                    [False],
                ) or {}
                full_name = preferences.get("name") or full_name
                email = preferences.get("email") or email
            except TrytonRPCError as exc:
                logger.info("Unable to fetch Tryton preferences for %s: %s", username, exc)
        except TrytonAuthError:
            logger.info("Tryton authentication failed for username=%s", username)
            return None
        except TrytonRPCError as exc:
            logger.error("Tryton RPC error during authentication for %s: %s", username, exc)
            return None
        else:
            first_name, last_name = self._split_name(full_name)

            user, _ = UserModel.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                },
            )
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.is_active = True
            user.set_unusable_password()
            user.save(update_fields=["email", "first_name", "last_name", "password", "is_active"])

            # Attach session info to the in-memory instance so the view can persist it.
            user._tryton_session = session_context  # type: ignore[attr-defined]
            return user
        finally:
            if client is not None:
                client.close()

    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None

    @staticmethod
    def _split_name(full_name: str) -> tuple[str, str]:
        parts = full_name.strip().split(" ", 1)
        first = parts[0] if parts else ""
        last = parts[1] if len(parts) > 1 else ""
        return first, last
