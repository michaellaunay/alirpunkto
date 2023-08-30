# Description: Schema for the register form.
# Creation date: 2023-07-22
# Author: Michaël Launay

import colander
from pyramid.i18n import TranslationStringFactory
from deform import ValidationFailure
from deform import schema
from deform.widget import SelectWidget, TextInputWidget, HiddenWidget
from .. import _


class RegisterForm(schema.CSRFSchema):
    """Register form schema."""
    fullname = colander.SchemaNode(
        colander.String(),
        title=_('full_name_as_in_id_label'),
        missing=""
    )
    #@TODO Gender (Mal, Femal, Undefined)
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


