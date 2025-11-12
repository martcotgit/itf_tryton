#!/usr/bin/env python3
"""
Script JSON-RPC pour créer rapidement une centaine de palettes de bois dans Tryton.

Exécution recommandée :
    docker compose run --rm tryton python3 tryton/scripts/create_pallet_products.py

Variables d'environnement :
    TRYTON_URL               URL du service Tryton (défaut : http://tryton:8000/)
    TRYTON_DATABASE          Nom de la base (défaut : tryton)
    TRYTON_USER              Identifiant (défaut : admin)
    TRYTON_PASSWORD          Mot de passe (défaut : admin)
    PALETTE_PRODUCT_COUNT    Nombre de produits (défaut : 100)
    PALETTE_CODE_PREFIX      Préfixe des codes (défaut : PAL)
    PALETTE_BASE_NAME        Préfixe du nom (défaut : Palette de bois)
    PALETTE_CATEGORY_NAME    Catégorie à utiliser/créer (défaut : Palettes de tests)
    PALETTE_UOM_NAME_HINT    Nom ou fragment d'UoM à réutiliser (défaut : Unité)
"""

from __future__ import annotations

import base64
import json
import os
import sys
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List
from urllib import error, request

ROOT_ENDPOINT_METHODS = {
    "common.server.version",
    "common.db.list",
    "common.authentication.services",
}


class JsonRpcError(RuntimeError):
    """Erreur remontée par Tryton via JSON-RPC."""


class TrytonRPCClient:
    def __init__(self, url: str, database: str, user: str, password: str):
        self.base_url = url.rstrip("/") + "/"
        self.database = database.strip().strip("/")
        self.user = user
        self.password = password
        self.context: dict[str, Any] = {"language": "fr"}
        self._counter = 0
        self._session_token: str | None = None
        self._session_user_id: int | None = None
        self._auth_header: str | None = None

    def _next_id(self) -> int:
        self._counter += 1
        return self._counter

    def _build_payload(self, method: str, params: List[Any]) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self._next_id(),
        }

    def _path_for(self, method: str) -> str:
        if method in ROOT_ENDPOINT_METHODS:
            return ""
        if method == "common.db.login" or method.startswith(
            ("model.", "wizard.", "report.", "common.db.")
        ):
            return f"{self.database}/"
        return ""

    def _post(self, path: str, payload: dict[str, Any], headers: dict[str, str] | None = None):
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        request_headers = {
            "Content-Type": "application/json",
            "User-Agent": "tryton-palettes-script",
        }
        if headers:
            request_headers.update(headers)
        req = request.Request(url, data=data, headers=request_headers)
        try:
            with request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="ignore")
            raise JsonRpcError(f"Erreur HTTP {exc.code}: {details}") from exc
        except error.URLError as exc:
            raise JsonRpcError(f"Impossible de contacter Tryton ({exc.reason}).") from exc

        try:
            message = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise JsonRpcError(f"Réponse JSON invalide : {raw}") from exc

        if isinstance(message, dict) and "error" in message:
            err = message["error"]
            raise JsonRpcError(f"{err.get('message')}: {err.get('data')}")
        return message

    def login(self) -> None:
        payload = self._build_payload("common.db.login", [self.user, {"password": self.password}])
        result = self._post(f"{self.database}/", payload)
        if not isinstance(result, list) or len(result) != 2:
            raise JsonRpcError("Réponse inattendue lors de l'authentification.")
        self._session_user_id = int(result[0])
        self._session_token = str(result[1])
        token_value = base64.b64encode(
            f"{self.user}:{self._session_user_id}:{self._session_token}".encode("utf-8")
        ).decode("ascii")
        self._auth_header = f"Session {token_value}"

    def call(self, method: str, params: List[Any]):
        if not self._auth_header:
            raise JsonRpcError("Session absente : appeler login() d'abord.")
        payload = self._build_payload(method, params)
        path = self._path_for(method)
        result = self._post(path, payload, headers={"Authorization": self._auth_header})
        if isinstance(result, dict):
            return result.get("result")
        return result


@dataclass(frozen=True)
class PaletteVariant:
    suffix: str
    capacity_kg: int
    thickness_mm: int
    cost_price: Decimal
    list_price: Decimal


VARIANTS: tuple[PaletteVariant, ...] = (
    PaletteVariant("EUR 1200x800 mm", 1500, 22, Decimal("12.50"), Decimal("22.00")),
    PaletteVariant("Américaine 48x40 po", 1800, 25, Decimal("14.80"), Decimal("26.50")),
    PaletteVariant("Lourde 1300x1100 mm", 2200, 30, Decimal("19.20"), Decimal("34.90")),
    PaletteVariant("Ultra sèche 1200x800 mm", 1200, 20, Decimal("16.10"), Decimal("28.00")),
    PaletteVariant("Bloc recyclé 1000x1000 mm", 1600, 23, Decimal("10.75"), Decimal("19.60")),
)


