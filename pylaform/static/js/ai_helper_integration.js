// static/js/ai_helper_integration.js
function openAiHelper(fieldId, improvementType) {
    const text = document.getElementById(fieldId).value;

    // Call the openAiHelper function defined in the ai_helper.html script
    if (window.openAiHelper) {
        window.openAiHelper(fieldId, improvementType);
    }
}
