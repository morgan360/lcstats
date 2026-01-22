/**
 * Dynamic student filtering for Homework Assignment admin
 * When a class is selected, automatically populate the students field
 * with all students from the selected classes.
 *
 * This works with Django's filter_horizontal widget which creates
 * two select boxes ("from" and "to") with move buttons.
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
         * Works with Django's filter_horizontal widget
         */
        function updateStudentsFromClasses() {
            // For filter_horizontal, the "to" box is id_assigned_classes_to
            var $classesToBox = $('#id_assigned_classes_to');

            if (!$classesToBox.length) {
                console.log('Classes "to" box not found');
                return;
            }

            // Get selected class IDs from the "to" box (these are the chosen classes)
            var selectedClasses = [];
            $classesToBox.find('option').each(function() {
                selectedClasses.push($(this).val());
            });

            console.log('Selected classes:', selectedClasses);

            if (selectedClasses.length === 0) {
                console.log('No classes selected');
                return;
            }

            // Collect all student IDs from selected classes
            var allStudentIds = new Set();
            var classesProcessed = 0;

            selectedClasses.forEach(function(classId) {
                getStudentsForClass(classId, function(students) {
                    students.forEach(function(studentId) {
                        allStudentIds.add(String(studentId));
                    });

                    classesProcessed++;

                    // Once all classes are processed, update the students field
                    if (classesProcessed === selectedClasses.length) {
                        moveStudentsToChosenBox(allStudentIds);
                    }
                });
            });
        }

        /**
         * Move students to the "chosen" (to) box in the filter_horizontal widget
         */
        function moveStudentsToChosenBox(studentIds) {
            var $studentsFromBox = $('#id_assigned_students_from');
            var $studentsToBox = $('#id_assigned_students_to');

            if (!$studentsFromBox.length || !$studentsToBox.length) {
                console.log('Student filter_horizontal boxes not found');
                return;
            }

            var movedCount = 0;

            // For each student ID, find it in the "from" box and move it to "to" box
            studentIds.forEach(function(studentId) {
                // Check if already in "to" box
                if ($studentsToBox.find('option[value="' + studentId + '"]').length > 0) {
                    return; // Already selected
                }

                // Find in "from" box
                var $option = $studentsFromBox.find('option[value="' + studentId + '"]');
                if ($option.length > 0) {
                    // Move to "to" box
                    $option.remove();
                    $studentsToBox.append($option);
                    movedCount++;
                }
            });

            console.log('Moved', movedCount, 'students to chosen box');

            // Sort the "to" box options
            var options = $studentsToBox.find('option').toArray();
            options.sort(function(a, b) {
                return $(a).text().localeCompare($(b).text());
            });
            $studentsToBox.empty().append(options);

            // Show a message to the user
            if (movedCount > 0) {
                showMessage('Added ' + movedCount + ' student(s) from selected class(es)');
            }
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

            // Add a button to manually trigger the update
            // Insert it near the assigned_classes field
            var $classesRow = $('.field-assigned_classes');
            if ($classesRow.length) {
                var $updateButton = $(
                    '<div style="margin-top: 10px;">' +
                    '<button type="button" id="update-students-from-classes" ' +
                    'class="button" style="cursor: pointer;">' +
                    '📥 Add Students from Selected Classes</button>' +
                    '</div>'
                );

                $classesRow.append($updateButton);

                $('#update-students-from-classes').on('click', function(e) {
                    e.preventDefault();
                    console.log('Button clicked - updating students from classes');
                    updateStudentsFromClasses();
                });
            }

            // Also trigger automatically when classes change
            // Watch for clicks on the "choose" arrow (moves items to "to" box)
            $(document).on('click', '#id_assigned_classes_add_link, #id_assigned_classes_remove_link', function() {
                console.log('Class selection changed');
                // Wait a moment for the DOM to update
                setTimeout(updateStudentsFromClasses, 100);
            });
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