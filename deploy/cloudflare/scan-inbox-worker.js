/* Cloudflare Email Worker: hands emailed homework scans to NumScoil.
 *
 * Kept in the repo for the record; it runs on Cloudflare, not on the server.
 * Paste it into Cloudflare -> Email -> Email Routing -> Email Workers, then
 * route scans@numscoil.ie to it (with Subaddressing on, so scans+<token>@
 * reaches it with the token intact).
 *
 * Variables on the Worker (Settings -> Variables and Secrets):
 *   NUMSCOIL_INBOUND_URL  https://www.numscoil.ie/homework-check/inbound-email/
 *                         -- www matters: the bare domain answers with a
 *                         redirect, and a redirected POST loses its body.
 *   SCAN_SECRET           (secret) the same value as the server's
 *                         HOMEWORK_CHECK_INBOUND_SECRET.
 *
 * Deliberately does nothing but forward. The raw email goes to NumScoil
 * untouched and is parsed there, where every awkward attachment is tested.
 */
export default {
  async email(message, env) {
    // Cloudflare refuses anything over 25 MiB before it gets here; this only
    // makes the reason readable if that limit ever changes.
    if (message.rawSize > 25 * 1024 * 1024) {
      message.setReject("That scan is too large for NumScoil. Scan fewer pages at a time.");
      return;
    }

    // Read into memory rather than streaming, so the request has a length:
    // the server (uWSGI on PythonAnywhere) does not take chunked uploads.
    const raw = await new Response(message.raw).arrayBuffer();

    let response;
    try {
      response = await fetch(env.NUMSCOIL_INBOUND_URL, {
        method: "POST",
        headers: {
          "Content-Type": "message/rfc822",
          "X-Scan-Secret": env.SCAN_SECRET,
          "X-Scan-To": message.to,
        },
        body: raw,
      });
    } catch (e) {
      response = null;
    }

    // A bounce tells whoever pressed Send that the scan did not arrive, which
    // beats a scan vanishing without anyone knowing.
    if (!response || !response.ok) {
      message.setReject("NumScoil couldn't take this scan just now. Please send it again.");
    }
  },
};
