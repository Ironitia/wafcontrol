from django.test import SimpleTestCase
from django.urls import reverse
from django.utils.translation import override

from wafinstaller.policy_forms import ApplicationForm, RuleExclusionForm


class PolicyFormLayoutTests(SimpleTestCase):
    def test_enabled_checkboxes_are_inline_with_their_labels(self):
        for form_class in (ApplicationForm, RuleExclusionForm):
            with self.subTest(form=form_class.__name__):
                css_classes = form_class().fields["enabled"].widget.attrs["class"]

                self.assertIn("form-check-input", css_classes)
                self.assertIn("position-static", css_classes)
                self.assertIn("ml-2", css_classes)
                self.assertIn("align-middle", css_classes)


class InternationalizationTests(SimpleTestCase):
    def test_french_policy_form_labels_are_available(self):
        with override("fr"):
            form = ApplicationForm()

            self.assertEqual(form.fields["name"].label, "Nom")
            self.assertEqual(form.fields["enabled"].label, "Activé")

    def test_language_endpoint_sets_persistent_cookie(self):
        response = self.client.post(
            reverse("set_language"),
            {"language": "fr", "next": "/login/"},
            secure=True,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/login/")
        self.assertEqual(response.cookies["wafcontrol_language"].value, "fr")
