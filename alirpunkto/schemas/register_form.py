# Description: Schema for the register form.
# Creation date: 2023-07-22
# Author: Michaël Launay
import datetime
import colander
from pyramid.i18n import TranslationStringFactory
from deform import ValidationFailure
from deform import schema
from deform.widget import SelectWidget, TextInputWidget, DateInputWidget
from alirpunkto.constants_and_globals import (
    _,
    EUROPEAN_LOCALES
)
from alirpunkto.utils import is_valid_password, is_valid_unique_pseudonym

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
    birthdate = colander.SchemaNode(
        colander.Date(),
        title=_('birthdate_label'),
        messages={'required': _('birthdate_required')},
        widget=DateInputWidget(),
        validator=colander.Range(
            min=datetime.date(1900, 1, 1),
            max=datetime.date(2020, 12, 31)
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
        widget=TextInputWidget(),
        #validator=colander.Function(is_valid_unique_pseudonym),
        messages={'required': _('pseudonym_required')},
        missing=""
    )
    password = colander.SchemaNode(
        colander.String(),
        title=_('password_label'),
        widget=TextInputWidget(type='password'),
        validator=colander.Function(is_valid_password),
        messages={'required': _('password_required')},
        missing=""
    )
    password_confirm = colander.SchemaNode(
        colander.String(),
        title=_('password_confirm_label'),
        widget=TextInputWidget(type='password'),
        messages={'required': _('confirm_password_required')},
        missing=""
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
    def prepare_for_ordinary(self):
        """Prepare the form for an ordinary user."""
        self.children.remove(self.get('fullname'))
        self.children.remove(self.get('fullsurname'))
        self.children.remove(self.get('birthdate'))
        self.children.remove(self.get('nationality'))
        self.children.remove(self.get('lang1'))
        self.children.remove(self.get('lang2'))

