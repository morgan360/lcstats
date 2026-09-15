"""What homework checks cost, and what is left of the Gemini credit.

Google has no spend or balance API for a Gemini key, so the spend page adds up
the cost NumScoil records for each call. These pin the prices, the recording,
and that a deleted check's cost is still counted -- without that, the estimate
of what is left of the credit drifts high every time a teacher deletes one.
"""
import datetime as dt
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from homework.models import TeacherClass, TeacherProfile
from homework_check.models import CheckPhoto, HomeworkCheck, VisionUsage
from homework_check.services import pricing, runner
from hw_solutions.models import HWSolution
from reports.gemini_spend import get_gemini_summary


class PricingTests(SimpleTestCase):

    def test_gemini_flash_at_list_price(self):
        # 20k prompt of which 16k cached, 500 out: 4k x .75 + 16k x .075 + 500 x 3.75
        cost = pricing.cost_usd('gemini-3.8-flash', 20000, 16000, 500, dt.date(2026, 9, 15))
        self.assertEqual(cost, Decimal('0.006075'))

    def test_the_january_price_rise_applies_from_january(self):
        before = pricing.cost_usd('gemini-3.8-flash', 1_000_000, 0, 0, dt.date(2026, 12, 31))
        after = pricing.cost_usd('gemini-3.8-flash', 1_000_000, 0, 0, dt.date(2027, 1, 1))
        self.assertEqual((before, after), (Decimal('0.75'), Decimal('1.5')))

    def test_an_unpriced_model_costs_nothing_rather_than_breaking(self):
        self.assertEqual(pricing.cost_usd('mystery-model', 1000, 0, 1000), Decimal('0'))


class RecordingTests(TestCase):

    def setUp(self):
        teacher = User.objects.create_user('t', password='pw', is_staff=True)
        profile = TeacherProfile.objects.create(user=teacher)
        student = User.objects.create_user('s')
        cls = TeacherClass.objects.create(teacher=profile, name='6th')
        self.check = HomeworkCheck.objects.create(
            teacher=teacher, teacher_class=cls, student=student,
            solution=HWSolution.objects.create(title='S'), exercise_name='Ex 1.1')
        CheckPhoto.objects.create(hw_check=self.check, order=0)

    def run_batch(self):
        result = {'questions': [], 'model_used': 'gemini-3.8-flash',
                  'usage': {'prompt_tokens': 20000, 'cached_tokens': 16000,
                            'completion_tokens': 500, 'reasoning_tokens': 0}}
        with mock.patch.object(runner, '_encode_solution_pages', return_value=([], [])), \
             mock.patch.object(runner, 'encode_for_api', return_value='b64'), \
             mock.patch.object(runner, 'analyse_chunk', return_value=result):
            runner.analyse_next_chunk(self.check)

    def test_each_batch_is_recorded_with_its_cost(self):
        self.run_batch()
        row = VisionUsage.objects.get()
        self.assertEqual((row.model, row.hw_check, row.cost_usd),
                         ('gemini-3.8-flash', self.check, Decimal('0.006075')))

    def test_a_deleted_check_still_counts(self):
        self.run_batch()
        self.check.delete()
        row = VisionUsage.objects.get()
        self.assertIsNone(row.hw_check)
        self.assertEqual(row.cost_usd, Decimal('0.006075'))

    def test_bookkeeping_never_fails_the_batch(self):
        with mock.patch.object(VisionUsage.objects, 'create', side_effect=RuntimeError('db')):
            self.run_batch()   # would raise if the ledger could break a check
        self.assertEqual(self.check.photos.get().status, CheckPhoto.Status.ANALYSED)


@override_settings(GEMINI_CREDIT_TOPUP=25.0, GEMINI_CREDIT_SINCE=dt.date(2026, 9, 15),
                   GEMINI_CREDIT_CURRENCY='EUR', GEMINI_USD_PER_CREDIT=1.15)
class SummaryTests(TestCase):

    def usage(self, model, cost, days_ago=0):
        row = VisionUsage.objects.create(model=model, cost_usd=Decimal(cost))
        VisionUsage.objects.filter(pk=row.pk).update(
            created_at=timezone.now() - dt.timedelta(days=days_ago))

    def test_remaining_is_the_credit_less_gemini_spend_in_euro(self):
        self.usage('gemini-3.8-flash', '1.15')
        self.usage('gemini-3.8-flash', '2.30')
        self.usage('gpt-5.5', '9.00')    # OpenAI, counted on its own side of the page
        s = get_gemini_summary()
        self.assertAlmostEqual(s['spent_since_usd'], 3.45)
        self.assertAlmostEqual(s['remaining'], 22.0)
        self.assertEqual(s['calls'], 2)

    @override_settings(GEMINI_CREDIT_TOPUP=None)
    def test_no_top_up_configured_shows_spend_only(self):
        self.usage('gemini-3.8-flash', '0.50')
        s = get_gemini_summary()
        self.assertIsNone(s['remaining'])
        self.assertAlmostEqual(s['today'], 0.50)

    def test_the_page_shows_both_providers(self):
        self.usage('gemini-3.8-flash', '1.15')
        User.objects.create_superuser('boss', password='pw')
        self.client.login(username='boss', password='pw')
        with mock.patch('reports.openai_costs.get_cost_summary',
                        return_value={'ok': False, 'not_configured': True, 'error': ''}):
            response = self.client.get(reverse('reports:openai_costs'))
        self.assertContains(response, 'AI spend')
        self.assertContains(response, 'Gemini')
        self.assertContains(response, '≈ €24.00')

    def test_teachers_cannot_see_it(self):
        User.objects.create_user('teach', password='pw', is_staff=True)
        self.client.login(username='teach', password='pw')
        self.assertEqual(self.client.get(reverse('reports:openai_costs')).status_code, 403)
