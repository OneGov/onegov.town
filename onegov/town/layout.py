from cached_property import cached_property
from onegov.core.static import StaticFile
from onegov.org.elements import Link
from onegov.org.layout import Layout as BaseLayout
from onegov.org.layout import DefaultLayout as BaseDefaultLayout
from onegov.town import _
from onegov.org.models import (
    GeneralFileCollection,
    ImageFileCollection,
)
from onegov.town.theme.town_theme import user_options


class Layout(BaseLayout):

    @property
    def town(self):
        """ An alias for self.request.app.town. """
        return self.request.app.town

    @property
    def primary_color(self):
        return self.town.theme_options.get(
            'primary-color', user_options['primary-color'])

    @cached_property
    def default_map_view(self):
        return self.town.default_map_view or None

    @cached_property
    def font_awesome_path(self):
        static_file = StaticFile.from_application(
            self.app, 'font-awesome/css/font-awesome.min.css')

        return self.request.link(static_file)


class DefaultLayout(BaseDefaultLayout):

    @cached_property
    def bottom_links(self):

        request = self.request

        if request.current_role == 'editor':
            return [
                Link(_('Logout'), self.logout_url),
                Link(_('User Profile'), request.link(
                    self.town, 'benutzerprofil'
                )),
                Link(_('Files'), request.link(
                    GeneralFileCollection(self.app)
                )),
                Link(_('Images'), request.link(
                    ImageFileCollection(self.app)
                )),
                Link('OneGov Cloud', 'http://www.onegovcloud.ch'),
                Link('Seantis GmbH', 'https://www.seantis.ch')
            ]
        elif request.current_role == 'admin':
            return [
                Link(_('Logout'), self.logout_url),
                Link(_('User Profile'), request.link(
                    self.town, 'benutzerprofil'
                )),
                Link(_('Files'), request.link(
                    GeneralFileCollection(self.app)
                )),
                Link(_('Images'), request.link(
                    ImageFileCollection(self.app)
                )),
                Link(_('Settings'), request.link(self.town, 'einstellungen')),
                Link('OneGov Cloud', 'http://www.onegovcloud.ch'),
                Link('Seantis GmbH', 'https://www.seantis.ch')
            ]
        else:
            return [
                Link(_('Login'), self.login_url),
                Link('OneGov Cloud', 'http://www.onegovcloud.ch'),
                Link('Seantis GmbH', 'https://www.seantis.ch')
            ]
