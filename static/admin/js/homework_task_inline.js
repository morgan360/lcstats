(function($) {
    'use strict';

    console.log('Homework task inline JS loaded');

    // Function to update field visibility based on task type for stacked inlines
    function updateTaskFieldVisibility(inline) {
        var $inline = $(inline);
        var taskTypeSelect = $inline.find('select[id$="-task_type"]');
        var taskType = taskTypeSelect.val();

        console.log('Updating task type:', taskType, 'for inline:', $inline);

        // Remove all task-type classes
        $inline.removeClass('task-type-section task-type-exam_question task-type-quickkick task-type-flashcard');

        // Add class based on current selection
        if (taskType) {
            $inline.addClass('task-type-' + taskType);
            console.log('Added class: task-type-' + taskType);
        }

        // Clear values for hidden fields to prevent validation errors
        if (taskType !== 'section') {
            $inline.find('select[id$="-section"]').val('');
        }
        if (taskType !== 'exam_question') {
            $inline.find('select[id$="-exam_question"]').val('');
        }
        if (taskType !== 'quickkick') {
            $inline.find('select[id$="-quickkick"]').val('');
        }
        if (taskType !== 'flashcard') {
            $inline.find('select[id$="-flashcard_set"]').val('');
        }
    }

    // Initialize on page load
    $(document).ready(function() {
        console.log('DOM ready, initializing homework tasks');

        // Process existing inline forms
        var inlines = $('#homework_tasks-group .inline-related');
        console.log('Found', inlines.length, 'inline forms');

        inlines.each(function() {
            updateTaskFieldVisibility(this);
        });

        // Handle changes to task type dropdown
        $(document).on('change', 'select[id*="homework_tasks"][id$="-task_type"]', function() {
            console.log('Task type changed');
            var inline = $(this).closest('.inline-related');
            updateTaskFieldVisibility(inline);
        });
    });

    // Handle dynamically added inlines (when clicking "Add another Homework Task")
    $(document).on('formset:added', function(event, $row, formsetName) {
        console.log('Formset added:', formsetName);
        if (formsetName === 'homework_tasks') {
            updateTaskFieldVisibility($row);
        }
    });

})(django.jQuery);