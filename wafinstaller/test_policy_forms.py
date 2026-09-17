from django.test import SimpleTestCase

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
