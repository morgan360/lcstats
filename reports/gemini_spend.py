"""
Gemini spend, for the superuser-only spend page beside the OpenAI figures.

Google exposes neither spend nor prepaid balance for a Gemini API key, so this
reads the cost NumScoil records for each homework-check vision call
(homework_check.VisionUsage, in dollars at list price) and estimates what is
left of the prepaid credit: the newest CreditBalance entered on the spend page,
or the GEMINI_CREDIT_* settings before one exists, minus the spend since.

Days are UTC, to line up with the OpenAI figures on the same page. Summed in
Python rather than with TruncDate: there are a few hundred rows a month, and
it keeps MySQL's timezone tables out of the picture.
"""
import datetime as dt
from decimal import Decimal

from django.conf import settings

from homework_check.models import VisionUsage

from .models import CreditBalance


def get_gemini_summary():
    now = dt.datetime.now(dt.timezone.utc)
    today = now.date()
    month_start = today.replace(day=1)
    balance = CreditBalance.latest_for("gemini")
    if balance:
        topup = float(balance.amount)
        since = balance.recorded_at.astimezone(dt.timezone.utc).date()
    else:
        topup, since = settings.GEMINI_CREDIT_TOPUP, settings.GEMINI_CREDIT_SINCE
    earliest = min(month_start, since) if since else month_start

    rows = VisionUsage.objects.filter(
        model__startswith="gemini",
        created_at__gte=dt.datetime(earliest.year, earliest.month, earliest.day,
                                    tzinfo=dt.timezone.utc),
    ).values_list("created_at", "cost_usd")

    # Calls are timestamped, so an entered balance is followed from the moment
    # it was entered. A settings date means from the start of that day.
    by_date, calls, spent_since_usd = {}, 0, Decimal("0")
    for created_at, cost in rows:
        day = created_at.astimezone(dt.timezone.utc).date()
        by_date[day] = by_date.get(day, Decimal("0")) + cost
        if day >= month_start:
            calls += 1
        if balance and created_at > balance.recorded_at:
            spent_since_usd += cost
        elif not balance and since and day >= since:
            spent_since_usd += cost

    summary = {
        "today": float(by_date.get(today, 0)),
        "month_to_date": float(sum(a for d, a in by_date.items() if d >= month_start)),
        "month_label": today.strftime("%B %Y"),
        "daily": sorted(({"date": d, "amount": float(a)}
                         for d, a in by_date.items() if d >= month_start),
                        key=lambda r: r["date"], reverse=True),
        "calls": calls,
        "remaining": None,
        "currency": settings.GEMINI_CREDIT_CURRENCY,
        "recorded_at": balance.recorded_at if balance else None,
    }

    if topup is not None and since is not None:
        spent_usd = float(spent_since_usd)
        rate = settings.GEMINI_USD_PER_CREDIT or 1.0
        summary.update({
            "topup": topup,
            "since": since,
            "spent_since_usd": spent_usd,
            "spent_since": spent_usd / rate,
            "remaining": topup - spent_usd / rate,
            "rate": rate,
        })
    return summary


def record_balance(amount, user=None):
    """Save the credit left, as AI Studio's billing page shows it."""
    return CreditBalance.objects.create(provider="gemini", amount=amount, recorded_by=user)
