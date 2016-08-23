import json
import onegov.core
import onegov.town
import pytest
import re
import textwrap
import transaction

from base64 import b64decode, b64encode
from datetime import datetime, date, timedelta
from libres.db.models import Reservation
from libres.modules.errors import AffectedReservationError
from lxml.html import document_fromstring
from onegov.core.utils import Bunch
from onegov.form import FormCollection, FormSubmission
from onegov.libres import ResourceCollection
from onegov.newsletter import RecipientCollection
from onegov.testing import utils
from onegov.ticket import TicketCollection
from onegov.user import UserCollection
from webtest import (
    TestApp as BaseApp,
    TestResponse as BaseResponse,
    TestRequest as BaseRequest
)
from webtest import Upload


class SkipFirstForm(object):

    @property
    def form(self):
        """ Ignore the first form, which is the general search form on
        the top of the page.

        """
        if len(self.forms) > 1:
            return self.forms[1]
        else:
            return super().form


class Response(SkipFirstForm, BaseResponse):
    pass


class Request(SkipFirstForm, BaseRequest):
    ResponseClass = Response


class Client(SkipFirstForm, BaseApp):
    RequestClass = Request

    def login(self, username, password, to):
        url = '/auth/login' + (to and ('/?to=' + to) or '')

        login_page = self.get(url)
        login_page.form.set('username', username)
        login_page.form.set('password', password)
        return login_page.form.submit()

    def login_admin(self, to=None):
        return self.login('admin@example.org', 'hunter2', to)

    def login_editor(self, to=None):
        return self.login('editor@example.org', 'hunter2', to)

    def logout(self):
        return self.get('/auth/logout')


def get_message(app, index, payload=0):
    message = app.smtp.outbox[index]
    message = message.get_payload(payload).get_payload(decode=True)
    return message.decode('iso-8859-1')


def extract_href(link):
    """ Takes a link (<a href...>) and returns the href address. """
    result = re.search(r'(?:href|ic-delete-from)="([^"]+)', link)

    return result and result.group(1) or None


def select_checkbox(page, groupname, label, form=None, checked=True):
    """ Selects one of many checkboxes by fuzzy searching the label next to
    it. Webtest is not good enough in this regard.

    Selects the checkbox from the form returned by page.form, or the given
    form if passed. In any case, the form needs to be part of the page.

    """

    elements = page.pyquery('input[name="{}"]'.format(groupname))
    form = form or page.form

    for ix, el in enumerate(elements):
        if label in el.label.text_content():
            form.get(groupname, index=ix).value = checked


def encode_map_value(dictionary):
    return b64encode(json.dumps(dictionary).encode('utf-8'))


def decode_map_value(value):
    return json.loads(b64decode(value).decode('utf-8'))


def bound_reserve(client, allocation):

    default_start = '{:%H:%M}'.format(allocation.start)
    default_end = '{:%H:%M}'.format(allocation.end)
    default_whole_day = allocation.whole_day
    resource = allocation.resource
    allocation_id = allocation.id

    def reserve(
        start=default_start,
        end=default_end,
        quota=1,
        whole_day=default_whole_day
    ):

        baseurl = '/einteilung/{}/{}/reserve'.format(
            resource,
            allocation_id
        )
        query = '?start={start}&end={end}&quota={quota}&whole_day={whole_day}'

        return client.post(baseurl + query.format(
            start=start,
            end=end,
            quota=quota,
            whole_day=whole_day and '1' or '0')
        )

    return reserve


def test_view_permissions():
    utils.assert_explicit_permissions(onegov.town, onegov.town.TownApp)


