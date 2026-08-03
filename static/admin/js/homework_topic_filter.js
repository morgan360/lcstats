// Live-filters the homework task inline dropdowns (sections, exam questions,
// QuickKicks, flashcard sets) by the topic selected on the assignment form,
// so the assignment can be created in a single save. Content already assigned
// to the ticked class(es) is marked "✓ assigned before".
(function () {
    'use strict';

    var FIELDS = ['section', 'exam_question', 'quickkick', 'flashcard_set'];
    var cachedOptions = null;

    function selectedTopic() {
        var topicSelect = document.getElementById('id_topic');
        return topicSelect ? topicSelect.value : '';
    }

    function checkedClassIds() {
        var boxes = document.querySelectorAll('input[name="assigned_classes"]:checked');
        return Array.prototype.map.call(boxes, function (b) { return b.value; });
    }

    function populateSelect(select, options) {
        var current = select.value;
        select.innerHTML = '';
        select.add(new Option('---------', ''));
        options.forEach(function (opt) {
            select.add(new Option(opt.label, opt.id));
        });
        var stillValid = options.some(function (opt) {
            return String(opt.id) === current;
        });
        if (stillValid) {
            select.value = current;
        }
    }

    function applyToAll(root) {
        if (!cachedOptions) return;
        FIELDS.forEach(function (field) {
            var selects = (root || document).querySelectorAll('select[name$="-' + field + '"]');
            selects.forEach(function (select) {
                populateSelect(select, cachedOptions[field] || []);
            });
        });
    }

    function refresh(root) {
        var topicId = selectedTopic();
        if (!topicId) {
            cachedOptions = null;
            return;
        }
        var url = '/homework/api/topic-content/' + topicId + '/';
        var classIds = checkedClassIds();
        if (classIds.length) {
            url += '?classes=' + classIds.join(',');
        }
        fetch(url, { credentials: 'same-origin' })
            .then(function (resp) { return resp.json(); })
            .then(function (data) {
                cachedOptions = data;
                applyToAll(root || document);
            })
            .catch(function (err) {
                console.error('Failed to load topic content options:', err);
            });
    }

    function init() {
        var topicSelect = document.getElementById('id_topic');
        if (!topicSelect) return;

        topicSelect.addEventListener('change', function () { refresh(); });

        // Re-fetch when class ticks change, so "assigned before" marks update
        document.addEventListener('change', function (event) {
            if (event.target && event.target.name === 'assigned_classes') {
                refresh();
            }
        });

        // Newly added inline rows ("Add another ...") get the cached options
        document.addEventListener('formset:added', function (event) {
            if (cachedOptions && event.target) {
                applyToAll(event.target);
            }
        });

        // On an existing assignment the topic is preselected — fetch marks now
        if (topicSelect.value) {
            refresh();
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
