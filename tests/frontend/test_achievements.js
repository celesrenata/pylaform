// tests/frontend/achievements.test.js

/**
 * @jest-environment jsdom
 */

// Mock DOM setup for achievements page
document.body.innerHTML = `
<div id="test-row">
    <select id="test-row_employer_dropdown">
        <option value="emp1" data-org-type="employer">Employer 1</option>
        <option value="emp2" data-org-type="employer">Employer 2</option>
        <option value="school1" data-org-type="school">School 1 (College)</option>
    </select>
    <input type="hidden" id="test-row_employer" value="">
    <input type="hidden" id="test-row_employer_type" value="">
    
    <select id="test-row_position_dropdown">
    </select>
    <input type="hidden" id="test-row_position" value="">
    <input type="hidden" id="test-row_position_type" value="">
    
    <button id="deleteRow">Delete</button>
</div>
<div id="newinput"></div>
<button id="rowAdder">ADD</button>
`;

// Mock jQuery
global.$ = require('jquery');
global.jQuery = global.$;

// Mock dropdown data
const ddpayload = {
    employer: [
        { id: 'emp1', name: 'Employer 1', type: 'employer' },
        { id: 'emp2', name: 'Employer 2', type: 'employer' },
        { id: 'school1', name: 'School 1', type: 'school' }
    ],
    position: [
        { id: 'pos1', name: 'Position 1', type: 'position', employer: 'emp1' },
        { id: 'pos2', name: 'Position 2', type: 'position', employer: 'emp1' },
        { id: 'pos3', name: 'Position 3', type: 'position', employer: 'emp2' },
        { id: 'focus1', name: 'Focus 1', type: 'focus', employer: 'school1' }
    ],
    employer_positions: {
        'emp1': ['pos1', 'pos2'],
        'emp2': ['pos3'],
        'school1': ['focus1']
    }
};

// Make ddpayload globally available as it would be in the page
global.ddpayload = ddpayload;

describe('Achievements Page UI Tests', () => {
    let rowAdder;
    let deleteRowBtn;
    let employerDropdown;
    let positionDropdown;

    beforeEach(() => {
        // Initialize elements
        rowAdder = document.getElementById('rowAdder');
        deleteRowBtn = document.getElementById('deleteRow');
        employerDropdown = document.getElementById('test-row_employer_dropdown');
        positionDropdown = document.getElementById('test-row_position_dropdown');

        // Set up click handlers
        rowAdder.addEventListener('click', function() {
            const newRowId = "new" + Math.floor(Math.random() * 1000);
            const newRowHtml = `
                <div id="${newRowId}">
                    <select id="${newRowId}_employer_dropdown">
                        <option value="emp1" data-org-type="employer">Employer 1</option>
                        <option value="emp2" data-org-type="employer">Employer 2</option>
                    </select>
                    <input type="hidden" id="${newRowId}_employer" value="">
                    <input type="hidden" id="${newRowId}_employer_type" value="">
                    
                    <select id="${newRowId}_position_dropdown">
                    </select>
                    <input type="hidden" id="${newRowId}_position" value="">
                    <input type="hidden" id="${newRowId}_position_type" value="">
                    
                    <button id="deleteRow">Delete</button>
                </div>
            `;
            document.getElementById('newinput').innerHTML += newRowHtml;
        });

        // Set up employer dropdown change handler
        $(employerDropdown).on('change', function() {
            const employerId = $(this).val();
            const rowId = this.id.split('_')[0];
            const positionDropdown = $(`#${rowId}_position_dropdown`);

            // Get employer info
            const selectedOption = $(this).find("option:selected");
            const employerName = selectedOption.text();
            const orgType = selectedOption.data("org-type") || "employer";

            // Update hidden fields
            $(`#${rowId}_employer`).val(employerName.replace(" (College)", ""));
            $(`#${rowId}_employer_type`).val(orgType);

            // Clear position dropdown
            positionDropdown.empty();

            // Get positions from ddpayload
            const allPositions = ddpayload.position;

            // Filter positions based on employer
            let matchingPositions = [];
            if (orgType === "school") {
                matchingPositions = allPositions.filter(p =>
                    p.type === "focus" && p.employer == employerId
                );
            } else {
                matchingPositions = allPositions.filter(p =>
                    p.type !== "focus" && p.employer == employerId
                );
            }

            // Add positions to dropdown
            matchingPositions.forEach(pos => {
                $("<option>")
                    .val(pos.id)
                    .text(pos.name + (pos.type === "focus" ? " (Focus)" : ""))
                    .attr("data-role-type", pos.type)
                    .attr("data-employer-id", pos.employer)
                    .appendTo(positionDropdown);
            });
        });

        // Set up position dropdown change handler
        $(positionDropdown).on('change', function() {
            const rowId = this.id.split('_')[0];
            const selectedOption = $(this).find("option:selected");
            const positionName = selectedOption.text();
            const positionType = selectedOption.data("role-type") || "position";

            // Update hidden fields
            $(`#${rowId}_position`).val(positionName.replace(" (Focus)", ""));
            $(`#${rowId}_position_type`).val(positionType);
        });
    });

    test('Employer dropdown updates hidden fields correctly', () => {
        // Select an employer
        $(employerDropdown).val('emp1').trigger('change');

        // Check hidden fields
        expect($('#test-row_employer').val()).toBe('Employer 1');
        expect($('#test-row_employer_type').val()).toBe('employer');

        // Check that position dropdown was populated
        const positionOptions = $(positionDropdown).find('option');
        expect(positionOptions.length).toBeGreaterThan(0);

        // Select a school
        $(employerDropdown).val('school1').trigger('change');

        // Check hidden fields
        expect($('#test-row_employer').val()).toBe('School 1');
        expect($('#test-row_employer_type').val()).toBe('school');
    });

    test('Position dropdown updates hidden fields correctly', () => {
        // First select an employer to populate positions
        $(employerDropdown).val('emp1').trigger('change');

        // Then select a position
        $(positionDropdown).val($(positionDropdown).find('option:first').val()).trigger('change');

        // Check that hidden fields were updated
        expect($('#test-row_position').val()).not.toBe('');
        expect($('#test-row_position_type').val()).toBe('position');
    });

    test('Add button creates a new row', () => {
        // Initial state
        const initialChildCount = $('#newinput').children().length;

        // Click add button
        rowAdder.click();

        // Check that a new row was added
        expect($('#newinput').children().length).toBe(initialChildCount + 1);
    });

    test('Delete button removes the row', () => {
        // Add a row first
        rowAdder.click();

        // Get the newly added row
        const newRow = $('#newinput').children().first();
        const rowId = newRow.attr('id');

        // Initial state
        expect(document.getElementById(rowId)).not.toBeNull();

        // Click delete button
        newRow.find('#deleteRow').click();

        // Check that the row was removed
        expect(document.getElementById(rowId)).toBeNull();
    });
});