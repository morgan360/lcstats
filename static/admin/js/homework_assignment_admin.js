/**
 * Dynamic student filtering for Homework Assignment admin
 * When a class is selected, automatically populate the students field
 * with all students from the selected classes.
 */
(function() {
    'use strict';

    console.log('Homework assignment admin JS loaded');

    function initHomeworkAssignment() {
        // Use django.jQuery if available, otherwise try window.jQuery
        var $ = window.django && window.django.jQuery || window.jQuery;

        if (!$) {
            console.error('jQuery not found, retrying in 100ms');
            setTimeout(initHomeworkAssignment, 100);
            return;
        }

        console.log('jQuery found, initializing homework assignment admin');

        // Cache of class -> students mapping (fetched via AJAX)
        var classStudentsCache = {};

        /**
         * Get students for a given class ID
         */
        function getStudentsForClass(classId, callback) {
            if (classStudentsCache[classId]) {
                // Return cached data
                callback(classStudentsCache[classId]);
                return;
            }

            // Fetch from server
            $.ajax({
                url: '/homework/api/class-students/' + classId + '/',
                method: 'GET',
                success: function(data) {
                    classStudentsCache[classId] = data.students || [];
                    callback(classStudentsCache[classId]);
                },
                error: function(xhr, status, error) {
                    console.error('Failed to fetch students for class', classId, error);
                    callback([]);
                }
            });
        }

        /**
         * Update the students field based on selected classes
         */
        function updateStudentsFromClasses() {
            var $classesField = $('#id_assigned_classes');
            var $studentsField = $('#id_assigned_students');

            if (!$classesField.length || !$studentsField.length) {
                console.log('Class or student fields not found');
                return;
            }

            var selectedClasses = $classesField.val() || [];
            console.log('Selected classes:', selectedClasses);

            if (selectedClasses.length === 0) {
                // No classes selected, don't modify students
                return;
            }

            // Collect all student IDs from selected classes
            var allStudentIds = new Set();
            var classesProcessed = 0;

            selectedClasses.forEach(function(classId) {
                getStudentsForClass(classId, function(students) {
                    students.forEach(function(studentId) {
                        allStudentIds.add(studentId);
                    });

                    classesProcessed++;

                    // Once all classes are processed, update the students field
                    if (classesProcessed === selectedClasses.length) {
                        updateStudentsField(allStudentIds);
                    }
                });
            });
        }

        /**
         * Update the students select field with the given student IDs
         */
        function updateStudentsField(studentIds) {
            var $studentsField = $('#id_assigned_students');

            // Get current selected students
            var currentlySelected = new Set($studentsField.val() || []);

            // Add new students from classes (preserving manually selected ones)
            studentIds.forEach(function(id) {
                currentlySelected.add(String(id));
            });

            // Update the field
            $studentsField.val(Array.from(currentlySelected));

            // Trigger change event to update UI (for select2 or other plugins)
            $studentsField.trigger('change');

            console.log('Updated students field with', currentlySelected.size, 'students');

            // Show a message to the user
            showMessage('Added students from selected classes');
        }

        /**
         * Show a temporary message to the user
         */
        function showMessage(text) {
            var $messagesDiv = $('.messagelist');
            if (!$messagesDiv.length) {
                $messagesDiv = $('<ul class="messagelist"></ul>');
                $('.breadcrumbs').after($messagesDiv);
            }

            var $message = $('<li class="info">' + text + '</li>');
            $messagesDiv.append($message);

            // Remove after 3 seconds
            setTimeout(function() {
                $message.fadeOut(function() {
                    $(this).remove();
                });
            }, 3000);
        }

        // Initialize on DOM ready
        $(document).ready(function() {
            console.log('DOM ready, setting up homework assignment handlers');

            // Listen for changes to the assigned_classes field
            $(document).on('change', '#id_assigned_classes', function() {
                console.log('Assigned classes changed');
                updateStudentsFromClasses();
            });

            // Alternative: Add a button to manually trigger the update
            var $classesField = $('#id_assigned_classes');
            if ($classesField.length) {
                var $updateButton = $(
                    '<button type="button" id="update-students-from-classes" ' +
                    'style="margin-left: 10px; padding: 5px 10px; cursor: pointer;">' +
                    'Add Students from Selected Classes</button>'
                );

                $classesField.closest('.form-row').find('.help').before($updateButton);

                $updateButton.on('click', function(e) {
                    e.preventDefault();
                    updateStudentsFromClasses();
                });
            }
        });
    }

    // Start initialization when DOM is loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initHomeworkAssignment);
    } else {
        // DOM already loaded
        initHomeworkAssignment();
    }

})();