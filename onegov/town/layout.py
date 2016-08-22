from cached_property import cached_property
from dateutil import rrule
from onegov.core.static import StaticFile
from onegov.core.utils import linkify
from onegov.event import OccurrenceCollection
from onegov.form import FormCollection
from onegov.libres import ResourceCollection
from onegov.org.elements import DeleteLink, Link, LinkGroup
from onegov.org.layout import Layout as BaseLayout
from onegov.page import Page, PageCollection
from onegov.people import PersonCollection
from onegov.ticket import TicketCollection
from onegov.town import _
from onegov.org.models import (
    GeneralFileCollection,
    ImageFileCollection,
    ImageSetCollection,
    PageMove
)
from onegov.town.theme.town_theme import user_options
from onegov.newsletter import NewsletterCollection, RecipientCollection
from purl import URL
from sqlalchemy import desc


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
    def svg(self):
        return self.template_loader['svg.pt']

    @cached_property
    def font_awesome_path(self):
        static_file = StaticFile.from_application(
            self.app, 'font-awesome/css/font-awesome.min.css')

        return self.request.link(static_file)


class DefaultMailLayout(Layout):
    """ A special layout for creating HTML E-Mails. """

    @cached_property
    def base(self):
        return self.template_loader['mail_layout.pt']

    @cached_property
    def macros(self):
        return self.template_loader['mail_macros.pt']

    @cached_property
    def contact_html(self):
        """ Returns the contacts html, but instead of breaking it into multiple
        lines (like on the site footer), this version puts it all on one line.

        """

        lines = (l.strip() for l in self.town.meta['contact'].splitlines())
        lines = (l for l in lines if l)

        return linkify(', '.join(lines))

    def unsubscribe_link(self, username):
        return '{}?token={}'.format(
            self.request.link(self.town, name='unsubscribe'),
            self.request.new_url_safe_token(
                data={'user': username},
                salt='unsubscribe'
            )
        )


class DefaultLayout(Layout):
    """ The defaut layout meant for the public facing parts of the site. """

    def __init__(self, model, request):
        super().__init__(model, request)

        # always include the common js files
        self.request.include('common')

        if self.request.is_logged_in:
            self.request.include('sortable')

    @cached_property
    def breadcrumbs(self):
        """ Returns the breadcrumbs for the current page. """
        return [Link(_("Homepage"), self.homepage_url)]

    @cached_property
    def root_pages(self):
        query = PageCollection(self.app.session()).query(ordered=False)
        query = query.order_by(desc(Page.type), Page.order)
        query = query.filter(Page.parent_id == None)

        return self.request.exclude_invisible(query.all())

    @cached_property
    def top_navigation(self):
        return tuple(
            Link(r.title, self.request.link(r)) for r in self.root_pages
        )

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


class AdjacencyListLayout(DefaultLayout):
    """ Provides layouts for for models inheriting from
    :class:`onegov.core.orm.abstract.AdjacencyList`

    """

    @cached_property
    def sortable_url_template(self):
        return self.csrf_protected_url(
            self.request.link(PageMove.for_url_template())
        )

    def get_breadcrumbs(self, item):
        """ Yields the breadcrumbs for the given adjacency list item. """

        yield Link(_("Homepage"), self.homepage_url)

        for ancestor in item.ancestors:
            yield Link(ancestor.title, self.request.link(ancestor))

        yield Link(item.title, self.request.link(item))

    def get_sidebar(self, type=None):
        """ Yields the sidebar for the given adjacency list item. """
        query = self.model.siblings.filter(self.model.__class__.type == type)
        items = self.request.exclude_invisible(query.all())

        for item in items:
            if item != self.model:
                yield Link(item.title, self.request.link(item), model=item)
            else:
                children = (
                    Link(c.title, self.request.link(c), model=c) for c
                    in self.request.exclude_invisible(self.model.children)
                )

                yield LinkGroup(
                    title=item.title,
                    links=tuple(children),
                    model=item
                )


class PageLayout(AdjacencyListLayout):

    @cached_property
    def breadcrumbs(self):
        return tuple(self.get_breadcrumbs(self.model))

    @cached_property
    def sidebar_links(self):
        return tuple(self.get_sidebar(type='topic'))


class NewsLayout(AdjacencyListLayout):

    @cached_property
    def breadcrumbs(self):
        return tuple(self.get_breadcrumbs(self.model))


