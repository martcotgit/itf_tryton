def sanitize_error_message(raw_message: str) -> str:
    """Transforme les erreurs techniques Tryton en messages lisibles."""
    # Détecter les patterns d'erreur Tryton
    if "You are not allowed to create records of" in raw_message:
        return "Vous n'avez pas les permissions nécessaires pour effectuer cette action. Contactez le support."
    if "User in companies" in raw_message:
        return "Erreur de configuration de votre compte. Veuillez contacter notre équipe."
    # Fallback
    if len(raw_message) > 200 or "<br>" in raw_message:
        return "Une erreur technique s'est produite. Veuillez réessayer ou contacter le support."
    return raw_message
