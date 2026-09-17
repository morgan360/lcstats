// Opens the exam question part picker from the assignment form, and takes the
// ticked parts back from it into the "Exam Question Parts" inline.
//
// The picker has to show the questions, which a <select> cannot do, but making
// it save the tasks itself would force the assignment to be saved first - out
// of step with every other task type, which the topic filter lets you set in
// one save. So the picker hands its choices back here instead.
(function () {
    'use strict';

    function partSelects() {
        // The hidden empty-form template matches the same name pattern, so it
        // is filtered out - filling it would stage a row that never submits.
        return Array.prototype.slice.call(
            document.querySelectorAll('select[name$="-exam_question_part"]')
        ).filter(function (select) {
            return select.name.indexOf('__prefix__') === -1;
        });
    }

    function emptySelect() {
        var selects = partSelects();
        for (var i = 0; i < selects.length; i++) {
            if (!selects[i].value) return selects[i];
        }
        return null;
    }

    function addRow() {
        var selects = partSelects();
        if (!selects.length) return null;
        var group = selects[0].closest('.inline-group');
        var link = group && group.querySelector('.add-row a');
        if (!link) return null;
        link.click();
        var after = partSelects();
        return after[after.length - 1] || null;
    }

    function place(part) {
        var select = emptySelect() || addRow();
        if (!select) return false;
        var exists = Array.prototype.some.call(select.options, function (option) {
            return option.value === String(part.id);
        });
        if (!exists) {
            select.add(new Option(part.label, part.id));
        }
        select.value = String(part.id);
        select.dispatchEvent(new Event('change', {bubbles: true}));
        return true;
    }

    function receive(event) {
        if (event.origin !== window.location.origin) return;
        var parts = event.data && event.data.numscoilExamParts;
        if (!Array.isArray(parts)) return;

        var added = parts.filter(place).length;
        var note = document.getElementById('parts-picker-note');
        if (note) {
            note.textContent = added + ' part' + (added === 1 ? '' : 's') +
                ' added below under "Exam Question Parts" - save the assignment to keep them.';
        }
        window.focus();
    }

    function pickerUrl() {
        var link = document.getElementById('parts-picker-link');
        var base = (link && link.dataset.url) || '/homework/teacher/parts/';
        var topic = document.getElementById('id_topic');
        var query = '?return=form';
        if (topic && topic.value) {
            query += '&topic=' + encodeURIComponent(topic.value);
        }
        return base + query;
    }

    function init() {
        var link = document.getElementById('parts-picker-link');
        if (!link) return;

        window.addEventListener('message', receive);
        link.addEventListener('click', function (event) {
            event.preventDefault();
            var topic = document.getElementById('id_topic');
            if (topic && !topic.value) {
                alert('Choose a topic first - the picker lists that topic’s parts.');
                return;
            }
            window.open(pickerUrl(), 'numscoil-parts-picker');
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
