(function () {
    const DEFAULT_SUMMARY = "Aucun produit n’est sélectionné.";
    const SELECTED_PREFIX = "Produit sélectionné : ";

    function debounce(fn, delay) {
        let timer = null;
        return function debounced(...args) {
            window.clearTimeout(timer);
            timer = window.setTimeout(() => fn.apply(this, args), delay);
        };
    }

    document.addEventListener('DOMContentLoaded', () => {
        const overlay = document.querySelector('[data-product-catalog]');
        if (!overlay) {
            return;
        }

        document.body.classList.add('product-picker-enabled');

        const catalogUrl = overlay.dataset.catalogUrl;
        const panel = overlay.querySelector('.catalog-panel');
        const resultsContainer = overlay.querySelector('[data-catalog-results]');
        const emptyState = overlay.querySelector('[data-catalog-empty]');
        const paginationContainer = overlay.querySelector('[data-catalog-pagination]');
        const statusEl = overlay.querySelector('[data-catalog-status]');
        const searchInput = overlay.querySelector('[data-catalog-search]');
        const unitFilter = overlay.querySelector('[data-catalog-unit-filter]');
        const resetButton = overlay.querySelector('[data-catalog-reset]');
        const template = overlay.querySelector('[data-catalog-item-template]');
        let activeField = null;
        let lastTrigger = null;
        let isErrorVisible = false;
        let fetchController = null;
        const state = {
            page: 1,
            pageSize: 8,
            query: '',
            unit: '',
        };

        function showStatus(message, variant = 'info') {
            if (!statusEl) {
                return;
            }
            isErrorVisible = variant === 'error';
            if (!message) {
                statusEl.hidden = true;
                statusEl.textContent = '';
                statusEl.classList.remove('is-error');
                return;
            }
            statusEl.hidden = false;
            statusEl.textContent = message;
            statusEl.classList.toggle('is-error', variant === 'error');
        }

        function setLoading(isLoading) {
            overlay.classList.toggle('is-loading', Boolean(isLoading));
            if (isLoading) {
                showStatus('Chargement du catalogue…');
            } else if (!isErrorVisible) {
                showStatus('');
            }
        }

        function refreshResetState() {
            if (!resetButton) {
                return;
            }
            const disabled = !state.query && !state.unit;
            resetButton.disabled = disabled;
            resetButton.setAttribute('aria-disabled', String(disabled));
        }

        function openPanel(field, trigger) {
            if (!catalogUrl || !panel) {
                return;
            }
            activeField = field;
            lastTrigger = trigger || null;
            overlay.classList.add('is-visible');
            overlay.removeAttribute('aria-hidden');
            document.body.classList.add('catalog-open');
            if (searchInput) {
                searchInput.value = state.query;
            }
            if (unitFilter) {
                unitFilter.value = state.unit;
            }
            panel.focus();
            loadProducts();
        }

        function closePanel({shouldReturnFocus = true} = {}) {
            overlay.classList.remove('is-visible');
            overlay.setAttribute('aria-hidden', 'true');
            document.body.classList.remove('catalog-open');
            if (shouldReturnFocus && lastTrigger && typeof lastTrigger.focus === 'function') {
                lastTrigger.focus();
            }
            activeField = null;
        }

        function handleOverlayClick(event) {
            if (event.target === overlay) {
                closePanel();
            }
        }

        function handleKeydown(event) {
            if (event.key === 'Escape' && overlay.classList.contains('is-visible')) {
                event.preventDefault();
                closePanel();
            }
        }

        function buildSummaryText(label) {
            if (!label) {
                return DEFAULT_SUMMARY;
            }
            return `${SELECTED_PREFIX}${label}`;
        }

        function updateSelectionSummary(field, providedLabel) {
            const summary = field.querySelector('[data-product-selection]');
            if (!summary) {
                return;
            }
            let label = providedLabel || '';
            if (!label) {
                const select = field.querySelector('[data-product-select]');
                if (select && select.selectedOptions.length) {
                    label = select.selectedOptions[0].textContent.trim();
                }
            }
            summary.textContent = buildSummaryText(label);
            summary.classList.toggle('is-empty', !label);
        }

        function syncSelectionSummaries() {
            document.querySelectorAll('[data-product-field]').forEach((field) => {
                updateSelectionSummary(field);
            });
        }

        function renderResults(data) {
            if (!resultsContainer || !emptyState) {
                return;
            }
            resultsContainer.innerHTML = '';
            const items = data && Array.isArray(data.results) ? data.results : [];
            if (!items.length) {
                emptyState.hidden = false;
                return;
            }
            emptyState.hidden = true;
            items.forEach((item) => {
                let element;
                if (template && template.content && template.content.firstElementChild) {
                    element = template.content.firstElementChild.cloneNode(true);
                } else {
                    element = document.createElement('article');
                }
                element.classList.add('catalog-card');
                element.dataset.productId = String(item.id);
                const nameEl = element.querySelector('[data-product-name]');
                const codeEl = element.querySelector('[data-product-code]');
                const unitEl = element.querySelector('[data-product-unit]');
                const summaryEl = element.querySelector('[data-product-summary]');
                const button = element.querySelector('[data-catalog-select]');
                if (nameEl) {
                    nameEl.textContent = item.name || 'Produit';
                }
                if (codeEl) {
                    codeEl.textContent = item.code ? `Code : ${item.code}` : 'Code non disponible';
                }
                if (unitEl) {
                    unitEl.textContent = item.unit_name || 'Sans unité';
                }
                if (summaryEl) {
                    summaryEl.textContent = item.summary || '';
                }
                if (button) {
                    button.dataset.productId = String(item.id);
                    button.dataset.productLabel = item.choice_label || item.name || '';
                }
                resultsContainer.appendChild(element);
            });
        }

        function updateFilters(filters) {
            if (!unitFilter) {
                return;
            }
            const options = filters && Array.isArray(filters.unit) ? filters.unit : [];
            const currentValue = state.unit;
            unitFilter.innerHTML = '<option value="">Toutes les unités</option>';
            options.forEach((option) => {
                const opt = document.createElement('option');
                const label = option.label || 'Sans unité';
                const count = typeof option.count === 'number' ? option.count : 0;
                opt.value = option.value || '';
                opt.textContent = `${label} (${count})`;
                unitFilter.appendChild(opt);
            });
            if (currentValue && unitFilter.querySelector(`option[value="${currentValue}"]`)) {
                unitFilter.value = currentValue;
            } else if (!currentValue) {
                unitFilter.value = '';
            } else {
                state.unit = '';
                unitFilter.value = '';
            }
            refreshResetState();
        }

        function updatePagination(pagination) {
            if (!paginationContainer) {
                return;
            }
            paginationContainer.innerHTML = '';
            if (!pagination || pagination.pages <= 1) {
                return;
            }
            const info = document.createElement('p');
            info.className = 'catalog-pagination-info';
            info.textContent = `Page ${pagination.page} sur ${pagination.pages}`;
            paginationContainer.appendChild(info);

            const controls = document.createElement('div');
            controls.className = 'catalog-pagination-actions';
            if (pagination.has_previous) {
                const prev = document.createElement('button');
                prev.type = 'button';
                prev.className = 'btn btn-secondary';
                prev.textContent = 'Précédent';
                prev.dataset.pageTarget = String(pagination.page - 1);
                controls.appendChild(prev);
            }
            if (pagination.has_next) {
                const next = document.createElement('button');
                next.type = 'button';
                next.className = 'btn btn-primary';
                next.textContent = 'Suivant';
                next.dataset.pageTarget = String(pagination.page + 1);
                controls.appendChild(next);
            }
            paginationContainer.appendChild(controls);
        }

        function loadProducts() {
            if (!catalogUrl) {
                return;
            }
            const params = new URLSearchParams();
            params.set('page', state.page);
            params.set('page_size', state.pageSize);
            if (state.query) {
                params.set('q', state.query);
            }
            if (state.unit) {
                params.set('unit', state.unit);
            }
            setLoading(true);
            if (fetchController) {
                fetchController.abort();
            }
            fetchController = new AbortController();
            fetch(`${catalogUrl}?${params.toString()}`, {signal: fetchController.signal})
                .then((response) => response
                    .json()
                    .catch(() => ({}))
                    .then((data) => ({ok: response.ok, data})))
                .then(({ok, data}) => {
                    if (!ok) {
                        const message = data && data.error ? data.error : 'Catalogue temporairement indisponible.';
                        throw new Error(message);
                    }
                    const pagination = data && data.pagination ? data.pagination : null;
                    state.page = pagination && pagination.page ? pagination.page : 1;
                    renderResults(data || {});
                    updateFilters(data && data.filters ? data.filters : null);
                    updatePagination(pagination);
                    showStatus('');
                })
                .catch((error) => {
                    if (error.name === 'AbortError') {
                        return;
                    }
                    showStatus(error.message || 'Lecture du catalogue impossible.', 'error');
                })
                .finally(() => {
                    setLoading(false);
                });
        }

        const scheduleSearch = debounce((value) => {
            state.query = value.trim();
            state.page = 1;
            loadProducts();
            refreshResetState();
        }, 300);

        if (searchInput) {
            searchInput.addEventListener('input', (event) => {
                scheduleSearch(event.target.value || '');
            });
        }

        if (unitFilter) {
            unitFilter.addEventListener('change', (event) => {
                state.unit = event.target.value || '';
                state.page = 1;
                loadProducts();
                refreshResetState();
            });
        }

        if (resetButton) {
            resetButton.addEventListener('click', () => {
                state.query = '';
                state.unit = '';
                state.page = 1;
                if (searchInput) {
                    searchInput.value = '';
                }
                if (unitFilter) {
                    unitFilter.value = '';
                }
                loadProducts();
                refreshResetState();
            });
        }

        overlay.addEventListener('click', (event) => {
            const selectButton = event.target.closest('[data-catalog-select]');
            if (selectButton) {
                event.preventDefault();
                const productId = selectButton.dataset.productId;
                if (productId && activeField) {
                    applySelection(productId, selectButton.dataset.productLabel || '');
                }
                return;
            }
            const paginationTrigger = event.target.closest('[data-page-target]');
            if (paginationTrigger) {
                event.preventDefault();
                const targetPage = parseInt(paginationTrigger.dataset.pageTarget, 10);
                if (!Number.isNaN(targetPage)) {
                    state.page = targetPage;
                    loadProducts();
                }
                return;
            }
        });

        overlay.addEventListener('click', handleOverlayClick);
        document.addEventListener('keydown', handleKeydown);
        overlay.querySelectorAll('[data-catalog-close]').forEach((button) => {
            button.addEventListener('click', () => closePanel());
        });

        document.addEventListener('click', (event) => {
            const trigger = event.target.closest('[data-product-catalog-trigger]');
            if (!trigger) {
                return;
            }
            const field = trigger.closest('[data-product-field]');
            if (!field) {
                return;
            }
            event.preventDefault();
            openPanel(field, trigger);
        });

        function applySelection(productId, label) {
            if (!activeField) {
                return;
            }
            const select = activeField.querySelector('[data-product-select]');
            if (!select) {
                return;
            }
            const value = String(productId);
            let option = Array.from(select.options).find((opt) => opt.value === value);
            if (!option) {
                option = new Option(label || `Produit #${value}`, value, true, true);
                select.add(option);
            }
            select.value = value;
            select.dispatchEvent(new Event('change', {bubbles: true}));
            updateSelectionSummary(activeField, label || option.textContent.trim());
            closePanel({shouldReturnFocus: false});
            focusNextField(activeField);
        }

        function focusNextField(field) {
            const row = field.closest('[data-formset-row]');
            if (!row) {
                return;
            }
            const quantityInput = row.querySelector('input[type="number"]');
            if (quantityInput) {
                quantityInput.focus();
            }
        }

        document.addEventListener('change', (event) => {
            const select = event.target.closest('[data-product-select]');
            if (!select) {
                return;
            }
            const field = select.closest('[data-product-field]');
            if (field) {
                updateSelectionSummary(field);
            }
        });

        syncSelectionSummaries();
        refreshResetState();
    });
})();
