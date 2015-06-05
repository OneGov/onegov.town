""" Renders and handles defined forms, turning them into submissions. """

import morepath

from onegov.core.security import Public
from onegov.form import (
    FormCollection,
    FormDefinition,
    PendingFormSubmission,
    render_field
)
from onegov.town import _
from onegov.town.app import TownApp
from onegov.town.layout import FormSubmissionLayout


@TownApp.form(model=FormDefinition, form=lambda e: e.form_class,
              template='form.pt', permission=Public)
def handle_defined_form(self, request, form):
    """ Renders the empty form and takes input, even if it's not valid, stores
    it as a pending submission and redirects the user to the view that handles
    pending submissions.

    """

    collection = FormCollection(request.app.session())

    if request.POST:
        submission = collection.submissions.add(
            self.name, form, state='pending')

        return morepath.redirect(request.link(submission))

    return {
        'layout': FormSubmissionLayout(self, request),
        'title': self.title,
        'form': form,
        'form_width': 'small',
        'lead': self.meta.get('lead'),
        'text': self.content.get('text')
    }


@TownApp.html(model=PendingFormSubmission, template='submission.pt',
              permission=Public, request_method='GET')
@TownApp.html(model=PendingFormSubmission, template='submission.pt',
              permission=Public, request_method='POST')
def handle_pending_submission(self, request):
    """ Renders a pending submission, takes it's input and allows the
    user to turn the submission into a complete submission, once all data
    is valid.

    """
    collection = FormCollection(request.app.session())

    form = request.get_form(self.form_class, data=self.data)
    form.action = request.link(self)
    form.validate()

    if not request.POST:
        form.ignore_csrf_error()
    else:
        collection.submissions.update(self, form)

    completable = not form.errors and 'edit' not in request.GET

    return {
        'layout': FormSubmissionLayout(self, request),
        'title': self.form.title,
        'form': form,
        'completable': completable,
        'render_field': render_field,
        'edit_link': request.link(self) + '?edit',
        'complete_link': request.link(self, 'complete')
    }


@TownApp.view(model=PendingFormSubmission, name='complete', permission=Public,
              request_method='POST')
def handle_complete_submission(self, request):
    form = request.get_form(self.form_class, data=self.data)

    # we're not really using a csrf protected form here (the complete form
    # button is basically just there so we can use a POST instead of a GET)
    form.validate()
    form.ignore_csrf_error()

    if form.errors:
        return morepath.redirect(request.link(self))
    else:
        self.state = 'complete'

        # TODO Show a new page with the transaction id and a thank you
        request.success(_(u"Thank you for your submission"))

        collection = FormCollection(request.app.session())
        return morepath.redirect(request.link(collection))