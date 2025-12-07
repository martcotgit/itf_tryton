document.addEventListener('DOMContentLoaded', function () {
    const passwordInput = document.getElementById('id_password1');
    const helpText = document.querySelector('#id_password1').parentElement.querySelector('.field-help');

    // Create a feedback element if it doesn't already exist or use the help text
    let feedbackElement = helpText;
    if (!feedbackElement) {
        feedbackElement = document.createElement('p');
        feedbackElement.className = 'field-help';
        passwordInput.parentElement.appendChild(feedbackElement);
    }

    // Store original help text
    const originalHelpText = feedbackElement.textContent;


    passwordInput.addEventListener('input', function () {
        const password = passwordInput.value;

        // Rules
        const minLength = 8;
        const hasLower = /[a-z]/.test(password);
        const hasUpper = /[A-Z]/.test(password);
        const hasDigit = /\d/.test(password);
        const hasSymbol = /[^a-zA-Z0-9]/.test(password);

        const typeCount = [hasLower, hasUpper, hasDigit, hasSymbol].filter(Boolean).length;

        // Validation logic
        if (password.length === 0) {
            feedbackElement.textContent = originalHelpText;
            feedbackElement.classList.remove('text-success', 'text-error');
            passwordInput.classList.remove('input-success', 'input-error');
            return;
        }

        const lengthValid = password.length >= minLength;
        const typesValid = typeCount >= 3;

        if (lengthValid && typesValid) {
            feedbackElement.textContent = "Mot de passe valide.";
            feedbackElement.classList.remove('text-error');
            feedbackElement.classList.add('text-success'); // Assuming you have or will add this class style
            passwordInput.classList.remove('input-error');
            passwordInput.classList.add('input-success');
            passwordInput.setCustomValidity("");
        } else {
            let message = "Mot de passe insuffisant : ";
            if (!lengthValid) message += ` ${password.length}/${minLength} caractères.`;
            if (!typesValid) message += ` ${typeCount}/3 catégories requises.`;

            feedbackElement.textContent = message;
            feedbackElement.classList.remove('text-success');
            feedbackElement.classList.add('text-error'); // Assuming you have or will add this class style
            passwordInput.classList.remove('input-success');
            passwordInput.classList.add('input-error');
            passwordInput.setCustomValidity("Le mot de passe ne respecte pas les critères de sécurité.");
        }
    });

    // --- Phone Validation ---
    const phoneInput = document.getElementById('id_phone');
    if (phoneInput) {
        // Create feedback element parent if not existing (it might not have help text)
        let phoneFeedback = phoneInput.parentElement.querySelector('.field-help');
        if (!phoneFeedback) {
            phoneFeedback = document.createElement('p');
            phoneFeedback.className = 'field-help';
            phoneInput.parentElement.appendChild(phoneFeedback);
        }
        const originalPhoneHelp = phoneFeedback.textContent;

        phoneInput.addEventListener('input', function () {
            const val = phoneInput.value.trim();
            if (val.length === 0) {
                // Optional field
                phoneFeedback.textContent = originalPhoneHelp;
                phoneFeedback.classList.remove('text-success', 'text-error');
                phoneInput.classList.remove('input-success', 'input-error');
                phoneInput.setCustomValidity("");
                return;
            }

            // Simple check: does it start with +?
            // And does it have enough digits?
            const isInternational = val.startsWith('+');
            const digitCount = (val.match(/\d/g) || []).length;

            if (!isInternational) {
                phoneFeedback.textContent = "Format international requis (ex: +1 418...).";
                phoneFeedback.classList.remove('text-success');
                phoneFeedback.classList.add('text-error');
                phoneInput.classList.remove('input-success');
                phoneInput.classList.add('input-error');
                phoneInput.setCustomValidity("Veuillez inclure l'indicatif pays (ex: +1).");
            } else if (digitCount < 8) {
                phoneFeedback.textContent = "Numéro trop court.";
                phoneFeedback.classList.remove('text-success');
                phoneFeedback.classList.add('text-error');
                phoneInput.classList.remove('input-success');
                phoneInput.classList.add('input-error');
                phoneInput.setCustomValidity("Numéro trop court.");
            } else {
                phoneFeedback.textContent = "Format valide.";
                phoneFeedback.classList.remove('text-error');
                phoneFeedback.classList.add('text-success');
                phoneInput.classList.remove('input-error');
                phoneInput.classList.add('input-success');
                phoneInput.setCustomValidity("");
            }
        });
    }
});

