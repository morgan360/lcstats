/* Ticking, counting and retagging on the two worksheet pages.
 *
 * The questions page ticks a whole card; the parts page ticks one row inside
 * a card, because a question's parts share its picture. So the element that
 * gets the .selected styling is whatever carries data-selectable, and the
 * checkbox name is read from the page rather than hard-coded.
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

    document.addEventListener('change', function (event) {
        var select = event.target;
        if (!select.classList || !select.classList.contains('topic-retag')) return;

        var state = select.parentElement.querySelector('.retag-state');
        var body = new FormData();
        body.append('topic', select.value);
        body.append('csrfmiddlewaretoken', csrf());
        state.textContent = 'saving…';

        fetch(select.dataset.endpoint, {
            method: 'POST',
            body: body,
            credentials: 'same-origin',
            headers: {'X-Requested-With': 'XMLHttpRequest'}
        }).then(function (response) {
            if (!response.ok) throw new Error(response.status);
            return response.json();
        }).then(function () {
            state.textContent = 'saved';
            state.style.color = '#B8E986';
        }).catch(function () {
            state.textContent = 'not saved';
            state.style.color = '#FA709A';
        });
    });

    /* Tick every part of one question, from the button on its card. */
    window.selectQuestion = function (button, on) {
        button.closest('[data-question]')
            .querySelectorAll('input[type="checkbox"][name="' + boxName + '"]')
            .forEach(function (box) { box.checked = on; mark(box); });
        updateCount();
    };

    document.addEventListener('DOMContentLoaded', function () {
        if (document.getElementById('count')) updateCount();
    });
})();
