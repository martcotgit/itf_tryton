---
trigger: always_on
---

# Design System

Un système de design minimaliste et strict pour assurer la cohérence visuelle et technique de l'interface utilisateur.

## 1. Palette de Couleurs (Globale)

Les couleurs doivent être utilisées strictement selon les variables CSS définies.

*   **Primary**: `#2d5016` (Variable: `--brand-primary` / `--primary-color`)
    *   *Usage*: Boutons principaux, liens actifs, états de focus, éléments de marque.
*   **Secondary / Accents**: `#4a7c59` (Variable: `--secondary-color`)
    *   *Usage*: Éléments secondaires, survel de boutons, décorations.
*   **Backgrounds**:
    *   **Page**: `#fafaf9` (Variable: `--background-page` / `--gray-50`) - Teinte chaude très légère ("Stone 50").
    *   **Cards**: `#ffffff` (Variable: `--background-card` / `--white`)
*   **Text**:
    *   **Body / Main**: `#1c1917` (Variable: `--text-main` / `--gray-900`)
    *   **Headings**: Utilisent la couleur Body, parfois `#2d5016` pour emphase majeure.
    *   **Muted**: `#57534e` (Variable: `--text-secondary` / `--gray-600`) - Pour textes d'aide et métadonnées.

## 2. Typographie

*   **Font Family**: `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`
*   **Scale**:
    *   **H1**: `32px` (3.5rem pour Hero)
    *   **H2**: `2rem` (32px)
    *   **H3**: `1.35rem` (21.6px)
    *   **Body**: `15px` (`--text-base`) ou `1rem` (16px) pour le texte standard.

## 3. Composants UI (Règles strictes)

### Boutons (`.btn`)
*   **Radius**: `10px` (`--radius-md`)
*   **Padding**: `0.75rem 2rem` (Vertical 12px, Horizontal 32px)
*   **Shadow**:
    *   **Défaut**: `0 1px 2px 0 rgba(0, 0, 0, 0.05)` (`--shadow-button`)
    *   **Hover**: `0 4px 12px 0 rgba(45, 80, 22, 0.2)` (`--shadow-button-hover`)
*   **Transition**: `transform: translateY(-2px)` au survol.

### Cartes (Containers) (`.card`, `.action-card`)
*   **Radius**: `16px` (`--radius-lg` / `--radius-card`)
*   **Border**: `1px solid rgba(0, 0, 0, 0.04)` ou `1px solid rgba(127, 140, 141, 0.15)` pour cartes produit.
    *   *Règle*: Privilégier une bordure très subtile ou nulle avec une ombre.
*   **Shadow**:
    *   **Défaut**: `0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 1px 2px -1px rgba(0, 0, 0, 0.02)` (`--shadow-card`)
    *   **Hover**: `0 4px 6px -1px rgba(0, 0, 0, 0.06), 0 2px 4px -2px rgba(0, 0, 0, 0.04)` (`--shadow-card-hover`)

### Inputs (`.form-input`)
*   **Radius**: `10px`
*   **Border**: `1.5px solid #dfe3e8`
*   **Background**: `#fafbfc` (Défaut), `#ffffff` (Hover/Focus)
*   **Focus State**:
    *   **Border**: `--primary-color` (`#2d5016`)
    *   **Shadow (Ring)**: `0 0 0 4px rgba(45, 90, 39, 0.12)`

## 4. Patterns UX (Règles de navigation)

*   **Fil d'ariane (Breadcrumbs)**:
    *   Toujours utiliser un fil d'ariane pour les pages profondes (> 1 niveau).
    *   Style: Pillule (`rounded-full`), fond translucide ou simple texte gris avec séparateurs.
*   **Actions Principales**:
    *   Les actions primaires (ex: "Nouvelle commande", "Enregistrer") doivent être situées en haut à droite des conteneurs ou des pages (Header de section).
    *   Utiliser la classe `.btn-primary` pour l'action principale unique par vue.
*   **Retour Utilisateur**:
    *   Utiliser des "Toasts" (Notyf) pour les confirmations d'action (Succès, Erreur), jamais de simples `alert()`.
