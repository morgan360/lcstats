(function($) {
    'use strict';

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