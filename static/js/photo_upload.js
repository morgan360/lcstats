/* Getting phone photos to the server as JPEG.
 *
 * The one job that matters here is HEIC. iPhones save to HEIC by default, the
 * server cannot decode it -- pillow-heif is a binary wheel and a build risk on
 * PythonAnywhere -- and a teacher picking sixteen photos out of their library
 * would otherwise have all sixteen rejected. Drawing the file into a canvas and
 * calling toBlob('image/jpeg') converts it for free, because Safari decodes
 * HEIC into the canvas even though it cannot hand us the bytes.
 *
 * The same trick shrinks a 4MB photo to a few hundred KB, which matters on
 * school wifi.
 *
 * NOTE: students/templates/students/work_mobile.html still carries its own
 * copy of downscale(). That page was verified by hand on a real phone and is
 * live to students, so it was deliberately left alone rather than switched
 * over as part of a teacher-side feature. The two are the same algorithm --
 * if you change the conversion here, change it there too, or the student and
 * teacher paths will start handling HEIC differently.
 */
window.PhotoUpload = (function () {
  'use strict';

  var MAX_EDGE = 1600;

  /* One file to a JPEG blob. Falls back to the original if the browser cannot
   * decode it at all, so the server gives the proper message rather than the
   * page inventing one. */
  function downscale(file, maxEdge, done) {
    var img = new Image();
    var url = URL.createObjectURL(file);

    img.onload = function () {
      var scale = Math.min(1, maxEdge / Math.max(img.width, img.height));
      var canvas = document.createElement('canvas');
      canvas.width = Math.round(img.width * scale);
      canvas.height = Math.round(img.height * scale);
      canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      canvas.toBlob(function (out) {
        // Release the backing store before the next file is decoded. Sixteen
        // full-resolution canvases held at once will have Safari kill the tab.
        canvas.width = canvas.height = 0;
        done(out || file);
      }, 'image/jpeg', 0.8);
    };

    img.onerror = function () {
      URL.revokeObjectURL(url);
      done(file);
    };

    img.src = url;
  }

  /* Convert and POST a list of files ONE AT A TIME.
   *
   * Sequential on purpose, on both counts: parallel decodes exhaust memory on
   * an older phone, and parallel uploads on school wifi are slower than one
   * after another, not faster.
   *
   * opts: { url, files, csrf, field, maxEdge,
   *         onProgress(index, total, file),
   *         onOne(index, data),        // that upload succeeded
   *         onError(index, message),   // that one failed; the rest continue
   *         onDone(succeeded, failed) }
   */
  function uploadAll(opts) {
    var files = Array.prototype.slice.call(opts.files || []);
    var field = opts.field || 'photo';
    var maxEdge = opts.maxEdge || MAX_EDGE;
    var succeeded = 0;
    var failed = 0;

    function step(i) {
      if (i >= files.length) {
        if (opts.onDone) opts.onDone(succeeded, failed);
        return;
      }

      if (opts.onProgress) opts.onProgress(i, files.length, files[i]);

      downscale(files[i], maxEdge, function (blob) {
        var form = new FormData();
        form.append(field, blob, 'page' + (i + 1) + '.jpg');

        fetch(opts.url, {
          method: 'POST',
          body: form,
          headers: { 'X-CSRFToken': opts.csrf }
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data && data.success) {
              succeeded++;
              if (opts.onOne) opts.onOne(i, data);
            } else {
              failed++;
              // One bad photo out of sixteen must not lose the other fifteen.
              if (opts.onError) {
                opts.onError(i, (data && data.message) || 'That one would not upload.');
              }
            }
          })
          .catch(function () {
            failed++;
            if (opts.onError) opts.onError(i, 'Could not reach NumScoil.');
          })
          .finally(function () { step(i + 1); });
      });
    }

    step(0);
  }

  return { downscale: downscale, uploadAll: uploadAll, MAX_EDGE: MAX_EDGE };
})();
