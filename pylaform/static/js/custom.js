// Handle form submissions to prevent double clicks
document.addEventListener('DOMContentLoaded', function() {
    setupCareerCustomizeForm();
});

function setupCareerCustomizeForm() {
    // Get the form element
    const customizeForm = document.getElementById('career-customize-form');

    if (customizeForm) {
        // Disable the submit button during processing to prevent double clicks
        customizeForm.addEventListener('submit', function(event) {
            // Show loading indicator
            const submitButton = document.querySelector('#career-customize-form button[type="submit"]');
            const originalButtonText = submitButton.innerHTML;

            // Change button text and disable it
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
            submitButton.disabled = true;

            // Add a hidden field to track submission
            if (!document.getElementById('form-submitted')) {
                const hiddenField = document.createElement('input');
                hiddenField.type = 'hidden';
                hiddenField.id = 'form-submitted';
                hiddenField.name = 'form_submitted';
                hiddenField.value = 'true';
                customizeForm.appendChild(hiddenField);
            }

            // Log submission for debugging
            console.log('Form submitted - processing request');

            // Form will submit normally after this
            // We don't prevent default so the form submits normally

            // Set a timeout to re-enable the button if the request takes too long
            setTimeout(function() {
                if (submitButton.disabled) {
                    submitButton.innerHTML = originalButtonText;
                    submitButton.disabled = false;
                    console.log('Button re-enabled due to timeout');
                }
            }, 30000); // 30 seconds timeout
        });
    }
}