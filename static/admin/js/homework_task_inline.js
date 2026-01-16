(function($) {
    'use strict';

    // Function to update table headers based on visible task types
    function updateTableHeaders() {
        var $table = $('#homework_tasks-group .tabular');
        var $headers = $table.find('thead th');

        // Remove all show-* classes from headers
        $headers.removeClass('show-section show-exam_question show-quickkick show-flashcard_set');

        // Check which task types are currently visible in any row
        var visibleTypes = {
            section: false,
            exam_question: false,
            quickkick: false,
            flashcard_set: false
        };

        $table.find('tbody tr:not(.empty-form)').each(function() {
            var $row = $(this);
            if ($row.hasClass('task-type-section')) visibleTypes.section = true;
            if ($row.hasClass('task-type-exam_question')) visibleTypes.exam_question = true;
            if ($row.hasClass('task-type-quickkick')) visibleTypes.quickkick = true;
            if ($row.hasClass('task-type-flashcard')) visibleTypes.flashcard_set = true;
        });

        // Show headers for visible task types
        if (visibleTypes.section) {
            $headers.filter('.column-section').addClass('show-section');
        }
        if (visibleTypes.exam_question) {
            $headers.filter('.column-exam_question').addClass('show-exam_question');
        }
        if (visibleTypes.quickkick) {
            $headers.filter('.column-quickkick').addClass('show-quickkick');
        }
        if (visibleTypes.flashcard_set) {
            $headers.filter('.column-flashcard_set').addClass('show-flashcard_set');
        }
    }

    // Function to update field visibility based on task type
    function updateTaskFieldVisibility(row) {
        var taskTypeSelect = row.find('select[id$="-task_type"]');
        var taskType = taskTypeSelect.val();

        // Remove all task-type classes
        row.removeClass('task-type-section task-type-exam_question task-type-quickkick task-type-flashcard');

        // Add class based on current selection
        if (taskType) {
            row.addClass('task-type-' + taskType);
        }

        // Also clear values for hidden fields to prevent validation errors
        if (taskType !== 'section') {
            row.find('select[id$="-section"]').val('');
        }
        if (taskType !== 'exam_question') {
            row.find('select[id$="-exam_question"]').val('');
        }
        if (taskType !== 'quickkick') {
            row.find('select[id$="-quickkick"]').val('');
        }
        if (taskType !== 'flashcard') {
            row.find('select[id$="-flashcard_set"]').val('');
        }

        // Update table headers
        updateTableHeaders();
    }

    // Initialize on page load
    $(document).ready(function() {
        // Process existing rows
        $('#homework_tasks-group .tabular tbody tr').each(function() {
            var row = $(this);
            if (!row.hasClass('empty-form')) {
                updateTaskFieldVisibility(row);
            }
        });

        // Update headers after processing all rows
        updateTableHeaders();

        // Handle changes to task type dropdown
        $(document).on('change', 'select[id*="homework_tasks"][id$="-task_type"]', function() {
            var row = $(this).closest('tr');
            updateTaskFieldVisibility(row);
        });
    });

    // Handle dynamically added rows (when clicking "Add another Homework Task")
    $(document).on('formset:added', function(event, $row, formsetName) {
        if (formsetName === 'homework_tasks') {
            updateTaskFieldVisibility($row);
        }
    });

})(django.jQuery);