'use strict';
/*
 * Live filter for the grouped admin index.
 *
 * Mirrors the behaviour of Django's own nav-sidebar filter so it feels native:
 * type to narrow the model links, Escape to clear. A group whose rows have all
 * been filtered out is hidden too, so the cards reclose rather than leaving a
 * row of empty headings.
 */
(function () {
    var input = document.getElementById('ns-filter');
    var main = document.getElementById('content-main');
    if (!input || !main) {
        return;
    }
    var empty = document.getElementById('ns-filter-empty');
    var HIDDEN = 'ns-filtered-out';

    // A model row is the one carrying th[scope="row"]; app_list.html also emits
    // a visually-hidden thead row that must not be treated as a model.
    var groups = Array.prototype.map.call(
        main.querySelectorAll('.module'),
        function (module) {
            var caption = module.querySelector('caption');
            var rows = Array.prototype.filter.call(
                module.querySelectorAll('tr'),
                function (row) { return row.querySelector('th[scope="row"]'); }
            );
            rows.forEach(function (row) {
                row.dataset.nsName =
                    row.querySelector('th[scope="row"]').textContent.trim().toLowerCase();
            });
            return {
                el: module,
                name: caption ? caption.textContent.trim().toLowerCase() : '',
                rows: rows
            };
        }
    );

    function apply() {
        var query = input.value.trim().toLowerCase();
        var anyShown = false;

        groups.forEach(function (group) {
            // Typing a group name reveals the whole group, so "teaching" is a
            // way to see one section rather than hunting its models by name.
            var wholeGroup = query !== '' && group.name.indexOf(query) !== -1;
            var shown = 0;

            group.rows.forEach(function (row) {
                var match = query === '' || wholeGroup ||
                    row.dataset.nsName.indexOf(query) !== -1;
                row.classList.toggle(HIDDEN, !match);
                if (match) {
                    shown += 1;
                }
            });

            group.el.classList.toggle(HIDDEN, shown === 0);
            if (shown > 0) {
                anyShown = true;
            }
        });

        if (empty) {
            empty.classList.toggle(HIDDEN, query === '' || anyShown);
        }
    }

    input.addEventListener('input', apply);
    input.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            input.value = '';
            apply();
        }
    });

    // Browsers restore the field's value on a back-navigation without firing
    // input, which would otherwise leave the text and the cards disagreeing.
    if (input.value !== '') {
        apply();
    }
}());