def test_startpage(town_app):
    client = Client(town_app)

    links = client.get('/').pyquery('.top-bar-section a')

    assert links[0].text == 'Bildung & Gesellschaft'
    assert links[0].attrib.get('href').endswith('/themen/bildung-gesellschaft')

    assert links[1].text == 'Gewerbe & Tourismus'
    assert links[1].attrib.get('href').endswith('/themen/gewerbe-tourismus')

    assert links[2].text == 'Kultur & Freizeit'
    assert links[2].attrib.get('href').endswith('/themen/kultur-freizeit')

    assert links[3].text == 'Leben & Wohnen'
    assert links[3].attrib.get('href').endswith('/themen/leben-wohnen')

    assert links[4].text == 'Politik & Verwaltung'
    assert links[4].attrib.get('href').endswith('/themen/politik-verwaltung')

    links = client.get('/').pyquery('.homepage-tiles a')

    assert links[0].find('h3').text == 'Bildung & Gesellschaft'
    assert links[0].attrib.get('href').endswith('/themen/bildung-gesellschaft')

    assert links[1].find('h3').text == 'Gewerbe & Tourismus'
    assert links[1].attrib.get('href').endswith('/themen/gewerbe-tourismus')

    assert links[2].find('h3').text == 'Kultur & Freizeit'
    assert links[2].attrib.get('href').endswith('/themen/kultur-freizeit')

    assert links[3].find('h3').text == 'Leben & Wohnen'
    assert links[3].attrib.get('href').endswith('/themen/leben-wohnen')

    assert links[4].find('h3').text == 'Politik & Verwaltung'
    assert links[4].attrib.get('href').endswith('/themen/politik-verwaltung')

    assert links[5].find('h3').text == 'Aktuelles'
    assert links[5].attrib.get('href').endswith('/aktuelles')


def test_settings(town_app):
    client = Client(town_app)

    assert client.get('/einstellungen', expect_errors=True).status_code == 403

    client.login_admin()

    settings_page = client.get('/einstellungen')
    document = settings_page.pyquery

    assert document.find('input[name=name]').val() == 'Govikon'
    assert document.find('input[name=primary_color]').val() == '#006fba'

    settings_page.form['primary_color'] = '#xxx'
    settings_page.form['reply_to'] = 'info@govikon.ch'
    settings_page = settings_page.form.submit()

    assert "Ungültige Farbe." in settings_page.text

    settings_page.form['primary_color'] = '#ccddee'
    settings_page.form['reply_to'] = 'info@govikon.ch'
    settings_page = settings_page.form.submit()

    assert "Ungültige Farbe." not in settings_page.text

    settings_page.form['logo_url'] = 'https://seantis.ch/logo.img'
    settings_page.form['reply_to'] = 'info@govikon.ch'
    settings_page = settings_page.form.submit()

    assert '<img src="https://seantis.ch/logo.img"' in settings_page.text

    settings_page.form['homepage_image_1'] = "http://images/one"
    settings_page.form['homepage_image_2'] = "http://images/two"
    settings_page = settings_page.form.submit()

    assert 'http://images/one' in settings_page
    assert 'http://images/two' in settings_page

    settings_page.form['analytics_code'] = '<script>alert("Hi!");</script>'
    settings_page = settings_page.form.submit()
    assert '<script>alert("Hi!");</script>' in settings_page.text


def test_view_occurrences_on_startpage(town_app):
    client = Client(town_app)
    links = [
        a.text for a in client.get('/').pyquery('.homepage-links-panel li a')
    ]
    events = (
        '150 Jahre Govikon',
        'Alle Veranstaltungen',
        'Gemeindeversammlung',
        'MuKi Turnen',
    )
    assert set(events) <= set(links)


def test_pages_on_homepage(es_town_app):
    client = Client(es_town_app)

    client.login_editor()

    new_page = client.get('/themen/bildung-gesellschaft').click('Thema')
    new_page.form['title'] = "0xdeadbeef"
    new_page = new_page.form.submit().follow()

    assert '0xdeadbeef' not in client.get('/')

    edit_page = new_page.click('Bearbeiten')
    edit_page.form['is_visible_on_homepage'] = True
    edit_page.form.submit()

    assert '0xdeadbeef' in client.get('/')

    edit_page = new_page.click('Bearbeiten')
    edit_page.form['is_hidden_from_public'] = True
    edit_page.form.submit()

    assert '0xdeadbeef' in client.get('/')
    assert '0xdeadbeef' not in Client(es_town_app).get('/')

    client.delete(
        new_page.pyquery('a[ic-delete-from]')[0].attrib['ic-delete-from']
    )

    assert '0xdeadbeef' not in client.get('/')