class EditorLayout(AdjacencyListLayout):

    def __init__(self, model, request, site_title):
        super().__init__(model, request)
        self.site_title = site_title
        self.include_editor()

    @cached_property
    def breadcrumbs(self):
        links = list(self.get_breadcrumbs(self.model.page))
        links.append(Link(self.site_title, url='#'))

        return links


class FormEditorLayout(DefaultLayout):

    def __init__(self, model, request):
        super().__init__(model, request)
        self.include_editor()
        self.include_code_editor()


class FormSubmissionLayout(DefaultLayout):

    def __init__(self, model, request, title=None):
        super().__init__(model, request)
        self.title = title or self.form.title

    @cached_property
    def form(self):
        if hasattr(self.model, 'form'):
            return self.model.form
        else:
            return self.model

    @cached_property
    def breadcrumbs(self):
        collection = FormCollection(self.request.app.session())

        return [
            Link(_("Homepage"), self.homepage_url),
            Link(_("Forms"), self.request.link(collection)),
            Link(self.title, '#')
        ]

    @cached_property
    def editbar_links(self):

        if not self.request.is_logged_in:
            return

        # only show the edit bar links if the site is the base of the form
        # -> if the user already entered some form data remove the edit bar
        # because it makes it seem like it's there to edit the submission,
        # not the actual form
        if hasattr(self.model, 'form'):
            return

        collection = FormCollection(self.request.app.session())

        edit_link = Link(
            text=_("Edit"),
            url=self.request.link(self.form, name='bearbeiten'),
            classes=('edit-link', )
        )

        if self.form.has_submissions(with_state='complete'):
            delete_link = DeleteLink(
                text=_("Delete"),
                url=self.request.link(self.form),
                confirm=_("This form can't be deleted."),
                extra_information=_(
                    "The are submissions associated with the form. "
                    "Those need to be removed first."
                )
            )

        else:
            delete_link = DeleteLink(
                text=_("Delete"),
                url=self.request.link(self.form),
                confirm=_("Do you really want to delete this form?"),
                yes_button_text=_("Delete form"),
                redirect_after=self.request.link(collection)
            )

        return [
            edit_link, delete_link
        ]


class FormCollectionLayout(DefaultLayout):

    @cached_property
    def breadcrumbs(self):
        return [
            Link(_("Homepage"), self.homepage_url),
            Link(_("Forms"), '#')
        ]

    @cached_property
    def editbar_links(self):
        if self.request.is_logged_in:
            return [
                LinkGroup(
                    title=_("Add"),
                    links=[
                        Link(
                            text=_("Form"),
                            url=self.request.link(
                                self.model,
                                name='neu'
                            ),
                            classes=('new-form', )
                        )
                    ]
                ),
            ]


class PersonCollectionLayout(DefaultLayout):

    @cached_property
    def breadcrumbs(self):
        return [
            Link(_("Homepage"), self.homepage_url),
            Link(_("People"), '#')
        ]

    @cached_property
    def editbar_links(self):
        if self.request.is_logged_in:
            return [
                LinkGroup(
                    title=_("Add"),
                    links=[
                        Link(
                            text=_("Person"),
                            url=self.request.link(
                                self.model,
                                name='neu'
                            ),
                            classes=('new-person', )
                        )
                    ]
                ),
            ]


class PersonLayout(DefaultLayout):

    @cached_property
    def collection(self):
        return PersonCollection(self.request.app.session())

    @cached_property
    def breadcrumbs(self):
        return [
            Link(_("Homepage"), self.homepage_url),
            Link(_("People"), self.request.link(self.collection)),
            Link(_(self.model.title), self.request.link(self.model))
        ]

    @cached_property
    def editbar_links(self):
        if self.request.is_logged_in:
            return [
                Link(
                    text=_("Edit"),
                    url=self.request.link(self.model, 'bearbeiten'),
                    classes=('edit-link', )
                ),
                DeleteLink(
                    text=_("Delete"),
                    url=self.request.link(self.model),
                    confirm=_(
                        "Do you really want to delete this person?"),
                    yes_button_text=_("Delete person"),
                    redirect_after=self.request.link(self.collection)
                )
            ]


class TicketsLayout(DefaultLayout):

    @cached_property
    def breadcrumbs(self):
        return [
            Link(_("Homepage"), self.homepage_url),
            Link(_("Tickets"), '#')
        ]


