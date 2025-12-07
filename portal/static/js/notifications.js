/**
 * ITF Notification System
 * Wrapper autour de Notyf pour les notifications toast
 */
(function () {
    'use strict';

    // Configuration Notyf
    const notyf = new Notyf({
        duration: 5000,
        dismissible: true,
        position: { x: 'right', y: 'top' },
        ripple: false,
        types: [
            {
                type: 'success',
                background: 'linear-gradient(135deg, #2d5a27, #4a7c59)',
                icon: {
                    className: 'notyf-icon-success',
                    tagName: 'span',
                    text: '✓'
                }
            },
            {
                type: 'error',
                duration: 8000,
                background: 'linear-gradient(135deg, #c1121f, #dc3545)',
                icon: {
                    className: 'notyf-icon-error',
                    tagName: 'span',
                    text: '!'
                }
            },
            {
                type: 'warning',
                duration: 6000,
                background: 'linear-gradient(135deg, #cc8a00, #ffc107)',
                icon: {
                    className: 'notyf-icon-warning',
                    tagName: 'span',
                    text: '⚠'
                }
            },
            {
                type: 'info',
                background: 'linear-gradient(135deg, #0b5394, #2196f3)',
                icon: {
                    className: 'notyf-icon-info',
                    tagName: 'span',
                    text: 'ℹ'
                }
            }
        ]
    });

    // Mapping des level_tag Django vers Notyf
    const levelMap = {
        'success': 'success',
        'info': 'info',
        'warning': 'warning',
        'error': 'error',
        'debug': 'info'  // Debug traité comme info
    };

    /**
     * Affiche une notification toast
     * @param {string} level - success|info|warning|error
     * @param {string} message - Le message à afficher
     */
    function show(level, message) {
        const type = levelMap[level] || 'info';
        notyf.open({ type, message });
    }

    /**
     * Affiche une notification de succès
     */
    function success(message) {
        notyf.success(message);
    }

    /**
     * Affiche une notification d'erreur
     */
    function error(message) {
        notyf.error(message);
    }

    /**
     * Ferme toutes les notifications actives
     */
    function dismissAll() {
        notyf.dismissAll();
    }

    // Exposer l'API globalement
    window.ITFNotify = {
        show,
        success,
        error,
        dismissAll,
        instance: notyf
    };
})();
