# Description: Schema for the register form.
# Creation date: 2023-07-22
# Author: Michaël Launay

import colander
from pyramid.i18n import TranslationStringFactory
from deform import ValidationFailure
from deform import schema
from deform.widget import SelectWidget, TextInputWidget, DateInputWidget
from .. import _, EUROPEAN_LOCALES

locales_as_choices = [(key, value) for key, value in EUROPEAN_LOCALES.items()]

class RegisterForm(schema.CSRFSchema):
    """Register form schema."""
    fullname = colander.SchemaNode(
        colander.String(),
        title=_('full_name_as_in_id_label'),
        messages={'required': _('full_name_as_in_id_required')},
        missing=""
    )
    fullsurname = colander.SchemaNode(
        colander.String(),
        title=_('full_surname_as_in_id_label'),
        messages={'required': _('full_surname_as_in_id_required')},
        missing=""
    )
    #@TODO Gender (Mal, Femal, Undefined)
    birthdate = colander.SchemaNode(
        colander.Date(),
        title=_('birthdate_label'),
        messages={'required': _('birthdate_required')},
        widget=DateInputWidget(),
        validator=colander.Range(
            min=colander.Date('1900-01-01'),
            max=colander.Date('2023-12-31')
        ),
        missing=""
    )
    nationality = colander.SchemaNode(
        colander.String(),
        title=_('nationality_label'),
        messages={'required': _('nationality_required')},
        widget=SelectWidget(values=[
            ('', _('Select a country')),
            ('AT', _('Austria')),
            ('BE', _('Belgium')),
            ('BG', _('Bulgaria')),
            ('CY', _('Cyprus')),
            ('CZ', _('Czech Republic')),
            ('DE', _('Germany')),
            ('DK', _('Denmark')),
            ('EE', _('Estonia')),
            ('ES', _('Spain')),
            ('FI', _('Finland')),
            ('FR', _('France')),
            ('GR', _('Greece')),
            ('HR', _('Croatia')),
            ('HU', _('Hungary')),
            ('IE', _('Ireland')),
            ('IT', _('Italy')),
            ('LT', _('Lithuania')),
            ('LU', _('Luxembourg')),
            ('LV', _('Latvia')),
            ('MT', _('Malta')),
            ('NL', _('Netherlands')),
            ('PL', _('Poland')),
            ('PT', _('Portugal')),
            ('RO', _('Romania')),
            ('SE', _('Sweden')),
            ('SI', _('Slovenia')),
            ('SK', _('Slovakia')),
            ('UK', _('United Kingdom')),
            ('OTHER', _('Other (outside Europe)')),
        ]),
        missing=""
    )
    cooperative_number = colander.SchemaNode(
        colander.String(),
        title=_('cooperator_number_label'),
        widget=TextInputWidget(readonly=True),  # The field is visible but not editable
        messages={'required': _('cooperator_number_required')},
        missing=""
    )
    pseudonym = colander.SchemaNode(
        colander.String(),
        title=_('pseudonym_label'),
        widget=TextInputWidget(readonly=True),  # The field is visible but not editable
    )
    email = colander.SchemaNode(
        colander.String(),
        title=_('email_label'),
        widget=TextInputWidget(readonly=True),  # The field is visible but not editable
    )
    lang1 = colander.SchemaNode(
        colander.String(),
        title=_('first_interaction_language_label'),
        widget=SelectWidget(values=locales_as_choices),
        messages={'required': _('first_interaction_language_required')},
    )
    lang2 = colander.SchemaNode(
        colander.String(),
        title=_('second_interaction_language_label'),
        widget=SelectWidget(values=locales_as_choices),
    )

