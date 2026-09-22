"""The stylesheet's cache-busting stamp.

Without it a rebuilt tailwind.css never reaches a browser that already has the
old one, and the symptom is invisible artwork on a page that otherwise looks
right -- so this is worth a test rather than an eyeball.
"""
from django.template import Context, Template
from django.test import TestCase


class AssetVersionTests(TestCase):

    def render(self, body):
        return Template('{% load assets %}' + body).render(Context({}))

    def test_a_real_asset_gets_a_stamp(self):
        stamp = self.render("{% asset_version 'css/tailwind.css' %}")
        self.assertTrue(stamp.isdigit(), stamp)

    def test_a_missing_asset_is_quietly_blank(self):
        self.assertEqual(self.render("{% asset_version 'css/nope.css' %}"), '')

    def test_the_stylesheet_link_carries_it(self):
        response = self.client.get('/')
        self.assertRegex(
            response.content.decode(), r'css/tailwind\.css\?v=\d+')