class TicketLayout(DefaultLayout):

    @cached_property
    def collection(self):
        return TicketCollection(self.request.app.session())

    @cached_property
    def breadcrumbs(self):
        return [
            Link(_("Homepage"), self.homepage_url),
            Link(_("Tickets"), self.request.link(self.collection)),
            Link(self.model.number, '#')
        ]

    @cached_property
    def editbar_links(self):
        if self.request.is_logged_in:

            # only show the model related links when the ticket is pending
            if self.model.state == 'pending':
                links = self.model.handler.get_links(self.request)
            else:
                links = []

            if self.model.state == 'open':
                links.append(Link(
                    text=_("Accept ticket"),
                    url=self.request.link(self.model, 'accept'),
                    classes=('ticket-button', 'ticket-accept'),
                ))

            elif self.model.state == 'pending':
                links.append(Link(
                    text=_("Close ticket"),
                    url=self.request.link(self.model, 'close'),
                    classes=('ticket-button', 'ticket-close'),
                ))

            elif self.model.state == 'closed':
                links.append(Link(
                    text=_("Reopen ticket"),
                    url=self.request.link(self.model, 'reopen'),
                    classes=('ticket-button', 'ticket-reopen'),
                ))

            return links


class ResourcesLayout(DefaultLayout):

    @cached_property
    def breadcrumbs(self):
        return [
            Link(_("Homepage"), self.homepage_url),
            Link(_("Reservations"), self.request.link(self.model))
        ]

    @cached_property
    def editbar_links(self):
        if self.request.is_logged_in:
            return [
                LinkGroup(
                    title=_("Add"),
                    links=[
                        Link(
                            text=_("Room"),
                            url=self.request.link(
                                self.model,
                                name='neuer-raum'
                            ),
                            classes=('new-room', )
                        ),
                        Link(
                            text=_("Daypass"),
                            url=self.request.link(
                                self.model,
                                name='neue-tageskarte'
                            ),
                            classes=('new-daypass', )
                        )
                    ]
                ),
            ]


class ResourceLayout(DefaultLayout):

    def __init__(self, model, request):
        super().__init__(model, request)

        self.request.include('fullcalendar')

    @cached_property
    def collection(self):
        return ResourceCollection(self.request.app.libres_context)

    @cached_property
    def breadcrumbs(self):
        return [
            Link(_("Homepage"), self.homepage_url),
            Link(_("Reservations"), self.request.link(self.collection)),
            Link(_(self.model.title), self.request.link(self.model))
        ]

    @cached_property
    def editbar_links(self):
        if self.request.is_logged_in:
            if self.model.deletable:
                delete_link = DeleteLink(
                    text=_("Delete"),
                    url=self.request.link(self.model),
                    confirm=_("Do you really want to delete this resource?"),
                    yes_button_text=_("Delete resource"),
                    redirect_after=self.request.link(self.collection)
                )

            else:
                delete_link = DeleteLink(
                    text=_("Delete"),
                    url=self.request.link(self.model),
                    confirm=_("This resource can't be deleted."),
                    extra_information=_(
                        "There are existing reservations associated "
                        "with this resource"
                    )
                )
            return [
                Link(
                    text=_("Edit"),
                    url=self.request.link(self.model, 'bearbeiten'),
                    classes=('edit-link', )
                ),
                delete_link,
                Link(
                    text=_("Clean up"),
                    url=self.request.link(self.model, 'cleanup'),
                    classes=('cleanup-link', 'calendar-dependent')
                ),
                Link(
                    text=_("Occupancy"),
                    url=self.request.link(self.model, 'belegung'),
                    classes=('occupancy-link', 'calendar-dependent')
                ),
                Link(
                    text=_("Export"),
                    url=self.request.link(self.model, 'export'),
                    classes=('export-link', 'calendar-dependent')
                )
            ]


class ReservationLayout(ResourceLayout):
    editbar_links = None


