/* Ticking, counting and retagging on the worksheet page.
 *
 * The element that gets the .selected styling is whatever carries
 * data-selectable, and the checkbox name is read from the page rather than
 * hard-coded.
 */
(function () {
    var holder = document.querySelector('[data-worksheet-checkbox]');
    var boxName = holder ? holder.dataset.worksheetCheckbox : 'question_ids';

    function boxes() {
        return document.querySelectorAll(
            'input[type="checkbox"][name="' + boxName + '"]');
    }

    function mark(box) {
        var target = box.closest('[data-selectable]');
        if (target) target.classList.toggle('selected', box.checked);
    }

    function setAll(checked) {
        boxes().forEach(function (box) {
            box.checked = checked;
            mark(box);
        });
        updateCount();
    }

    window.selectAll = function () { setAll(true); };
    window.deselectAll = function () { setAll(false); };

    window.updateCount = function () {
        var checked = 0;
        boxes().forEach(function (box) {
            if (box.checked) checked++;
            mark(box);
        });
        document.getElementById('count').textContent = checked;
        ['print-btn', 'pdf-btn'].forEach(function (id) {
            var button = document.getElementById(id);
            if (button) button.disabled = checked === 0;
        });
    };

    window.filterChanged = function () {
        var subject = document.getElementById('subject-select').value;
        var topic = document.getElementById('topic-select').value;
        var params = [];
        if (subject) params.push('subject=' + subject);
        if (topic) params.push('topic=' + topic);
        window.location.href = window.location.pathname + '?' + params.join('&');
    };

    /* Retagging. The row stays where it is until the page is reloaded, even
       when it has just been moved off the topic being listed -- reshuffling
       the grid under someone correcting a run of cards is worse than a stale
       row, and the state chip says what happened. */
    function csrf() {
        var input = document.querySelector('[name=csrfmiddlewaretoken]');
        return input ? input.value : '';
    }

    /* A question's three topics and its "also list" tick post together, so
       a change to any one of them saves the whole set. */
    document.addEventListener('change', function (event) {
        var control = event.target.closest && event.target.closest('.topic-retag');
        if (!control) return;

        var state = control.querySelector('.retag-state');
        var body = new FormData();
        control.querySelectorAll('select[name]').forEach(function (select) {
            body.append(select.name, select.value);
        });
        var tick = control.querySelector('input[name="list_under_secondary"]');
        body.append('list_under_secondary', tick && tick.checked ? '1' : '');
        body.append('csrfmiddlewaretoken', csrf());
        state.textContent = 'saving…';
        state.style.color = '';

        fetch(control.dataset.endpoint, {
            method: 'POST',
            body: body,
            credentials: 'same-origin',
            headers: {'X-Requested-With': 'XMLHttpRequest'}
        }).then(function (response) {
            return response.json().then(function (data) {
                if (!response.ok) throw new Error(data.error || response.status);
                return data;
            });
        }).then(function (data) {
            if (tick) tick.checked = data.list_under_secondary;
            state.textContent = 'saved';
            state.style.color = '#B8E986';
        }).catch(function (error) {
            state.textContent = 'not saved: ' + error.message;
            state.style.color = '#FA709A';
        });
    });

    document.addEventListener('DOMContentLoaded', function () {
        if (document.getElementById('count')) updateCount();
    });
})();
