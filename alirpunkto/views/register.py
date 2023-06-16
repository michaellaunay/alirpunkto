# In your Pyramid views.py

import deform
from deform import schema, ValidationFailure
from pyramid_handlers import action
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound

from pyramid.i18n import TranslationStringFactory
_ = TranslationStringFactory('alirpunkto')

import colander
import deform
from deform import schema

class RegisterForm(schema.CSRFSchema):
    fullname = colander.SchemaNode(
        colander.String(),
        title=_('Full name as in ID'),
        missing=""
    )
    birthdate = colander.SchemaNode(
        colander.Date(),
        title=_('Birthdate (Cooperators only)'),
        missing=""
    )
    nationality = colander.SchemaNode(
        colander.String(),
        title=_('Nationality (Cooperators only, EU countries)'),
        missing=""
    )
    cooperative_number = colander.SchemaNode(
        colander.String(),
        title=_('Cooperator number (Cooperators only)'),
        missing=""
    )
    pseudonym = colander.SchemaNode(
        colander.String(),
        title=_('Pseudonym'),
        validator=colander.Length(min=2)
    )
    email = colander.SchemaNode(
        colander.String(),
        title=_('Email'),
        validator=colander.Email()
    )
    lang1 = colander.SchemaNode(
        colander.String(),
        title=_('First interaction language'),
    )
    lang2 = colander.SchemaNode(
        colander.String(),
        title=_('Second interaction language'),
    )
    usual_name = colander.SchemaNode(
        colander.String(),
        title=_('Usual first name (Cooperators/Donators only)'),
        missing=""
    )
    usual_surname = colander.SchemaNode(
        colander.String(),
        title=_('Usual surname (Cooperators/Donators only)'),
        missing=""
    )
    postal_code = colander.SchemaNode(
        colander.String(),
        title=_('Postal code (Cooperators/Donators only)'),
        missing=""
    )
    city = colander.SchemaNode(
        colander.String(),
        title=_('City (Cooperators/Donators only)'),
        missing=""
    )
    country = colander.SchemaNode(
        colander.String(),
        title=_('Country (Cooperators/Donators only)'),
        missing=""
    )

    

class RegisterHandler(object):
    def __init__(self, request):
        self.request = request
        self.schema = RegisterForm().bind(request=self.request)

    @view_config(route_name='register', renderer='templates/register.pt')
    @action(renderer='templates/register.pt')
    def register(self):
        form = deform.Form(self.schema, buttons=('submit',))

        if 'submit' in self.request.POST:
            controls = self.request.POST.items()
            try:
                appstruct = form.validate(controls)
                # Utilisez appstruct pour créer un nouvel utilisateur ici...
                return HTTPFound(location=self.request.route_url('success'))
            except ValidationFailure as e:
                return {'form': e.render()}

        return {'form': form.render()}
