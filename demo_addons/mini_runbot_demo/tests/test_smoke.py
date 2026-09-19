from odoo.tests.common import TransactionCase


class TestMiniRunbotDemo(TransactionCase):
    def test_registry_is_available(self):
        self.assertIsNotNone(self.env.registry)
