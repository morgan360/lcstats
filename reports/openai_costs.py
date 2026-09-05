"""
OpenAI organization spend, for the superuser-only cost page.

OpenAI does not expose a prepaid *balance* over the API. It does expose actual
dollar *spend* via the org Costs API, which needs an Admin key (sk-admin-...),
not the project API key. This module fetches daily spend and, if a top-up figure
is configured, derives a "remaining" estimate ourselves.

Costs API: GET https://api.openai.com/v1/organization/costs
  headers: Authorization: Bearer <OPENAI_ADMIN_KEY>
  params : start_time (unix s, required), bucket_width='1d', limit, page
  data[] : {object:"bucket", start_time, results:[{amount:{value, currency}}]}
"""
import datetime as dt
import logging

import requests
from django.conf import settings
from django.core.cache import cache

log = logging.getLogger(__name__)

COSTS_URL = "https://api.openai.com/v1/organization/costs"
CACHE_KEY = "openai_costs_summary_v1"
CACHE_TTL = 600  # 10 minutes -- the API is slow-ish and this page is low-traffic
REQUEST_TIMEOUT = 20
MAX_PAGES = 24  # safety cap on pagination


def _fetch_daily_costs(start_ts):
    """
    Return {date: amount_float} of daily spend from start_ts (unix seconds) to now.

    Buckets are UTC-day aligned to match how OpenAI reports them. Raises on a
    missing key or any HTTP/parse error -- callers wrap this.
    """
    key = settings.OPENAI_ADMIN_KEY
    if not key:
        raise RuntimeError("OPENAI_ADMIN_KEY is not set")

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    params = {"start_time": int(start_ts), "bucket_width": "1d", "limit": 180}

    by_date = {}
    currency = "usd"
    page = None
    for _ in range(MAX_PAGES):
        if page:
            params["page"] = page
        resp = requests.get(COSTS_URL, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()

        for bucket in payload.get("data", []):
            bucket_ts = bucket.get("start_time", start_ts)
            bucket_date = dt.datetime.fromtimestamp(bucket_ts, tz=dt.timezone.utc).date()
            amount = 0.0
            for result in bucket.get("results", []):
                amt = result.get("amount") or {}
                amount += float(amt.get("value") or 0)
                currency = amt.get("currency", currency)
            by_date[bucket_date] = by_date.get(bucket_date, 0.0) + amount

        if payload.get("has_more") and payload.get("next_page"):
            page = payload["next_page"]
        else:
            break

    return by_date, currency


def get_cost_summary(force_refresh=False):
    """
    Cached spend summary for the template. Always returns a dict; on failure it
    carries {"ok": False, "error": ...} so the page can show a notice, never 500.
    """
    if not force_refresh:
        cached = cache.get(CACHE_KEY)
        if cached:
            return cached

    if not settings.OPENAI_ADMIN_KEY:
        return {
            "ok": False,
            "not_configured": True,
            "error": "OPENAI_ADMIN_KEY is not set in the environment.",
        }

    try:
        now = dt.datetime.now(dt.timezone.utc)
        today = now.date()
        month_start = today.replace(day=1)

        topup = settings.OPENAI_CREDIT_TOPUP
        since = settings.OPENAI_CREDIT_SINCE

        # Fetch back far enough to cover both the current month and the top-up date.
        fetch_from = month_start
        if since and since < fetch_from:
            fetch_from = since
        start_ts = dt.datetime(
            fetch_from.year, fetch_from.month, fetch_from.day, tzinfo=dt.timezone.utc
        ).timestamp()

        by_date, currency = _fetch_daily_costs(start_ts)

        today_spend = by_date.get(today, 0.0)
        mtd = sum(a for d, a in by_date.items() if d >= month_start)
        daily = sorted(
            ({"date": d, "amount": a} for d, a in by_date.items() if d >= month_start),
            key=lambda x: x["date"],
            reverse=True,
        )

        summary = {
            "ok": True,
            "currency": currency,
            "today": today_spend,
            "month_to_date": mtd,
            "month_label": today.strftime("%B %Y"),
            "daily": daily,
            "updated_at": now,
            "topup": None,
            "since": None,
            "spent_since": None,
            "remaining": None,
        }

        if topup is not None and since is not None:
            spent_since = sum(a for d, a in by_date.items() if d >= since)
            summary.update({
                "topup": topup,
                "since": since,
                "spent_since": spent_since,
                "remaining": topup - spent_since,
            })

        cache.set(CACHE_KEY, summary, CACHE_TTL)
        return summary

    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        hint = ""
        if status == 401:
            hint = " (401 -- key rejected; is this an Admin key, not a project key?)"
        log.warning("OpenAI cost fetch HTTP %s: %s", status, exc)
        return {"ok": False, "error": f"OpenAI API returned HTTP {status}{hint}"}
    except Exception as exc:  # noqa: BLE001 -- page must degrade, never 500
        log.warning("OpenAI cost fetch failed: %s", exc)
        return {"ok": False, "error": str(exc)}
