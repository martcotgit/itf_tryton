(function () {
    function initOrderLineFormset(container) {
        const prefix = container.dataset.prefix;
        const maxFormsAttr = container.dataset.maxForms || '';
        const parsedMax = parseInt(maxFormsAttr, 10);
        const maxForms = Number.isNaN(parsedMax) ? Infinity : parsedMax;
        const body = container.querySelector('[data-formset-body]');
        const template = container.querySelector('[data-formset-template]');
        const addButton = container.querySelector('[data-formset-add]');
        const totalFormsInput = prefix
            ? container.querySelector(`input[name="${prefix}-TOTAL_FORMS"]`)
            : null;

        if (!prefix || !body || !template || !addButton || !totalFormsInput) {
            return;
        }

        const nameRegex = new RegExp(`^(${prefix}-)(\\d+|__prefix__)(-.*)$`);
        const idRegex = new RegExp(`^(id_${prefix}-)(\\d+|__prefix__)(-.*)$`);

        const currentRows = () => Array.from(body.querySelectorAll('[data-formset-row]'));

        const focusFirstField = (row) => {
            const field = row.querySelector('select, input[type="text"], input[type="number"], textarea');
            if (field) {
                field.focus();
            }
        };

        const updateLineLabels = () => {
            currentRows().forEach((row, index) => {
                const label = row.querySelector('[data-line-label]');
                if (label) {
                    label.textContent = `Ligne ${index + 1}`;
                }
            });
        };

        const refreshAddState = () => {
            const rowsCount = currentRows().length;
            const shouldDisable = rowsCount >= maxForms;
            addButton.disabled = shouldDisable;
            addButton.setAttribute('aria-disabled', String(shouldDisable));
            addButton.classList.toggle('is-disabled', shouldDisable);
        };

        const renderTemplateRow = () => {
            const html = template.innerHTML.trim();
            if (!html) {
                return null;
            }
            const nextIndex = currentRows().length;
            const rendered = html.replace(/__prefix__/g, nextIndex);
            const wrapper = document.createElement('tbody');
            wrapper.innerHTML = rendered;
            return wrapper.querySelector('[data-formset-row]');
        };

        const syncIndexes = () => {
            const rows = currentRows();
            rows.forEach((row, index) => {
                row.dataset.formsetIndex = index.toString();
                row.querySelectorAll('[name]').forEach((element) => {
                    const name = element.getAttribute('name');
                    if (!name) {
                        return;
                    }
                    const match = name.match(nameRegex);
                    if (match) {
                        element.setAttribute('name', `${match[1]}${index}${match[3]}`);
                    }
                });
                row.querySelectorAll('[id]').forEach((element) => {
                    const idValue = element.getAttribute('id');
                    if (!idValue) {
                        return;
                    }
                    const match = idValue.match(idRegex);
                    if (match) {
                        element.setAttribute('id', `${match[1]}${index}${match[3]}`);
                    }
                });
                row.querySelectorAll('label[for]').forEach((label) => {
                    const target = label.getAttribute('for');
                    if (!target) {
                        return;
                    }
                    const match = target.match(idRegex);
                    if (match) {
                        label.setAttribute('for', `${match[1]}${index}${match[3]}`);
                    }
                });
            });
            totalFormsInput.value = rows.length.toString();
        };

        const addRow = () => {
            if (currentRows().length >= maxForms) {
                return;
            }
            const row = renderTemplateRow();
            if (!row) {
                return;
            }
            body.appendChild(row);
            syncIndexes();
            updateLineLabels();
            refreshAddState();
            focusFirstField(row);
        };

        const removeRow = (row) => {
            row.remove();
            syncIndexes();
            if (currentRows().length === 0) {
                addRow();
                return;
            }
            updateLineLabels();
            refreshAddState();
        };

        addButton.addEventListener('click', (event) => {
            event.preventDefault();
            addRow();
        });

        container.addEventListener('click', (event) => {
            const trigger = event.target.closest('[data-formset-remove]');
            if (!trigger) {
                return;
            }
            event.preventDefault();
            const row = trigger.closest('[data-formset-row]');
            if (row) {
                removeRow(row);
            }
        });

        syncIndexes();
        updateLineLabels();
        refreshAddState();
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('[data-order-line-formset]').forEach((container) => {
            initOrderLineFormset(container);
        });
    });
})();
