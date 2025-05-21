// summary.js - Handles summary page specific functionality
document.addEventListener('DOMContentLoaded', function() {
    console.log('Summary.js loaded');

    // Handle delete button clicks - this will override the inline handler
    document.addEventListener('click', function(e) {
        if (e.target.closest('.delete-summary')) {
            e.preventDefault();
            const button = e.target.closest('.delete-summary');
            const id = button.getAttribute('data-id');
            console.log('Delete button clicked for ID:', id);

            if (!id) {
                console.error('No summary ID found');
                return;
            }

            const card = button.closest('.card.summary-item');

            if (confirm('Are you sure you want to delete this summary item?')) {
                // For existing items (with UUID), submit the form with delete parameter
                if (id.length === 36) { // UUID length is 36
                    console.log('Submitting delete for existing item:', id);

                    // Create a form specifically for deletion to avoid conflicts
                    const deleteForm = document.createElement('form');
                    deleteForm.method = 'POST';
                    deleteForm.action = window.location.pathname; // Current URL
                    deleteForm.style.display = 'none';

                    // Add the ID to be deleted
                    const deleteInput = document.createElement('input');
                    deleteInput.type = 'hidden';
                    deleteInput.name = '_delete';
                    deleteInput.value = id;
                    deleteForm.appendChild(deleteInput);

                    // Add the active resume ID if available
                    const activeResumeInput = document.querySelector('input[name="active_resume_id"]');
                    if (activeResumeInput) {
                        const resumeInput = document.createElement('input');
                        resumeInput.type = 'hidden';
                        resumeInput.name = 'active_resume_id';
                        resumeInput.value = activeResumeInput.value;
                        deleteForm.appendChild(resumeInput);
                    }

                    // Add CSRF token if needed
                    const csrfToken = document.querySelector('meta[name="csrf-token"]');
                    if (csrfToken) {
                        const csrfInput = document.createElement('input');
                        csrfInput.type = 'hidden';
                        csrfInput.name = 'csrf_token';
                        csrfInput.value = csrfToken.getAttribute('content');
                        deleteForm.appendChild(csrfInput);
                    }

                    // Append form to body and submit
                    document.body.appendChild(deleteForm);
                    console.log('Submitting delete form');
                    deleteForm.submit();
                } else {
                    // For new items that haven't been saved yet, just remove from DOM
                    console.log('Removing unsaved item from DOM');
                    if (card) {
                        card.remove();
                    }
                }
            }
        }
    });
});