class AllocationEditFormLayout(DefaultLayout):
    """ Same as the resource layout, but with different editbar links, because
    there's not really an allocation view, but there are allocation forms.

    """

    @cached_property
    def collection(self):
        return ResourceCollection(self.request.app.libres_context)

    @cached_property
    def breadcrumbs(self):
        return [
            Link(_("Homepage"), self.homepage_url),
            Link(_("Reservations"), self.request.link(self.collection)),
            Link(_("Edit allocation"), '#')
        ]

    @cached_property
    def editbar_links(self):
        if self.request.is_logged_in:
            if self.model.availability == 100.0:
                yield DeleteLink(
                    _("Delete"),
                    self.request.link(self.model),
                    confirm=_("Do you really want to delete this allocation?"),
                    yes_button_text=_("Delete allocation"),
                    redirect_after=self.request.link(self.collection)
                )
            else:
                yield DeleteLink(
                    text=_("Delete"),
                    url=self.request.link(self.model),
                    confirm=_("This resource can't be deleted."),
                    extra_information=_(
                        "There are existing reservations associated "
                        "with this resource"
                    ),
                    redirect_after=self.request.link(self.collection)
                )


class EventBaseLayout(DefaultLayout):

    event_format = 'EEEE, d. MMMM YYYY, HH:mm'

    def format_recurrence(self, recurrence):
        """ Returns a human readable version of an RRULE used by us. """

        WEEKDAYS = (_("Mo"), _("Tu"), _("We"), _("Th"), _("Fr"), _("Sa"),
                    _("Su"))

        if recurrence:
            rule = rrule.rrulestr(recurrence)
            if rule._freq == rrule.WEEKLY:
                return _(
                    "Every ${days} until ${end}",
                    mapping={
                        'days': ', '.join((
                            self.request.translate(WEEKDAYS[day])
                            for day in rule._byweekday
                        )),
                        'end': rule._until.date().strftime('%d.%m.%Y')
                    }
                )

        return ''

    def event_deletable(self, event):
        tickets = TicketCollection(self.app.session())
        ticket = tickets.by_handler_id(event.id.hex)
        return False if ticket else True


class OccurrencesLayout(EventBaseLayout):

    @cached_property
    def breadcrumbs(self):
        return [
            Link(_("Homepage"), self.homepage_url),
            Link(_("Events"), self.request.link(self.model))
        ]


class OccurrenceLayout(EventBaseLayout):

    @cached_property
    def collection(self):
        return OccurrenceCollection(self.request.app.session())

    @cached_property
    def breadcrumbs(self):
        return [
            Link(_("Homepage"), self.homepage_url),
            Link(_("Events"), self.request.link(self.collection)),
            Link(self.model.title, '#')
        ]

    @cached_property
    def editbar_links(self):
        if self.request.is_logged_in:
            edit_url = URL(self.request.link(self.model.event, 'bearbeiten'))
            edit_url = edit_url.query_param(
                'return-to', self.request.link(self.model.event)
            )
            edit_link = Link(
                text=_("Edit"),
                url=edit_url.as_string(),
                classes=('edit-link', )
            )

            if self.event_deletable(self.model.event):
                delete_link = DeleteLink(
                    text=_("Delete"),
                    url=self.request.link(self.model.event),
                    confirm=_("Do you really want to delete this event?"),
                    yes_button_text=_("Delete event"),
                    redirect_after=self.events_url
                )
            else:
                delete_link = DeleteLink(
                    text=_("Delete"),
                    url=self.request.link(self.model.event),
                    confirm=_("This event can't be deleted."),
                    extra_information=_(
                        "To remove this event, go to the ticket and reject it."
                    )
                )

            return [edit_link, delete_link]


class EventLayout(EventBaseLayout):

    @cached_property
    def breadcrumbs(self):
        return [
            Link(_("Homepage"), self.homepage_url),
            Link(_("Events"), self.events_url),
            Link(self.model.title, self.request.link(self.model)),
        ]

    @cached_property
    def editbar_links(self):
        if self.request.is_logged_in:
            edit_link = Link(
                text=_("Edit"),
                url=self.request.link(self.model, 'bearbeiten'),
                classes=('edit-link', )
            )
            if self.event_deletable(self.model):
                delete_link = DeleteLink(
                    text=_("Delete"),
                    url=self.request.link(self.model),
                    confirm=_("Do you really want to delete this event?"),
                    yes_button_text=_("Delete event"),
                    redirect_after=self.events_url
                )
            else:
                delete_link = DeleteLink(
                    text=_("Delete"),
                    url=self.request.link(self.model),
                    confirm=_("This event can't be deleted."),
                    extra_information=_(
                        "To remove this event, go to the ticket and reject it."
                    )
                )

            return [edit_link, delete_link]


