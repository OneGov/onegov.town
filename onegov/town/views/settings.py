""" The settings view, defining things like the logo or color of the town. """

from onegov.core.security import Secret
from onegov.form import Form
from wtforms import StringField, validators
from wtforms_components import ColorField
from onegov.town import _
from onegov.town.app import TownApp
from onegov.town.elements import Link
from onegov.town.layout import DefaultLayout
from onegov.town.model import Town


class SettingsForm(Form):
    """ Defines the settings form for onegov town. """

    name = StringField(_(u"Name"), [validators.InputRequired()])
    logo_url = StringField(_("Logo"))
    primary_color = ColorField(_(u"Primary Color"))


@TownApp.form(
    model=Town, name='einstellungen', template='form.pt', permission=Secret,
    form=SettingsForm)
def handle_settings(self, request, form):
    """ Handles the GET and POST login requests. """

    if form.submitted(request):
        with request.app.update_town() as town:
            town.name = form.name.data
            town.logo_url = form.logo_url.data
            town.theme_options['primary-color']\
                = form.primary_color.data.get_hex()

        request.success(_(u"Your changes were saved."))
    else:
        form.name.data = self.name
        form.logo_url.data = self.logo_url
        form.primary_color.data = self.theme_options.get('primary-color')

    layout = DefaultLayout(self, request)
    layout.breadcrumbs = [
        Link(_("Homepage"), layout.homepage_url),
        Link(_("Settings"), request.link(self))
    ]

    return {
        'layout': layout,
        'title': _(u'Settings'),
        'form': form
    }
