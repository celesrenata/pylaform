/**
 * AI Helper Integration
 * This script connects the modal-based AI helper UI with the footer-based implementation
 */

// Store a reference to the original openAiHelper function
window.originalOpenAiHelper = window.openAiHelper;

// Override the openAiHelper function to work with both implementations
function openAiHelper(fieldId, improvementType, textContent) {
    // Use the textContent parameter as needed
    const text = textContent || document.getElementById(fieldId).value;
    const field = document.getElementById(fieldId);
    if (!field) return;

    const content = field.value.trim();

    // Check if we're using the modal implementation
    const aiHelperModal = document.getElementById('aiHelperModal');
    if (aiHelperModal) {
        // Modal implementation
        // Set the content in the input field
        const aiInputField = document.getElementById('ai-text-input');
        if (aiInputField) {
            aiInputField.value = content;
        }

        // Set the content type
        const aiContentTypeField = document.getElementById('ai-content-type');
        if (aiContentTypeField) {
            aiContentTypeField.value = improvementType;
        }

        // Set the target field ID to update after improvement
        const aiTargetField = document.getElementById('ai-target-field');
        if (aiTargetField) {
            aiTargetField.value = fieldId;
        }

        // Select the appropriate improvement type option
        const aiOptions = document.querySelectorAll('.ai-helper-option');
        aiOptions.forEach(option => {
            if (option.dataset.type === improvementType) {
                option.click(); // Trigger the click event to select this option
            }
        });

        // Show the modal
        const modal = new bootstrap.Modal(aiHelperModal);
        modal.show();
    } else {
        // Footer implementation
        // Check if the original function exists and call it
        if (window.originalOpenAiHelper) {
            window.originalOpenAiHelper(fieldId, improvementType, text);
        } else {
            // Fallback to basic footer implementation
            const aiHelper = document.querySelector('.ai-helper-footer');
            if (aiHelper) {
                // Expand the footer
                aiHelper.classList.add('expanded');

                // Set the text in the input field
                const aiTextInput = document.getElementById('ai-text-input');
                if (aiTextInput) {
                    aiTextInput.value = content;
                }

                // Select the appropriate option
                const aiOptions = document.querySelectorAll('.ai-helper-option');
                aiOptions.forEach(option => {
                    option.classList.remove('active');
                    if (option.dataset.type === improvementType) {
                        option.classList.add('active');
                    }
                });

                // Store the target field ID in a data attribute
                const aiSubmitBtn = document.getElementById('ai-submit');
                if (aiSubmitBtn) {
                    aiSubmitBtn.dataset.targetField = fieldId;
                    aiSubmitBtn.disabled = false;
                }
            }
        }
    }
};

// Add event listener to apply the AI suggestion to the target field
document.addEventListener('DOMContentLoaded', function() {
    const aiApplyBtn = document.getElementById('ai-apply-btn');
    if (aiApplyBtn) {
        aiApplyBtn.addEventListener('click', function() {
            const targetFieldId = document.getElementById('ai-target-field').value;
            const resultContent = document.getElementById('ai-result-content');

            if (targetFieldId && resultContent && resultContent.textContent.trim()) {
                const targetField = document.getElementById(targetFieldId);
                if (targetField) {
                    targetField.value = resultContent.textContent.trim();

                    // Close the modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('aiHelperModal'));
                    if (modal) {
                        modal.hide();
                    }
                }
            }
        });
    }
});