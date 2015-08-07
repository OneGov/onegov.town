from onegov.core.security import Private
from onegov.town import _, TownApp
from onegov.town.models import SiteCollection


@TownApp.json(model=SiteCollection, permission=Private)
def get_site_collection(self, request):

    objects = self.get()

    collection = []

    collection.append({
        'group': request.translate(_("Topics")),
        'links': [
            {
                'title': obj.title,
                'url': request.link(obj)
            } for obj in objects['topics']
        ]
    })

    collection.append({
        'group': request.translate(_("Latest news")),
        'links': [
            {
                'title': obj.title,
                'url': request.link(obj)
            } for obj in objects['news']
        ]
    })

    collection.append({
        'group': request.translate(_("Forms")),
        'links': [
            {
                'title': obj.title,
                'url': request.link(obj)
            } for obj in objects['forms']
        ]
    })

    collection.append({
        'group': request.translate(_("Resources")),
        'links': [
            {
                'title': obj.title,
                'url': request.link(obj)
            } for obj in objects['resources']
        ]
    })

    return collection
