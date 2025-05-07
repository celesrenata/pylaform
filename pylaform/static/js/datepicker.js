/**
 * Date picker initialization and utility functions for Pylaform
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all date pickers
    initDatePickers();

    // Add click handler for "Set Present" buttons
    document.querySelectorAll('.set-present-btn').forEach(function(button) {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const inputField = document.getElementById(targetId);
            const hiddenField = document.getElementById(targetId + '_actual');

            if (inputField) {
                // Set the display value to "Present"
                inputField.value = 'Present';
            }

            if (hiddenField) {
                // Set the hidden value to 9999-01-01 for database
                hiddenField.value = '9999-01-01';
            }
        });
    });

    // Toggle date picker on icon click
    document.querySelectorAll('.date-picker-toggle').forEach(function(toggle) {
        toggle.addEventListener('click', function() {
            const input = this.previousElementSibling;
            if (input && input.classList.contains('datepicker')) {
                input.focus();
            }
        });
    });
});

/**
 * Initialize all date pickers with appropriate formatting
 */
function initDatePickers() {
    // Make sure flatpickr is available
    if (typeof flatpickr !== 'function') {
        console.error('Flatpickr library not loaded');
        return;
    }

    // Initialize all date picker elements
    document.querySelectorAll('.datepicker').forEach(function(element) {
        const withTime = element.getAttribute('data-with-time') === 'true';
        const includePresent = element.getAttribute('data-include-present') === 'true';
        const dateFormat = withTime ? 'Y-m-d H:i' : 'Y-m-d';
        const id = element.id;

        // Check if this is a year-only field
        const isYearOnly = id && (id.includes('_year') || id.endsWith('year'));

        // Check for "Present" value
        if (element.value === 'Present') {
            const hiddenField = document.getElementById(id + '_actual');
            if (hiddenField) {
                hiddenField.value = '9999-01-01';
            }
        }

        // Different configuration based on field type
        if (isYearOnly) {
            // Year picker configuration
            flatpickr(element, {
                dateFormat: 'Y',
                allowInput: true,
                static: true,
                plugins: [
                    new YearSelectPlugin({
                        step: 1,
                        formatYear: (year) => year
                    })
                ],
                onChange: function(selectedDates, dateStr) {
                    if (selectedDates.length > 0) {
                        // Format for database: YYYY-01-01
                        const formattedDate = `${dateStr}-01-01`;
                        const hiddenField = document.getElementById(id + '_actual');
                        if (hiddenField) {
                            hiddenField.value = formattedDate;
                        }
                    }
                }
            });
        } else {
            // Regular date picker configuration
            flatpickr(element, {
                dateFormat: dateFormat,
                allowInput: true,
                static: true,
                enableTime: withTime,
                time_24hr: true,
                onChange: function(selectedDates, dateStr) {
                    if (selectedDates.length > 0) {
                        const date = selectedDates[0];

                        // Update hidden field with YYYY-MM-DD format for database
                        const formattedDate = formatDateYMD(date);
                        const hiddenField = document.getElementById(id + '_actual');
                        if (hiddenField) {
                            hiddenField.value = formattedDate;
                        }

                        // Update display format for education dates (MM/YYYY)
                        if (id && (id.includes('_startdate') || id.includes('_enddate'))) {
                            const month = date.getMonth() + 1;
                            const year = date.getFullYear();
                            element.value = `${month.toString().padStart(2, '0')}/${year}`;
                        }
                    }
                }
            });
        }
    });
}

/**
 * Format a date in YYYY-MM-DD format for database storage
 * @param {Date} date - The date to format
 * @returns {string} - Formatted date string
 */
function formatDateYMD(date) {
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    return `${year}-${month}-${day}`;
}