def test_unsubscribe_link(town_app):

    client = Client(town_app)

    user = UserCollection(town_app.session()).by_username('editor@example.org')
    assert user.data is None

    token = town_app.request_class.new_url_safe_token(Bunch(app=town_app), {
        'user': 'editor@example.org'
    }, salt='unsubscribe')

    client.get('/unsubscribe?token={}'.format(token))
    page = client.get('/')
    assert "abgemeldet" in page

    user = UserCollection(town_app.session()).by_username('editor@example.org')
    assert user.data['daily_ticket_statistics'] == False

    token = town_app.request_class.new_url_safe_token(Bunch(app=town_app), {
        'user': 'unknown@example.org'
    }, salt='unsubscribe')

    page = client.get(
        '/unsubscribe?token={}'.format(token), expect_errors=True)
    assert page.status_code == 403

    token = town_app.request_class.new_url_safe_token(Bunch(app=town_app), {
        'user': 'editor@example.org'
    }, salt='foobar')

    page = client.get(
        '/unsubscribe?token={}'.format(token), expect_errors=True)
    assert page.status_code == 403


def test_newsletters_crud(town_app):

    client = Client(town_app)
    client.login_editor()

    newsletter = client.get('/').click('Newsletter')
    assert 'Es wurden noch keine Newsletter versendet' in newsletter

    new = newsletter.click('Newsletter')
    new.form['title'] = "Our town is AWESOME"
    new.form['lead'] = "Like many of you, I just love our town..."

    select_checkbox(new, "news", "Willkommen bei OneGov")
    select_checkbox(new, "occurrences", "150 Jahre Govikon")
    select_checkbox(new, "occurrences", "MuKi Turnen")

    newsletter = new.form.submit().follow()

    assert newsletter.pyquery('h1').text() == "Our town is AWESOME"
    assert "Like many of you" in newsletter
    assert "Willkommen bei OneGov" in newsletter
    assert "Ihre neuer Online Schalter" in newsletter
    assert "MuKi Turnen" in newsletter
    assert "Turnhalle" in newsletter
    assert "150 Jahre Govikon" in newsletter
    assert "Sportanlage" in newsletter

    edit = newsletter.click("Bearbeiten")
    edit.form['title'] = "I can't even"
    select_checkbox(edit, "occurrences", "150 Jahre Govikon", checked=False)

    newsletter = edit.form.submit().follow()

    assert newsletter.pyquery('h1').text() == "I can't even"
    assert "Like many of you" in newsletter
    assert "Willkommen bei OneGov" in newsletter
    assert "Ihre neuer Online Schalter" in newsletter
    assert "MuKi Turnen" in newsletter
    assert "Turnhalle" in newsletter
    assert "150 Jahre Govikon" not in newsletter
    assert "Sportanlage" not in newsletter

    newsletters = client.get('/newsletters')
    assert "I can't even" in newsletters
    assert "Noch nicht gesendet." in newsletters

    # not sent, therefore not visible to the public
    assert "noch keine Newsletter" in Client(town_app).get('/newsletters')

    delete_link = newsletter.pyquery('a.delete-link').attr('ic-delete-from')
    client.delete(delete_link)

    newsletters = client.get('/newsletters')
    assert "noch keine Newsletter" in newsletters


