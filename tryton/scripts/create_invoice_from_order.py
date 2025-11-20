#!/usr/bin/env python3
"""Convert a Tryton sale order into a draft customer invoice.

Usage (depuis la racine du projet) :
    docker compose run --rm tryton python3 tryton/scripts/create_invoice_from_order.py \
        --email martcot@gmail.com [--sale-id 5]

Le script s'appuie sur Proteus pour interagir directement avec Tryton.
Il crée (ou met à jour) les prérequis minimaux côté comptabilité
(comptes par défaut, catégorie produit, journal) puis génère une
facture à l'état « Brouillon » pour l'utilisateur ciblé.
"""

from __future__ import annotations

import argparse
import os
from datetime import date
from decimal import Decimal
from typing import Optional

from proteus import config, Model


def bootstrap_tryton() -> None:
    database = os.environ.get("TRYTON_DATABASE", "tryton")
    config_file = os.environ.get("TRYTON_CONFIG", "/etc/tryton/trytond.conf")
    config.set_trytond(database=database, config_file=config_file)


def find_party(email: str):
    Party = Model.get("party.party")
    parties = Party.find([("contact_mechanisms.value", "=", email.strip().lower())])
    if not parties:
        raise RuntimeError(f"Aucun client avec le courriel {email} dans Tryton.")
    return parties[0]


def select_sale(party, sale_id: Optional[int]):
    Sale = Model.get("sale.sale")
    domain = [("party", "=", party.id)]
    if sale_id is not None:
        domain.append(("id", "=", sale_id))
    sales = Sale.find(domain, order=[("id", "DESC")])
    if not sales:
        raise RuntimeError("Aucune commande associée à ce client.")
    return sales[0]


def ensure_party_accounts(party):
    if party.account_receivable and party.account_payable:
        return
    Account = Model.get("account.account")
    updates = False
    if not party.account_receivable:
        receivables = Account.find([("type.receivable", "=", True)], limit=1)
        if not receivables:
            raise RuntimeError("Aucun compte clients (receivable) n'est défini.")
        party.account_receivable = receivables[0]
        updates = True
    if not party.account_payable:
        payables = Account.find([("type.payable", "=", True)], limit=1)
        if payables:
            party.account_payable = payables[0]
            updates = True
    if updates:
        party.save()


def ensure_category_accounts(category):
    Account = Model.get("account.account")
    changed = False
    if not category.accounting:
        category.accounting = True
        changed = True
    if not category.account_revenue:
        revenue = Account.find([("type.revenue", "=", True)], limit=1)
        if not revenue:
            raise RuntimeError("Aucun compte de revenus n'est disponible.")
        category.account_revenue = revenue[0]
        changed = True
    if not category.account_expense:
        expense = Account.find([("type.expense", "=", True)], limit=1)
        if expense:
            category.account_expense = expense[0]
            changed = True
    if changed:
        category.save()


def ensure_product_category(product):
    template = product.template
    if template and template.categories:
        category = template.categories[0]
        ensure_category_accounts(category)
        if template.account_category != category:
            template.account_category = category
            template.save()


def pick_revenue_journal():
    Journal = Model.get("account.journal")
    journals = Journal.find([("type", "=", "revenue")], limit=1)
    if not journals:
        raise RuntimeError("Aucun journal de type 'revenue' n'est configuré.")
    return journals[0]


def build_invoice(party, sale):
    Invoice = Model.get("account.invoice")
    invoice = Invoice()
    invoice.type = "out"
    invoice.company = sale.company
    invoice.currency = sale.currency
    invoice.party = party
    invoice.invoice_address = sale.invoice_address or (party.addresses and party.addresses[0])
    if not invoice.invoice_address:
        raise RuntimeError("Le client n'a aucune adresse pour la facturation.")
    invoice.account = party.account_receivable
    invoice.journal = pick_revenue_journal()
    invoice.invoice_date = date.today()
    for sale_line in sale.lines:
        if not sale_line.product:
            continue
        ensure_product_category(sale_line.product)
        line = invoice.lines.new()
        line.product = sale_line.product
        line.account = line.product.account_category.account_revenue
        line.quantity = Decimal(sale_line.quantity or 0)
        line.unit = sale_line.unit
        line.unit_price = Decimal(sale_line.unit_price or 0)
        line.description = sale_line.description or sale_line.product.rec_name
    if not invoice.lines:
        raise RuntimeError("La commande ne contient aucune ligne facturable.")
    return invoice


def parse_args():
    parser = argparse.ArgumentParser(description="Créer une facture à partir d'une commande Tryton")
    parser.add_argument("--email", required=True, help="Courriel du client (party)")
    parser.add_argument("--sale-id", type=int, help="Identifiant de la commande à facturer")
    return parser.parse_args()


def main():
    args = parse_args()
    bootstrap_tryton()
    party = find_party(args.email)
    ensure_party_accounts(party)
    sale = select_sale(party, args.sale_id)
    invoice = build_invoice(party, sale)
    invoice.save()
    print(
        f"Facture {invoice.id} créée pour {party.rec_name} à partir de la commande #{sale.id} (montant {invoice.total_amount} {invoice.currency.code})."
    )


if __name__ == "__main__":
    main()
