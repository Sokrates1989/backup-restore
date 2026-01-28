/**
 * Module: multi-select.js
 * Author: Engaige Assistant
 * Date: 2026-01-23
 * Version: 1.0.0
 *
 * Description:
 *     Shared multi-select dropdown helpers for UI tabs (history, backup files).
 *
 * Dependencies:
 *     - None
 *
 * Usage:
 *     Include via <script src="multi-select.js"></script> before tab scripts.
 */

/**
 * Get selected values from a checkbox filter group.
 *
 * @param {string} name Checkbox input name attribute.
 * @returns {string[]} Array of selected values.
 */
function getCheckedFilterValues(name) {
    const checkboxes = document.querySelectorAll(`input[name="${name}"]:checked`);
    return Array.from(checkboxes).map(cb => cb.value);
}

/**
 * Update the display text for a multiselect dropdown based on checked values.
 *
 * @param {string} dropdownId Dropdown container id.
 * @param {string} checkboxName Checkbox input name attribute.
 * @param {string} allText Text to show when nothing is selected.
 * @returns {void}
 */
function updateMultiselectDisplay(dropdownId, checkboxName, allText) {
    const dropdown = document.getElementById(dropdownId);
    if (!dropdown) return;

    const display = dropdown.querySelector('.multiselect-display');
    if (!display) return;

    const checked = document.querySelectorAll(`input[name="${checkboxName}"]:checked`);
    if (checked.length === 0) {
        display.textContent = allText;
        display.classList.add('placeholder');
    } else {
        const labels = Array.from(checked).map(cb => {
            const option = cb.closest('.multiselect-option');
            const span = option ? option.querySelector('span') : null;
            return span ? span.textContent.trim() : cb.value;
        });
        display.textContent = labels.join(', ');
        display.classList.remove('placeholder');
    }
}

/**
 * Toggle a multi-select dropdown open/closed.
 *
 * @param {HTMLElement} dropdown Dropdown container element.
 * @returns {void}
 */
function toggleMultiselectDropdown(dropdown) {
    const wasOpen = dropdown.classList.contains('open');

    // Close all other dropdowns
    document.querySelectorAll('.multiselect-dropdown.open').forEach(d => {
        d.classList.remove('open');
    });

    // Toggle this one
    if (!wasOpen) {
        dropdown.classList.add('open');
    }
}

/**
 * Initialize multi-select dropdown behavior for all dropdowns.
 *
 * @returns {void}
 */
function initMultiselectDropdowns() {
    // Handle trigger clicks
    document.querySelectorAll('.multiselect-trigger').forEach(trigger => {
        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            const dropdown = trigger.closest('.multiselect-dropdown');
            if (dropdown) toggleMultiselectDropdown(dropdown);
        });

        // Handle keyboard navigation
        trigger.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                const dropdown = trigger.closest('.multiselect-dropdown');
                if (dropdown) toggleMultiselectDropdown(dropdown);
            }
        });
    });

    // Handle checkbox changes inside dropdowns
    document.querySelectorAll('.multiselect-options').forEach(options => {
        options.addEventListener('change', (e) => {
            if (!(e.target instanceof HTMLInputElement) || e.target.type !== 'checkbox') return;

            const dropdown = options.closest('.multiselect-dropdown');
            if (!dropdown) return;

            const checkboxName = e.target.name;
            const allText = dropdown.id.includes('database') ? 'All Databases' :
                dropdown.id.includes('operation') ? 'All Operations' :
                dropdown.id.includes('trigger') ? 'All Triggers' :
                dropdown.id.includes('storage') ? 'All Locations (Local + Remote)' : 'All';

            updateMultiselectDisplay(dropdown.id, checkboxName, allText);

            // Call appropriate render function based on context
            if (dropdown.id.includes('history')) {
                if (typeof renderHistory === 'function') {
                    renderHistory();
                }
            } else if (dropdown.id.includes('backup-files')) {
                if (typeof loadBackupFiles === 'function') {
                    loadBackupFiles();
                }
            }
        });

        // Handle clicks on the option div to toggle checkbox
        options.addEventListener('click', (e) => {
            const option = e.target.closest('.multiselect-option');
            if (!option) return;

            // If clicking directly on the checkbox, prevent dropdown from closing
            if (e.target.type === 'checkbox') {
                e.stopPropagation();
                return;
            }

            // If clicking on the option (text or background), toggle the checkbox
            const checkbox = option.querySelector('input[type="checkbox"]');
            if (checkbox) {
                checkbox.checked = !checkbox.checked;
                checkbox.dispatchEvent(new Event('change', { bubbles: true }));
            }
            e.stopPropagation();
        });
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', () => {
        document.querySelectorAll('.multiselect-dropdown.open').forEach(d => {
            d.classList.remove('open');
        });
    });
}

window.getCheckedFilterValues = getCheckedFilterValues;
window.updateMultiselectDisplay = updateMultiselectDisplay;
window.toggleMultiselectDropdown = toggleMultiselectDropdown;
window.initMultiselectDropdowns = initMultiselectDropdowns;