def find_uom(client: TrytonRPCClient, hint: str) -> Dict[str, Any]:
    extra_hints = [hint] if hint else []
    extra_hints.extend(["Unité", "Unit", "Unités", "Unidad"])
    seen = set()
    for term in extra_hints:
        key = term.lower()
        if key in seen:
            continue
        seen.add(key)
        domain = [["name", "ilike", term]]
        ids = client.call(
            "model.product.uom.search",
            [domain, 0, 1, None, client.context],
        )
        if ids:
            records = client.call(
                "model.product.uom.read",
                [ids, ["id", "name", "symbol"], client.context],
            )
            if records:
                return records[0]
    raise JsonRpcError(
        "Aucune unité de mesure trouvée. Ajuster PALETTE_UOM_NAME_HINT pour pointer vers une unité existante."
    )


def ensure_category(client: TrytonRPCClient, name: str) -> int:
    domain = [["name", "=", name]]
    existing_ids = client.call(
        "model.product.category.search",
        [domain, 0, 1, None, client.context],
    )
    if existing_ids:
        return int(existing_ids[0])
    created = client.call(
        "model.product.category.create",
        [[{"name": name}], client.context],
    )
    return int(created[0])


def fetch_existing_templates(
    client: TrytonRPCClient, codes: List[str]
) -> dict[str, dict[str, Any]]:
    if not codes:
        return {}
    domain = [["code", "in", codes]]
    ids = client.call(
        "model.product.template.search",
        [domain, 0, None, None, client.context],
    )
    if not ids:
        return {}
    records = client.call(
        "model.product.template.read",
        [ids, ["code", "products"], client.context],
    )
    mapping: dict[str, dict[str, Any]] = {}
    for record in records or []:
        code = record.get("code")
        if not code:
            continue
        mapping[code] = {
            "id": record["id"],
            "has_products": bool(record.get("products")),
        }
    return mapping


def build_records(
    total: int,
    base_name: str,
    code_prefix: str,
    category_id: int,
    uom_id: int,
) -> List[dict[str, Any]]:
    records: List[dict[str, Any]] = []
    for index in range(1, total + 1):
        variant = VARIANTS[(index - 1) % len(VARIANTS)]
        code = f"{code_prefix}-{index:03d}"
        label = f"{base_name} {variant.suffix}"
        records.append(
            {
                "name": label,
                "code": code,
                "type": "goods",
                "salable": True,
                "purchasable": True,
                "default_uom": uom_id,
                "sale_uom": uom_id,
                "purchase_uom": uom_id,
                "categories": [("add", [category_id])],
                "products": [("create", [{}])],
            }
        )
    return records


def create_palettes(
    client: TrytonRPCClient,
    records: List[dict[str, Any]],
) -> tuple[int, int, int]:
    codes = [record["code"] for record in records]
    existing_map = fetch_existing_templates(client, codes)
    to_create = [record for record in records if record["code"] not in existing_map]
    created_ids: list[int] = []
    if to_create:
        created_ids = client.call(
            "model.product.template.create",
            [to_create, client.context],
        )
    patched = 0
    missing_variants = [
        info["id"] for info in existing_map.values() if not info["has_products"]
    ]
    if missing_variants:
        for template_id in missing_variants:
            client.call(
                "model.product.template.write",
                [[template_id], {"products": [("create", [{}])]}, client.context],
            )
        patched = len(missing_variants)
    return len(created_ids), len(existing_map), patched


def main() -> int:
    url = os.environ.get("TRYTON_URL", "http://tryton:8000/")
    database = os.environ.get("TRYTON_DATABASE", "tryton")
    user = os.environ.get("TRYTON_USER", "admin")
    password = os.environ.get("TRYTON_PASSWORD", "admin")

    total = int(os.environ.get("PALETTE_PRODUCT_COUNT", "100"))
    code_prefix = os.environ.get("PALETTE_CODE_PREFIX", "PAL").upper()
    base_name = os.environ.get("PALETTE_BASE_NAME", "Palette de bois")
    category_name = os.environ.get("PALETTE_CATEGORY_NAME", "Palettes de tests")
    uom_hint = os.environ.get("PALETTE_UOM_NAME_HINT", "Unité")

    client = TrytonRPCClient(url, database, user, password)
    try:
        client.login()
        uom = find_uom(client, uom_hint)
        category_id = ensure_category(client, category_name)
        records = build_records(total, base_name, code_prefix, category_id, uom["id"])
        created, skipped, patched = create_palettes(client, records)
    except (ValueError, JsonRpcError) as exc:
        print(f"[ERREUR] {exc}", file=sys.stderr)
        return 1

    print(
        f"{created} palette(s) créée(s). "
        f"{skipped} code(s) déjà présent(s) ont été ignorés. "
        + (
            f"{patched} gabarit(s) existant(s) ont reçu une variante produit."
            if patched
            else ""
        )
        + " "
        f"Catégorie : '{category_name}', UoM : '{uom['name']}'."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