def test_newsletter_signup(town_app):

    client = Client(town_app)

    page = client.get('/newsletters')
    page.form['address'] = 'asdf'
    page = page.form.submit()

    assert 'Ungültig' in page

    page.form['address'] = 'info@example.org'
    page.form.submit()

    assert len(town_app.smtp.outbox) == 1

    # make sure double submissions don't result in multiple e-mails
    page.form.submit()
    assert len(town_app.smtp.outbox) == 1

    message = town_app.smtp.outbox[0]
    message = message.get_payload(0).get_payload(decode=True)
    message = message.decode('utf-8')

    confirm = re.search(r'Anmeldung bestätigen\]\(([^\)]+)', message).group(1)

    # try an illegal token first
    illegal = confirm.split('/confirm')[0] + 'x/confirm'
    assert "falsches Token" in client.get(illegal).follow()

    # make sure double calls work
    assert "info@example.org wurde erfolgreich" in client.get(confirm).follow()
    assert "info@example.org wurde erfolgreich" in client.get(confirm).follow()

    # subscribing still works the same, but there's still no email sent
    page.form.submit()
    assert len(town_app.smtp.outbox) == 1

    # unsubscribing does not result in an e-mail either
    assert "falsches Token" in client.get(
        illegal.replace('/confirm', '/unsubscribe')
    ).follow()
    assert "erfolgreich abgemeldet" in client.get(
        confirm.replace('/confirm', '/unsubscribe')
    ).follow()

    # no e-mail is sent when unsubscribing
    assert len(town_app.smtp.outbox) == 1

    # however, we can now signup again
    page.form.submit()
    assert len(town_app.smtp.outbox) == 2


def test_newsletter_subscribers_management(town_app):

    client = Client(town_app)

    page = client.get('/newsletters')
    page.form['address'] = 'info@example.org'
    page.form.submit()

    assert len(town_app.smtp.outbox) == 1

    message = town_app.smtp.outbox[0]
    message = message.get_payload(0).get_payload(decode=True)
    message = message.decode('utf-8')

    confirm = re.search(r'Anmeldung bestätigen\]\(([^\)]+)', message).group(1)
    assert "info@example.org wurde erfolgreich" in client.get(confirm).follow()

    client.login_editor()

    subscribers = client.get('/abonnenten')
    assert "info@example.org" in subscribers

    unsubscribe = subscribers.pyquery('a[ic-get-from]').attr('ic-get-from')
    result = client.get(unsubscribe).follow()
    assert "info@example.org wurde erfolgreich abgemeldet" in result


def test_newsletter_send(town_app):
    client = Client(town_app)
    anon = Client(town_app)

    client.login_editor()

    # add a newsletter
    new = client.get('/').click('Newsletter').click('Newsletter')
    new.form['title'] = "Our town is AWESOME"
    new.form['lead'] = "Like many of you, I just love our town..."

    select_checkbox(new, "news", "Willkommen bei OneGov")
    select_checkbox(new, "occurrences", "150 Jahre Govikon")
    select_checkbox(new, "occurrences", "MuKi Turnen")

    newsletter = new.form.submit().follow()

    # add some recipients the quick wqy
    recipients = RecipientCollection(town_app.session())
    recipients.add('one@example.org', confirmed=True)
    recipients.add('two@example.org', confirmed=True)
    recipients.add('xxx@example.org', confirmed=False)

    transaction.commit()

    assert "2 Abonnenten registriert" in client.get('/newsletters')

    # send the newsletter to one recipient
    send = newsletter.click('Senden')
    assert "Dieser Newsletter wurde noch nicht gesendet." in send
    assert "one@example.org" in send
    assert "two@example.org" in send
    assert "xxx@example.org" not in send

    len(send.pyquery('input[name="recipients"]')) == 2

    select_checkbox(send, 'recipients', 'one@example.org', checked=True)
    select_checkbox(send, 'recipients', 'two@example.org', checked=False)

    newsletter = send.form.submit().follow()

    assert '"Our town is AWESOME" wurde an 1 Empfänger gesendet' in newsletter

    page = anon.get('/newsletters')
    assert "gerade eben" in page

    # the send form should now look different
    send = newsletter.click('Senden')

    assert "Zum ersten Mal gesendet gerade eben." in send
    assert "Dieser Newsletter wurde an 1 Abonnenten gesendet." in send
    assert "one@example.org" in send
    assert "two@example.org" in send
    assert "xxx@example.org" not in send

    assert len(send.pyquery('input[name="recipients"]')) == 1
    assert len(send.pyquery('.previous-recipients li')) == 1

    # send to the other mail adress
    send = send.form.submit().follow().click("Senden")
    assert "von allen Abonnenten empfangen" in send

    # make sure the mail was sent correctly
    assert len(town_app.smtp.outbox) == 2

    message = town_app.smtp.outbox[0]
    message = message.get_payload(0).get_payload(decode=True)
    message = message.decode('utf-8')

    assert "Our town is AWESOME" in message
    assert "Like many of you" in message

    web = re.search(r'Web-Version anzuzeigen.\]\(([^\)]+)', message).group(1)
    assert web.endswith('/newsletter/our-town-is-awesome')

    # make sure the unconfirm link is different for each mail
    unconfirm_1 = re.search(r'abzumelden.\]\(([^\)]+)', message).group(1)

    message = town_app.smtp.outbox[1]
    message = message.get_payload(0).get_payload(decode=True)
    message = message.decode('utf-8')

    unconfirm_2 = re.search(r'abzumelden.\]\(([^\)]+)', message).group(1)

    assert unconfirm_1 and unconfirm_2
    assert unconfirm_1 != unconfirm_2

    # make sure the unconfirm link actually works
    anon.get(unconfirm_1)
    assert recipients.query().count() == 2

    anon.get(unconfirm_2)
    assert recipients.query().count() == 1


