from typing import ClassVar

from django import forms
from django.utils.translation import gettext_lazy as _

from wafinstaller.models import (
    AddressEntry,
    AddressList,
    Application,
    Policy,
    PolicyBinding,
    RuleExclusion,
    TriageDecision,
)


FIELD_LABELS = {
    "address_list": _("Address list"),
    "application": _("Application"),
    "classification": _("Classification"),
    "comment": _("Comment"),
    "description": _("Description"),
    "enabled": _("Enabled"),
    "engine_mode": _("Engine mode"),
    "expires_at": _("Expires at"),
    "host": _("Host"),
    "hostname": _("Hostname"),
    "inbound_threshold": _("Inbound threshold"),
    "kind": _("Type"),
    "method": _("HTTP method"),
    "name": _("Name"),
    "network": _("IPv4, IPv6 or CIDR"),
    "notes": _("Notes"),
    "outbound_threshold": _("Outbound threshold"),
    "overrides": _("Overrides"),
    "owner": _("Owner"),
    "paranoia_level": _("Paranoia level"),
    "parent": _("Parent policy"),
    "path": _("Path"),
    "path_match": _("Path matching"),
    "policy": _("Policy"),
    "purpose": _("Purpose"),
    "rationale": _("Rationale"),
    "rule_id": _("Rule ID"),
    "rule_tag": _("Rule tag"),
    "source": _("Source"),
    "source_ip": _("Source IP"),
    "starts_at": _("Starts at"),
    "target": _("Target variable"),
}


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.label = FIELD_LABELS.get(field_name, field.label)
            css_class = (
                "form-check-input position-static ml-2 align-middle"
                if isinstance(field.widget, forms.CheckboxInput)
                else "form-control"
            )
            field.widget.attrs.setdefault("class", css_class)


class AddressListForm(StyledModelForm):
    class Meta:
        model = AddressList
        fields = ("name", "purpose", "description", "enabled")
        widgets: ClassVar[dict] = {"description": forms.Textarea(attrs={"rows": 2})}


class AddressEntryForm(StyledModelForm):
    class Meta:
        model = AddressEntry
        fields = (
            "address_list",
            "network",
            "comment",
            "source",
            "starts_at",
            "expires_at",
            "enabled",
        )
        widgets: ClassVar[dict] = {
            "comment": forms.Textarea(attrs={"rows": 2}),
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "expires_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class RuleExclusionForm(StyledModelForm):
    class Meta:
        model = RuleExclusion
        fields = (
            "name",
            "kind",
            "rule_id",
            "target",
            "host",
            "rule_tag",
            "path",
            "path_match",
            "method",
            "rationale",
            "owner",
            "expires_at",
            "enabled",
        )
        widgets: ClassVar[dict] = {
            "rationale": forms.Textarea(attrs={"rows": 2}),
            "expires_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class TriageDecisionForm(StyledModelForm):
    class Meta:
        model = TriageDecision
        fields = ("classification", "notes")
        widgets: ClassVar[dict] = {
            "notes": forms.Textarea(
                attrs={"rows": 2, "placeholder": "Reasoning, evidence or follow-up"}
            )
        }


class ApplicationForm(StyledModelForm):
    class Meta:
        model = Application
        fields = ("name", "hostname", "description", "enabled")
        widgets: ClassVar[dict] = {"description": forms.Textarea(attrs={"rows": 2})}


class PolicyForm(StyledModelForm):
    class Meta:
        model = Policy
        fields = (
            "name",
            "description",
            "parent",
            "engine_mode",
            "paranoia_level",
            "inbound_threshold",
            "outbound_threshold",
            "enabled",
        )
        widgets: ClassVar[dict] = {"description": forms.Textarea(attrs={"rows": 2})}


class PolicyBindingForm(StyledModelForm):
    class Meta:
        model = PolicyBinding
        fields = ("application", "policy", "overrides", "enabled")
        widgets: ClassVar[dict] = {
            "overrides": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": '{"paranoia_level": 2, "inbound_threshold": 7}',
                }
            )
        }
