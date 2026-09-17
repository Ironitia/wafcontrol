from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from wafinstaller.models import Attack, RuleExclusion
from wafinstaller.policy import render_policy
from wafinstaller.policy_forms import RuleExclusionForm
from wafinstaller.policy_views import PolicyManagementView


class SourceIPExclusionTests(TestCase):
    def setUp(self):
        self.data = {
            "name": "numeric-host-admin",
            "kind": "remove_rule",
            "rule_id": 920350,
            "source_ip": "192.0.2.10",
            "path_match": "prefix",
            "rationale": "Administrative access by IP",
            "owner": "operations",
            "enabled": True,
        }

    def exclusion(self, **overrides):
        data = {**self.data, "status": "approved", **overrides}
        instance = RuleExclusion(**data)
        instance.full_clean()
        instance.save()
        return instance

    def test_ip_only_is_runtime_scoped_and_never_global_or_full_bypass(self):
        instance = self.exclusion()
        bundle = render_policy()
        self.assertIn(
            f'SecRule REMOTE_ADDR "@streq 192.0.2.10" "id:{1700000 + instance.pk},'
            'phase:1,pass,nolog,t:none,ctl:ruleRemoveById=920350"',
            bundle.before,
        )
        self.assertNotIn("920350", bundle.after)
        self.assertNotIn("ruleEngine=Off", bundle.before)

    def test_ipv6_is_validated_and_normalized(self):
        self.exclusion(source_ip="2001:0DB8:0:0::1")
        self.assertIn('REMOTE_ADDR "@streq 2001:db8::1"', render_policy().before)

    def test_invalid_ip_and_networks_are_rejected(self):
        for value in ("not-an-ip", "192.0.2.0/24", "*", '192.0.2.1"\nSecRuleEngine Off'):
            with self.subTest(value=value):
                form = RuleExclusionForm(data={**self.data, "source_ip": value})
                self.assertFalse(form.is_valid())
                self.assertIn("source_ip", form.errors)
                with self.assertRaises(ValidationError):
                    RuleExclusion(**{**self.data, "source_ip": value}).full_clean()

    def test_renderer_rejects_corrupt_ip_instead_of_broadening(self):
        instance = self.exclusion()
        RuleExclusion.objects.filter(pk=instance.pk).update(source_ip="invalid")
        with self.assertRaises(ValueError):
            render_policy()

    def test_all_scope_conditions_are_chained_before_exclusion_action(self):
        self.exclusion(host="example.test", path="/admin", method="GET")
        rules = [line.strip() for line in render_policy().before.splitlines() if "SecRule " in line]
        self.assertEqual(len(rules), 4)
        self.assertIn('REMOTE_ADDR "@streq 192.0.2.10"', rules[0])
        self.assertTrue(all("chain" in line and "ctl:" not in line for line in rules[:-1]))
        self.assertEqual(rules[-1], 'SecRule REQUEST_METHOD "@streq GET" "t:none,ctl:ruleRemoveById=920350"')

    def test_empty_ip_preserves_existing_scope(self):
        form = RuleExclusionForm(data={**self.data, "source_ip": ""})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.cleaned_data["source_ip"])
        self.exclusion(source_ip=None, host="example.test")
        bundle = render_policy()
        self.assertIn('REQUEST_HEADERS:Host "@streq example.test"', bundle.before)
        self.assertNotIn("REMOTE_ADDR", bundle.before)

    def test_draft_disabled_and_expired_are_not_applied(self):
        instance = self.exclusion(status="draft")
        self.assertNotIn("920350", render_policy().before)
        instance.status = "approved"
        instance.enabled = False
        instance.save()
        self.assertNotIn("920350", render_policy().before)
        instance.enabled = True
        instance.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        instance.save()
        self.assertNotIn("920350", render_policy().before)

    def test_impact_count_respects_ip_scope(self):
        instance = self.exclusion()
        for ip in ("192.0.2.10", "192.0.2.11"):
            Attack.objects.create(ip=ip, rule_id="920350", uri="/", severity=3)
        self.assertEqual(PolicyManagementView._impact_count(instance), {"total": 1, "suspicious": 1})

    @patch("wafinstaller.policy_views.include_status", return_value=False)
    def test_ui_create_edit_clone_toggle_and_display(self, _includes):
        user = get_user_model().objects.create_user(username="ip-admin")
        self.client.force_login(user)
        response = self.client.post(
            reverse("wafinstaller:rule_exclusion_create"), self.data, secure=True
        )
        self.assertEqual(response.status_code, 302)
        instance = RuleExclusion.objects.get(name=self.data["name"])
        self.assertEqual(instance.source_ip, "192.0.2.10")
        self.assertEqual(instance.status, "draft")
        page = reverse("wafinstaller:policy_management")
        response = self.client.get(page, secure=True)
        self.assertContains(response, 'Source: <code>192.0.2.10</code>')
        response = self.client.get(page, {"edit": instance.pk}, secure=True)
        self.assertContains(response, 'name="source_ip" value="192.0.2.10"')

        def mutate(operation):
            return self.client.post(
                reverse(
                    "wafinstaller:policy_object_mutation",
                    args=("rule-exclusion", instance.pk, operation),
                ),
                secure=True,
            )

        mutate("approve")
        self.assertIn("920350", render_policy().before)
        mutate("clone")
        clone = RuleExclusion.objects.exclude(pk=instance.pk).get()
        self.assertEqual(clone.source_ip, "192.0.2.10")
        self.assertEqual(clone.status, "draft")
        mutate("toggle")
        self.assertNotIn("920350", render_policy().before)
        mutate("toggle")
        response = self.client.post(
            reverse("wafinstaller:rule_exclusion_update", args=(instance.pk,)),
            {**self.data, "source_ip": "192.0.2.12"},
            secure=True,
        )
        self.assertEqual(response.status_code, 302)
        instance.refresh_from_db()
        self.assertEqual(instance.source_ip, "192.0.2.12")
        self.assertEqual(instance.status, "draft")
        self.assertIsNone(instance.approved_by)
        self.assertNotIn("920350", render_policy().before)
