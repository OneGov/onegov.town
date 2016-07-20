import morepath

from onegov.core.security import Public, Private
from onegov.town import _
from onegov.town.app import TownApp
from onegov.town.models import ImageSet, ImageSetCollection
from onegov.town.layout import ImageSetLayout, ImageSetCollectionLayout
from onegov.town.forms import ImageSetForm
from onegov.town.elements import Link
from unidecode import unidecode


def get_form_class(self, request):
    if isinstance(self, ImageSetCollection):
        model = ImageSet()
    else:
        model = self

    return model.with_content_extensions(ImageSetForm, request)


@TownApp.html(model=ImageSetCollection, template='imagesets.pt',
              permission=Public)
def view_imagesets(self, request):

    # XXX add collation support to the core (create collations automatically)
    imagesets = self.query().all()
    imagesets = sorted(imagesets, key=lambda d: unidecode(d.title))

    return {
        'layout': ImageSetCollectionLayout(self, request),
        'title': _("Photo Albums"),
        'imagesets': request.exclude_invisible(imagesets)
    }


@TownApp.form(model=ImageSetCollection, name='neu', template='form.pt',
              permission=Public, form=get_form_class)
def handle_new_imageset(self, request, form):

    if form.submitted(request):
        imageset = self.add(title=form.title.data)
        form.populate_obj(imageset)
        request.success(_("Added a new photo album"))

        return morepath.redirect(request.link(imageset))

    layout = ImageSetCollectionLayout(self, request)
    layout.include_editor()
    layout.breadcrumbs.append(Link(_("New"), '#'))

    return {
        'layout': layout,
        'title': _("New Photo Album"),
        'form': form,
    }


@TownApp.form(model=ImageSet, name='bearbeiten', template='form.pt',
              permission=Private, form=get_form_class)
def handle_edit_resource(self, request, form):
    if form.submitted(request):
        form.populate_obj(self)

        request.success(_("Your changes were saved"))
        return morepath.redirect(request.link(self))

    elif not request.POST:
        form.process(obj=self)

    layout = ImageSetLayout(self, request)
    layout.include_editor()
    layout.breadcrumbs.append(Link(_("Edit"), '#'))

    return {
        'layout': layout,
        'title': self.title,
        'form': form
    }


@TownApp.view(model=ImageSet, request_method='DELETE', permission=Private)
def handle_delete_resource(self, request):
    collection = ImageSetCollection(request.app.session())
    collection.delete(self)


@TownApp.html(model=ImageSet, template='imageset.pt', permission=Public)
def view_imageset(self, request):

    return {
        'layout': ImageSetLayout(self, request),
        'title': self.title,
        'imageset': self
    }