def test_map_default_view(town_app):
    client = Client(town_app)
    client.login_admin()

    settings = client.get('/einstellungen')

    assert decode_map_value(settings.form['default_map_view'].value) == {
        'lat': None, 'lon': None, 'zoom': None
    }

    settings.form['default_map_view'] = encode_map_value({
        'lat': 47, 'lon': 8, 'zoom': 12
    })
    settings = settings.form.submit()

    assert decode_map_value(settings.form['default_map_view'].value) == {
        'lat': 47, 'lon': 8, 'zoom': 12
    }

    edit = client.get('/editor/edit/page/1')
    assert 'data-default-lat="47"' in edit
    assert 'data-default-lon="8"' in edit
    assert 'data-default-zoom="12"' in edit


def test_map_set_marker(town_app):
    client = Client(town_app)
    client.login_admin()

    edit = client.get('/editor/edit/page/1')
    assert decode_map_value(edit.form['coordinates'].value) == {
        'lat': None, 'lon': None, 'zoom': None
    }
    page = edit.form.submit().follow()

    assert 'marker-map' not in page

    edit = client.get('/editor/edit/page/1')
    edit.form['coordinates'] = encode_map_value({
        'lat': 47, 'lon': 8, 'zoom': 12
    })
    page = edit.form.submit().follow()

    assert 'marker-map' in page
    assert 'data-lat="47"' in page
    assert 'data-lon="8"' in page
    assert 'data-zoom="12"' in page


def test_manage_album(town_app):
    client = Client(town_app)
    client.login_editor()

    albums = client.get('/').click('Fotoalben')
    assert "Noch keine Fotoalben" in albums

    new = albums.click('Fotoalbum')
    new.form['title'] = "Comicon 2016"
    new.form.submit()

    albums = client.get('/').click('Fotoalben')
    assert "Comicon 2016" in albums

    album = albums.click("Comicon 2016")
    assert "Comicon 2016" in album
    assert "noch keine Bilder" in album

    images = albums.click("Bilder verwalten")
    images.form['file'] = Upload('test.jpg', utils.create_image().read())
    images.form.submit()

    select = album.click("Bilder auswählen")
    select.form[tuple(select.form.fields.keys())[1]] = True
    select.form.submit()

    album = albums.click("Comicon 2016")
    assert "noch keine Bilder" not in album

    images = albums.click("Bilder verwalten")

    url = re.search(r'data-note-update-url="([^"]+)"', images.text).group(1)
    client.post(url, {'note': "This is an alt text"})

    album = albums.click("Comicon 2016")
    assert "This is an alt text" in album
