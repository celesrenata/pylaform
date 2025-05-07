// tests/frontend/ai_helper.test.js

// Configure Jest environment for browser testing
/**
 * @jest-environment jsdom
 */

// Mock DOM setup
document.body.innerHTML = `
<div class="ai-helper-footer">
    <div class="ai-helper-toggle">
        <div>
            <i class="bi bi-cpu ai-icon"></i>
            <span>AI Resume Helper</span>
        </div>
        <div class="arrow">
            <i class="bi bi-chevron-up"></i>
        </div>
    </div>
    <div class="ai-helper-content">
        <div class="ai-helper-options">
            <div class="ai-helper-option" data-type="tenet">Core Principle/Tenet</div>
            <div class="ai-helper-option" data-type="list">Convert to List</div>
            <div class="ai-helper-option" data-type="sentence_restructure">Restructure Sentence</div>
            <div class="ai-helper-option" data-type="sentence_summarization">Summarize</div>
        </div>
        <div class="form-group ai-helper-input">
            <textarea class="form-control" id="ai-text-input"></textarea>
        </div>
        <button id="ai-submit" class="btn btn-primary" disabled>Improve Text</button>
        <div class="ai-helper-loading" style="display: none;">
            <i class="bi bi-hourglass-split"></i> Processing...
        </div>
        <div class="ai-helper-result" style="display: none;"></div>
    </div>
</div>
`;

// Mock fetch API
global.fetch = jest.fn(() =>
    Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ response: 'Improved text' })
    })
);

// Import the script (in an actual setup, you'd use a module system)
// For testing purposes, we'll mock the script behavior
describe('AI Helper UI Tests', () => {
    let aiToggle;
    let aiHelper;
    let aiOptions;
    let aiTextInput;
    let aiSubmitBtn;
    let aiResultDiv;
    let aiLoadingDiv;

    beforeEach(() => {
        // Initialize DOM elements
        aiToggle = document.querySelector('.ai-helper-toggle');
        aiHelper = document.querySelector('.ai-helper-footer');
        aiOptions = document.querySelectorAll('.ai-helper-option');
        aiTextInput = document.getElementById('ai-text-input');
        aiSubmitBtn = document.getElementById('ai-submit');
        aiResultDiv = document.querySelector('.ai-helper-result');
        aiLoadingDiv = document.querySelector('.ai-helper-loading');

        // Add event listeners (simulating the script)
        aiToggle.addEventListener('click', () => {
            aiHelper.classList.toggle('expanded');
        });

        aiOptions.forEach(option => {
            option.addEventListener('click', function() {
                aiOptions.forEach(o => o.classList.remove('active'));
                this.classList.add('active');

                if (aiTextInput.value.trim()) {
                    aiSubmitBtn.disabled = false;
                }
            });
        });

        aiTextInput.addEventListener('input', function() {
            const hasActiveOption = Array.from(aiOptions).some(opt => opt.classList.contains('active'));
            aiSubmitBtn.disabled = !(this.value.trim() && hasActiveOption);
        });

        aiSubmitBtn.addEventListener('click', function() {
            const text = aiTextInput.value.trim();
            const selectedOption = document.querySelector('.ai-helper-option.active');

            if (!text || !selectedOption) {
                return;
            }

            aiResultDiv.style.display = 'none';
            aiLoadingDiv.style.display = 'block';
            aiSubmitBtn.disabled = true;

            fetch('/api/improve-text', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    text: text,
                    type: selectedOption.dataset.type
                })
            })
            .then(response => response.json())
            .then(data => {
                aiLoadingDiv.style.display = 'none';

                if (data.error) {
                    aiResultDiv.textContent = `Error: ${data.error}`;
                } else {
                    aiResultDiv.textContent = data.response;
                }

                aiResultDiv.style.display = 'block';
                aiSubmitBtn.disabled = false;
            });
        });
    });

    test('AI Helper toggles expanded class on click', () => {
        // Initial state
        expect(aiHelper.classList.contains('expanded')).toBe(false);

        // Click to expand
        aiToggle.click();
        expect(aiHelper.classList.contains('expanded')).toBe(true);

        // Click to collapse
        aiToggle.click();
        expect(aiHelper.classList.contains('expanded')).toBe(false);
    });

    test('Option selection enables submit button when text is present', () => {
        // Initial state
        expect(aiSubmitBtn.disabled).toBe(true);

        // Add text but no option selected
        aiTextInput.value = 'Sample text';
        aiTextInput.dispatchEvent(new Event('input'));
        expect(aiSubmitBtn.disabled).toBe(true);

        // Select an option
        aiOptions[0].click();
        expect(aiSubmitBtn.disabled).toBe(false);

        // Clear text
        aiTextInput.value = '';
        aiTextInput.dispatchEvent(new Event('input'));
        expect(aiSubmitBtn.disabled).toBe(true);
    });

    test('Submit button triggers API call and updates UI', async () => {
        // Setup test scenario
        aiTextInput.value = 'Test content';
        aiTextInput.dispatchEvent(new Event('input'));
        aiOptions[0].click(); // Select first option

        // Initial states
        expect(aiSubmitBtn.disabled).toBe(false);
        expect(aiResultDiv.style.display).toBe('none');

        // Click submit
        aiSubmitBtn.click();

        // Check immediate state changes
        expect(aiLoadingDiv.style.display).toBe('block');
        expect(aiSubmitBtn.disabled).toBe(true);

        // Wait for async operation
        await new Promise(resolve => setTimeout(resolve, 0));

        // Verify API was called with correct data
        expect(global.fetch).toHaveBeenCalledWith(
            '/api/improve-text',
            expect.objectContaining({
                method: 'POST',
                body: JSON.stringify({
                    text: 'Test content',
                    type: 'tenet'
                })
            })
        );

        // Verify final UI state
        expect(aiLoadingDiv.style.display).toBe('none');
        expect(aiResultDiv.style.display).toBe('block');
        expect(aiResultDiv.textContent).toBe('Improved text');
        expect(aiSubmitBtn.disabled).toBe(false);
    });
});