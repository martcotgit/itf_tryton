#!/usr/bin/env python3
"""
Met à jour les prix de vente dans Tryton via Proteus.

Exécution :
    docker compose run --rm tryton python3 /opt/trytond/scripts/update_product_prices.py

Variables d'environnement :
    TRYTON_CONFIG        Chemin du fichier trytond.conf (défaut : /etc/tryton/trytond.conf)
    TRYTON_DATABASE      Base à utiliser (défaut : tryton)
    TRYTON_USER          Identifiant (défaut : admin)
    TRYTON_PASSWORD      Mot de passe (défaut : admin)
    DEFAULT_LIST_PRICE   Prix par défaut (défaut : 25.00)
"""

from __future__ import annotations

import os
from decimal import Decimal

from proteus import Model, config

PRICE_TABLE = {
    "PAL-001": Decimal("22.00"),
    "PAL-002": Decimal("25.00"),
    "PAL-003": Decimal("34.90"),
    "PAL-004": Decimal("28.00"),
    "PAL-005": Decimal("19.60"),
}


def decimal_from_env(name: str, default: str) -> Decimal:
    raw = os.environ.get(name, default)
    try:
        return Decimal(str(raw))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Valeur invalide pour {name}: {raw}") from exc


def configure():
    cfg_file = os.environ.get("TRYTON_CONFIG", "/etc/tryton/trytond.conf")
    database = os.environ.get("TRYTON_DATABASE", "tryton")
    user = os.environ.get("TRYTON_USER", "admin")
    config.set_trytond(database=database, user=user, config_file=cfg_file)


def determine_price(code: str | None, default_price: Decimal) -> Decimal | None:
    if code and code in PRICE_TABLE:
        return PRICE_TABLE[code]
    if default_price:
        return default_price
    return None


def update_prices(default_price: Decimal) -> tuple[int, int]:
    Template = Model.get("product.template")
    templates = Template.find([("salable", "=", True)])
    template_updates = 0
    variant_updates = 0
    for template in templates:
        target = determine_price(template.code, default_price)
        if not target:
            continue
        needs_update = template.list_price in (None, Decimal("0"))
        if needs_update:
            template.list_price = target
            template_updates += 1
        dirty = False
        for variant in template.products:
            if variant.list_price in (None, Decimal("0")):
                variant.list_price = target
                variant.save()
                dirty = True
                variant_updates += 1
        if needs_update:
            template.save()
    return template_updates, variant_updates


def main() -> None:
    configure()
    default_price = decimal_from_env("DEFAULT_LIST_PRICE", "25.00")
    tpl_count, var_count = update_prices(default_price)
    print(f"{tpl_count} gabarit(s) mis à jour.")
    print(f"{var_count} variante(s) mises à jour.")


if __name__ == "__main__":
    main()
