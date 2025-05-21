// skills.js - Completely revised
document.addEventListener('DOMContentLoaded', function() {
    // Create a map of employer IDs to position IDs from the data passed from the server
    const employerPositionsMap = typeof employerPositionsMap !== 'undefined' ?
        employerPositionsMap : {};

    // Handle category dropdown changes
    $("body").on("change", "[id$='_category_dropdown']", function() {
        const selectedValue = $(this).val();
        const rowId = this.id.split('_')[0];
        const categoryDiv = $(`#${rowId}_category_div`);

        if (selectedValue === 'EDIT' || selectedValue === 'ADD') {
            categoryDiv.removeClass('d-none');
        } else {
            categoryDiv.addClass('d-none');
            // Store the selected text in the hidden input
            $(`#${rowId}_category`).val($(this).find("option:selected").text());
        }
    });

    // Handle subcategory dropdown changes
    $("body").on("change", "[id$='_subcategory_dropdown']", function() {
        const selectedValue = $(this).val();
        const rowId = this.id.split('_')[0];
        const subcategoryDiv = $(`#${rowId}_subcategory_div`);

        if (selectedValue === 'EDIT' || selectedValue === 'ADD') {
            subcategoryDiv.removeClass('d-none');
        } else {
            subcategoryDiv.addClass('d-none');
            // Store the selected text in the hidden input
            $(`#${rowId}_subcategory`).val($(this).find("option:selected").text());
        }
    });

    // Handle employer dropdown changes to filter position options
    $("body").on("change", "[id$='_employer_dropdown']", function() {
        const employerId = $(this).val();
        const rowId = this.id.split('_')[0];
        const positionDropdown = $(`#${rowId}_position_dropdown`);

        // Store the selected employer in the hidden field
        $(`#${rowId}_employer`).val($(this).find("option:selected").text());

        // Reset position dropdown first
        positionDropdown.val('');

        // If no employer is selected, disable the position dropdown
        if (!employerId || employerId === 'EDIT' || employerId === 'ADD') {
            positionDropdown.prop('disabled', true);
            return;
        }

        // Enable position dropdown
        positionDropdown.prop('disabled', false);

        // Filter positions based on the employer-position mapping
        const validPositionIds = employerPositionsMap[employerId] || [];

        positionDropdown.find("option").each(function() {
            const positionId = $(this).val();

            // Always show EDIT/ADD options
            if(positionId === 'EDIT' || positionId === 'ADD' || positionId === '') {
                $(this).show();
                return;
            }

            // Only show positions that belong to the selected employer
            if (validPositionIds.includes(parseInt(positionId))) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    });

    // Handle position dropdown changes
    $("body").on("change", "[id$='_position_dropdown']", function() {
        const rowId = this.id.split('_')[0];
        // Store the selected position in the hidden field
        $(`#${rowId}_position`).val($(this).find("option:selected").text());
    });

    // Initialize all dropdowns when the page loads
    $(document).ready(function() {
        // Initialize category and subcategory dropdowns
        $("[id$='_category_dropdown']").each(function() {
            $(this).trigger("change");
        });

        $("[id$='_subcategory_dropdown']").each(function() {
            $(this).trigger("change");
        });

        // Initialize employer-position relationships
        $("[id$='_employer_dropdown']").each(function() {
            $(this).trigger("change");
        });
    });

    // Add new skill row
    $("#rowAdder").click(function() {
        let clicks = 0;
        if (window.skillClicks) {
            window.skillClicks++;
            clicks = window.skillClicks;
        } else {
            window.skillClicks = 1;
            clicks = 1;
        }

        // Your existing row adding code
        newRowAdd = templateString.replace(/new/g, "new" + clicks);
        $('#newinput').append(newRowAdd);

        // Initialize dropdowns for the new row
        const newRowId = "new" + clicks;
        $(`#${newRowId}_category_dropdown`).trigger("change");
        $(`#${newRowId}_subcategory_dropdown`).trigger("change");
        $(`#${newRowId}_employer_dropdown`).trigger("change");

        // Smooth scroll to the new element
        const newestElement = $('#newinput').children().last()[0];
        if (newestElement) {
            newestElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    });

    // Handle deletion
    $("body").on("click", "#deleteRow", function() {
        const div_id = $(this).closest("div.card").attr("id");
        if (confirm("Are you sure you want to delete this skill?")) {
            $("#" + div_id).fadeOut(300, function() {
                $(this).remove();
                $("#skillsForm").append(`<input type="hidden" name="_delete" value="${div_id}">`);
            });
        }
    });
});