class NewsletterLayout(DefaultLayout):

    @cached_property
    def collection(self):
        return NewsletterCollection(self.app.session())

    @cached_property
    def recipients(self):
        return RecipientCollection(self.app.session())

    @cached_property
    def is_collection(self):
        return isinstance(self.model, NewsletterCollection)

    @cached_property
    def breadcrumbs(self):

        if self.is_collection and self.view_name == 'neu':
            return [
                Link(_("Homepage"), self.homepage_url),
                Link(_("Newsletter"), self.request.link(self.collection)),
                Link(_("New"), '#')
            ]
        elif self.is_collection:
            return [
                Link(_("Homepage"), self.homepage_url),
                Link(_("Newsletter"), '#')
            ]
        else:
            return [
                Link(_("Homepage"), self.homepage_url),
                Link(_("Newsletter"), self.request.link(self.collection)),
                Link(self.model.title, '#')
            ]

    @cached_property
    def editbar_links(self):
        if not self.request.is_logged_in:
            return

        if self.is_collection:
            return [
                Link(
                    text=_("Subscribers"),
                    url=self.request.link(self.recipients),
                    classes=('manage-subscribers', )
                ),
                LinkGroup(
                    title=_("Add"),
                    links=[
                        Link(
                            text=_("Newsletter"),
                            url=self.request.link(
                                NewsletterCollection(self.app.session()),
                                name='neu'
                            ),
                            classes=('new-newsletter', )
                        ),
                    ]
                ),
            ]
        else:
            return [
                Link(
                    text=_("Send"),
                    url=self.request.link(self.model, 'senden'),
                    classes=('send-link', )
                ),
                Link(
                    text=_("Edit"),
                    url=self.request.link(self.model, 'bearbeiten'),
                    classes=('edit-link', )
                ),
                DeleteLink(
                    text=_("Delete"),
                    url=self.request.link(self.model),
                    confirm=_(
                        'Do you really want to delete "{}"?'.format(
                            self.model.title
                        )),
                    yes_button_text=_("Delete newsletter"),
                    redirect_after=self.request.link(self.collection)
                )
            ]


class RecipientLayout(DefaultLayout):

    @cached_property
    def breadcrumbs(self):
        return [
            Link(_("Homepage"), self.homepage_url),
            Link(_("Newsletter"), self.request.link(
                NewsletterCollection(self.app.session())
            )),
            Link(_("Subscribers"), '#')
        ]


class ImageSetCollectionLayout(DefaultLayout):

    @cached_property
    def breadcrumbs(self):
        return [
            Link(_("Homepage"), self.homepage_url),
            Link(_("Photo Albums"), self.request.link(self.model))
        ]

    @cached_property
    def editbar_links(self):
        if self.request.is_logged_in:
            return [
                Link(
                    text=_("Manage images"),
                    url=self.request.link(ImageFileCollection(self.app)),
                    classes=('upload', )
                ),
                LinkGroup(
                    title=_("Add"),
                    links=[
                        Link(
                            text=_("Photo Album"),
                            url=self.request.link(
                                self.model,
                                name='neu'
                            ),
                            classes=('new-photo-album', )
                        )
                    ]
                ),
            ]


class ImageSetLayout(DefaultLayout):

    @property
    def collection(self):
        return ImageSetCollection(self.request.app.session())

    @cached_property
    def breadcrumbs(self):
        return [
            Link(_("Homepage"), self.homepage_url),
            Link(_("Photo Albums"), self.request.link(self.collection)),
            Link(self.model.title, self.request.link(self.model))
        ]

    @cached_property
    def editbar_links(self):
        if self.request.is_logged_in:
            return [
                Link(
                    text=_("Choose images"),
                    url=self.request.link(self.model, 'auswahl'),
                    classes=('select', )
                ),
                Link(
                    text=_("Edit"),
                    url=self.request.link(
                        self.model,
                        name='bearbeiten'
                    ),
                    classes=('edit-link', )
                ),
                DeleteLink(
                    text=_("Delete"),
                    url=self.request.link(self.model),
                    confirm=_(
                        'Do you really want to delete "{}"?'.format(
                            self.model.title
                        )),
                    yes_button_text=_("Delete photo album"),
                    redirect_after=self.request.link(self.collection)
                )
            ]
