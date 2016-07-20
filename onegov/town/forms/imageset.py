from onegov.form import Form
from onegov.town import _
from wtforms import StringField, TextAreaField, validators


class ImageSetForm(Form):
    title = StringField(_("Title"), [validators.InputRequired()])

    lead = TextAreaField(
        label=_("Lead"),
        description=_("Describes what this photo album is about"),
        render_kw={'rows': 4})
