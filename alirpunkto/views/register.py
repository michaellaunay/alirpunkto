# description: Register view
# author: Michaël Launay
# date: 2023-06-15


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
    """Register form schema."""
    fullname = colander.SchemaNode(
        colander.String(),
        title=_('full_name_as_in_id_label'),
        missing=""
    )
    birthdate = colander.SchemaNode(
        colander.Date(),
        title=_('birthdate_label'),
        missing=""
    )
    nationality = colander.SchemaNode(
        colander.String(),
        title=_('nationality_label'),
        missing=""
    )
    cooperative_number = colander.SchemaNode(
        colander.String(),
        title=_('cooperator_number_label'),
        missing=""
    )
    pseudonym = colander.SchemaNode(
        colander.String(),
        title=_('pseudonym_label'),
        validator=colander.Length(min=2)
    )
    email = colander.SchemaNode(
        colander.String(),
        title=_('email_label'),
        validator=colander.Email()
    )
    lang1 = colander.SchemaNode(
        colander.String(),
        title=_('first_interaction_language_label'),
    )
    lang2 = colander.SchemaNode(
        colander.String(),
        title=_('second_interaction_language_label'),
    )
    usual_name = colander.SchemaNode(
        colander.String(),
        title=_('usual_first_name_label'),
        missing=""
    )
    usual_surname = colander.SchemaNode(
        colander.String(),
        title=_('usual_surname_label'),
        missing=""
    )
    postal_code = colander.SchemaNode(
        colander.String(),
        title=_('postal_code_label'),
        missing=""
    )
    city = colander.SchemaNode(
        colander.String(),
        title=_('city_label'),
        missing=""
    )
    country = colander.SchemaNode(
        colander.String(),
        title=_('country_label'),
        missing=""
    )

    

class RegisterHandler(object):
    def __init__(self, request):
        self.request = request
        self.schema = RegisterForm().bind(request=self.request)

    @view_config(route_name='register', renderer='alirpunkto:templates/register.pt')
    @action(renderer='alirpunkto:templates/register.pt')
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
