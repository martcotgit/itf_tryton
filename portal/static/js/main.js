// Attendre que le DOM soit chargé
document.addEventListener('DOMContentLoaded', function() {
    // Initialiser les animations d'intersection observer
    initIntersectionObserver();
    
    // Initialiser les animations au scroll
    initScrollAnimations();
    
    // Initialiser les interactions du logo
    initLogoInteractions();
});

// Intersection Observer pour les animations au scroll
function initIntersectionObserver() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    // Observer les éléments à animer
    const animatedElements = document.querySelectorAll('.service-card, .contact-item');
    animatedElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
}



// Animations au scroll
function initScrollAnimations() {
    let ticking = false;
    
    function updateAnimations() {
        const scrolled = window.pageYOffset;
        const parallaxElements = document.querySelectorAll('.hero::before');
        
        parallaxElements.forEach(element => {
            const speed = 0.5;
            element.style.transform = `translateY(${scrolled * speed}px)`;
        });
        
        ticking = false;
    }
    
    function requestTick() {
        if (!ticking) {
            requestAnimationFrame(updateAnimations);
            ticking = true;
        }
    }
    
    window.addEventListener('scroll', requestTick);
}

// Interactions du logo
function initLogoInteractions() {
    const logo = document.querySelector('.logo');
    const recycleSymbol = document.querySelector('.recycle-symbol');
    
    if (!logo || !recycleSymbol) return;
    
    // Animation au hover
    logo.addEventListener('mouseenter', () => {
        recycleSymbol.style.animationDuration = '2s';
    });
    
    logo.addEventListener('mouseleave', () => {
        recycleSymbol.style.animationDuration = '10s';
    });
    
    // Animation au clic
    logo.addEventListener('click', () => {
        recycleSymbol.style.animationDuration = '0.5s';
        setTimeout(() => {
            recycleSymbol.style.animationDuration = '10s';
        }, 500);
    });
}

// Fonctions de navigation
function scrollToServices() {
    const servicesSection = document.getElementById('services');
    if (servicesSection) {
        servicesSection.scrollIntoView({ 
            behavior: 'smooth',
            block: 'start'
        });
    }
}

// Exposer les fonctions globalement pour les boutons HTML
window.scrollToServices = scrollToServices;

// Animation des cartes de service au hover
document.addEventListener('DOMContentLoaded', function() {
    const serviceCards = document.querySelectorAll('.service-card');
    
    serviceCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
});

// Optimisation des performances
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Gestion du redimensionnement de fenêtre
const handleResize = debounce(() => {
    // Recalculer les animations si nécessaire
    const animatedElements = document.querySelectorAll('.service-card, .contact-item');
    animatedElements.forEach(el => {
        el.style.opacity = '1';
        el.style.transform = 'translateY(0)';
    });
}, 250);

window.addEventListener('resize', handleResize); 