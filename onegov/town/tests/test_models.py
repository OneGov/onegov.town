import os

from onegov.core.utils import module_path, rchop
from onegov.org.models import SiteCollection


def test_sitecollection(town_app):

    sitecollection = SiteCollection(town_app.session())
    objects = sitecollection.get()

    assert {o.name for o in objects['topics']} == {
        'leben-wohnen',
        'kultur-freizeit',
        'bildung-gesellschaft',
        'gewerbe-tourismus',
        'politik-verwaltung'
    }

    assert {o.name for o in objects['news']} == {
        'aktuelles',
        'willkommen-bei-onegov'
    }

    builtin_forms_path = module_path('onegov.town', 'forms/builtin')

    paths = (p for p in os.listdir(builtin_forms_path))
    paths = (p for p in paths if p.endswith('.form'))
    paths = (os.path.basename(p) for p in paths)
    builtin_forms = set(rchop(p, '.form') for p in paths)

    assert {o.name for o in objects['forms']} == set(builtin_forms)
    assert {o.name for o in objects['resources']} == {'sbb-tageskarte'}
