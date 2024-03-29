# Description: Schema for the register form.
# Creation date: 2023-07-22
# Author: Michaël Launay
import datetime
import os
import colander
from deform import schema
from deform.widget import SelectWidget, TextInputWidget, DateInputWidget, FileUploadWidget
from alirpunkto.constants_and_globals import (
    _,
    EUROPEAN_LOCALES
)
from alirpunkto.utils import is_valid_password

locales_as_choices = [(key, value) for key, value in EUROPEAN_LOCALES.items()]

class RegisterForm(schema.CSRFSchema):
    """Register form schema."""
    fullname = colander.SchemaNode(
        colander.String(),
        title = _('full_name_as_in_id_label'),
        description = _('full_name_as_in_id_description'),
        messages = {'required': _('full_name_as_in_id_required')},
        missing = ""
    )
    fullsurname = colander.SchemaNode(
        colander.String(),
        title = _('full_surname_as_in_id_label'),
        description = _('full_surname_as_in_id_description'),
        messages = {'required': _('full_surname_as_in_id_required')},
        missing = ""
    )
    """ WIP
    @TODO define tempstore
    avatar = colander.SchemaNode(
        tmpstore=tmpstore, #@TODO create an IOCharSteam in temporary directory
        colander.String(),  # Use colander.String as the base field type.
        widget=FileUploadWidget(size=40,  # Define the input field size.
                                max_file_size=4096*1024,  # Limit the file size.
                                template='custom_file_upload_template'),  # Use a custom template if needed.
        missing = colander.drop,  # Use colander.drop to ignore the field if missing.
        title = _('Avatar')  # The field title for display.
    )
    """
    description = colander.SchemaNode(
        colander.String(),
        title = _('description_label'),
        description = _('description_description'),
        widget = TextInputWidget(maxlength=5000),
        missing = ""
    )
    birthdate = colander.SchemaNode(
        colander.Date(),
        title = _('birthdate_label'),
        description = _('birthdate_description'),
        messages = {'required': _('birthdate_required')},
        widget = DateInputWidget(),
        validator = colander.Range(
            min = datetime.date(1900, 1, 1),
            max = datetime.date(2020, 12, 31)
        ),
        missing = ""
    )
    nationality = colander.SchemaNode(
        colander.String(),
        title = _('nationality_label'),
        description = _('nationality_description'),
        messages = {'required': _('nationality_required')},
        widget = SelectWidget(values=[
            ('', _('select_a_country')),
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
        missing = ""
    )
    cooperative_number = colander.SchemaNode(
        colander.String(),
        title = _('cooperator_number_label'),
        description = _('cooperator_number_description'),
        widget = TextInputWidget(readonly = True),  # The field is visible but not editable
        messages = {'required': _('cooperator_number_required')},
        missing = ""
    )
    pseudonym = colander.SchemaNode(
        colander.String(),
        title = _('pseudonym_label'),
        description = _('pseudonym_description'),
        widget = TextInputWidget(),
        #validator = colander.Function(is_valid_unique_pseudonym),
        messages = {'required': _('pseudonym_required')},
        missing = ""
    )
    password = colander.SchemaNode(
        colander.String(),
        title = _('password_label'),
        description = _('password_description'),
        widget = TextInputWidget(type='password'),
        validator = colander.Function(is_valid_password),
        messages = {'required': _('password_required')},
        missing = ""
    )
    password_confirm = colander.SchemaNode(
        colander.String(),
        title = _('password_confirm_label'),
        description = _('password_confirm_description'),
        widget = TextInputWidget(type='password'),
        messages = {'required': _('confirm_password_required')},
        missing = ""
    )
    email = colander.SchemaNode(
        colander.String(),
        title = _('email_label'),
        description = _('email_description'),
        widget = TextInputWidget(readonly = True),  # The field is visible but not editable
    )
    lang1 = colander.SchemaNode(
        colander.String(),
        title = _('first_interaction_language_label'),
        description = _('first_interaction_language_description'),
        widget = SelectWidget(values=locales_as_choices),
        messages = {'required': _('first_interaction_language_required')},
    )
    lang2 = colander.SchemaNode(
        colander.String(),
        title = _('second_interaction_language_label'),
        description = _('second_interaction_language_description'),
        widget = SelectWidget(values=locales_as_choices),
    )
    lang3 = colander.SchemaNode(
        colander.String(),
        title = _('third_interaction_language_label'),
        description = _('third_interaction_language_description'),
        widget = SelectWidget(values=locales_as_choices),
    )
    cooperative_behaviour_mark = colander.SchemaNode(
        colander.Float(),
        title = _('cooperative_behaviour_mark_label'),
        description = _('cooperative_behaviour_mark_description'),
        widget = TextInputWidget(type='number', readonly = True),  # The field is visible but not editable
        missing=0.0
    )
    cooperative_behaviour_mark_update = colander.SchemaNode(
        colander.Date(),
        title = _('cooperative_behaviour_mark_update_label'),
        description = _('cooperative_behaviour_mark_update_description'),
        messages = {'required': _('cooperative_behaviour_mark_update_required')},
        widget = DateInputWidget(readonly = True),
        validator = colander.Range(
            min = datetime.date(2020, 1, 1)
        ),
        missing = ""
    )
    number_shares_owned = colander.SchemaNode(
        colander.Integer(),
        title = _('number_shares_owned_label'),
        description = _('number_shares_owned_description'),
        widget = TextInputWidget(readonly = True),  # The field is visible but not editable
        messages = {'required': _('number_shares_owned_required')},
        missing=0
    )
    date_end_validity_yearly_contribution = colander.SchemaNode(
        colander.Date(),
        title = _('date_end_validity_yearly_contribution_label'),
        description = _('date_end_validity_yearly_contribution_description'),
        messages = {'required': _('date_end_validity_yearly_contribution_required')},
        widget = DateInputWidget(readonly = True),
        validator = colander.Range(
            min = datetime.date(2020, 1, 1)
        ),
        missing = ""
    )
    iban = colander.SchemaNode(
        colander.String(),
        title = _('iban_label'),
        description = _('iban_description'),
        widget = TextInputWidget(),  # The field is visible but not editable
        messages = {'required': _('iban_required')},
        missing = ""
    )
    date_erasure_all_data = colander.SchemaNode(
        colander.Date(),
        title = _('date_erasure_all_data_title'),
        description = _('date_erasure_all_data_description'),
        widget = DateInputWidget(readonly = True),
        missing = ""
    )
    def prepare_for_ordinary(self):
        """Prepare the form for an ordinary user."""
        self.children.remove(self.get('fullname'))
        self.children.remove(self.get('fullsurname'))
        self.children.remove(self.get('birthdate'))
        self.children.remove(self.get('nationality'))
        self.children.remove(self.get('cooperative_behaviour_mark'))
        self.children.remove(self.get('cooperative_behaviour_mark_update'))
        self.children.remove(self.get('number_shares_owned'))
        self.children.remove(self.get('date_end_validity_yearly_contribution'))
        self.children.remove(self.get('iban'))

    def prepare_for_modification(self, read_only_fields: dict, writable_field_values: dict):
        """Prepare the form for an ordinary user."""
        if 'pseudonym' in read_only_fields:
            self.get('pseudonym').widget = TextInputWidget(readonly = True)
            self.get('pseudonym').widget.value = read_only_fields['pseudonym']
        elif 'pseudonym' in writable_field_values:
            self.get('pseudonym').widget.value = writable_field_values['pseudonym']
        else:
            self.children.remove(self.get('pseudonym'))
        if 'fullname' in read_only_fields:
            self.get('fullname').widget = TextInputWidget(readonly = True)
            self.get('fullname').widget.value = read_only_fields['fullname']
        elif 'fullname' in writable_field_values:
            self.get('fullname').widget.value = writable_field_values['fullname']
        else:
            self.children.remove(self.get('fullname'))
        if 'fullsurname' in read_only_fields:
            self.get('fullsurname').widget = TextInputWidget(readonly = True)
            self.get('fullsurname').widget.value = read_only_fields['fullsurname']
        elif 'fullsurname' in writable_field_values:
            self.get('fullsurname').widget.value = writable_field_values['fullsurname']
        else:
            self.children.remove(self.get('fullsurname'))
        if 'birthdate' in read_only_fields:
            self.get('birthdate').widget = DateInputWidget(readonly = True)
            self.get('birthdate').widget.value = read_only_fields['birthdate']
        elif 'birthdate' in writable_field_values:
            self.get('birthdate').widget.value = writable_field_values['birthdate']
        else:
            self.children.remove(self.get('birthdate'))
        if 'nationality' in read_only_fields:
            self.get('nationality').widget = SelectWidget(readonly = True)
            self.get('nationality').widget.value = read_only_fields['nationality']
        elif 'nationality' in writable_field_values:
            self.get('nationality').widget.value = writable_field_values['nationality']
        else:
            self.children.remove(self.get('nationality'))
        if 'lang1' in read_only_fields:
            self.get('lang1').widget = SelectWidget(readonly = True)
            self.get('lang1').widget.value = read_only_fields['lang1']
        elif 'lang1' in writable_field_values:
            self.get('lang1').widget.value = writable_field_values['lang1']
        else:
            self.children.remove(self.get('lang1'))
        if 'lang2' in read_only_fields:
            self.get('lang2').widget = SelectWidget(readonly = True)
            self.get('lang2').widget.value = read_only_fields['lang2']
        elif 'lang2' in writable_field_values:
            self.get('lang2').widget.value = writable_field_values['lang2']
        else:
            self.children.remove(self.get('lang2'))
        if 'lang3' in read_only_fields:
            self.get('lang3').widget = SelectWidget(readonly = True)
            self.get('lang3').widget.value = read_only_fields['lang3']
        elif 'lang3' in writable_field_values:
            self.get('lang3').widget.value = writable_field_values['lang3']
        else:
            self.children.remove(self.get('lang3'))
        if 'description' in read_only_fields:
            self.get('description').widget = TextInputWidget(readonly = True)
            self.get('description').widget.value = read_only_fields['description']
        elif 'description' in writable_field_values:
            self.get('description').widget.value = writable_field_values['description']
        else:
            self.children.remove(self.get('description'))
        if 'cooperative_behaviour_mark' in read_only_fields:
            self.get('cooperative_behaviour_mark').widget = SelectWidget(readonly = True)
            self.get('cooperative_behaviour_mark').widget.value = read_only_fields['cooperative_behaviour_mark']
        elif 'cooperative_behaviour_mark' in writable_field_values:
            self.get('cooperative_behaviour_mark').widget.value = writable_field_values['cooperative_behaviour_mark']
        else:
            self.children.remove(self.get('cooperative_behaviour_mark'))
        if 'cooperative_behaviour_mark_update' in read_only_fields:
            self.get('cooperative_behaviour_mark_update').widget = DateInputWidget(readonly = True)
            self.get('cooperative_behaviour_mark_update').widget.value = read_only_fields['cooperative_behaviour_mark_update']
        elif 'cooperative_behaviour_mark_update' in writable_field_values:
            self.get('cooperative_behaviour_mark_update').widget.value = writable_field_values['cooperative_behaviour_mark_update']
        else:
            self.children.remove(self.get('cooperative_behaviour_mark_update'))
        if 'number_shares_owned' in read_only_fields:
            self.get('number_shares_owned').widget = TextInputWidget(readonly = True)
            self.get('number_shares_owned').widget.value = read_only_fields['number_shares_owned']
        elif 'number_shares_owned' in writable_field_values:
            self.get('number_shares_owned').widget.value = writable_field_values['number_shares_owned']
        else:
            self.children.remove(self.get('number_shares_owned'))
        if 'date_end_validity_yearly_contribution' in read_only_fields:
            self.get('date_end_validity_yearly_contribution').widget = DateInputWidget(readonly = True)
            self.get('date_end_validity_yearly_contribution').widget.value = read_only_fields['date_end_validity_yearly_contribution']
        elif 'date_end_validity_yearly_contribution' in writable_field_values:
            self.get('date_end_validity_yearly_contribution').widget.value = writable_field_values['date_end_validity_yearly_contribution']
        else:
            self.children.remove(self.get('date_end_validity_yearly_contribution'))
        if 'iban' in read_only_fields:
            self.get('iban').widget = TextInputWidget(readonly = True)
            self.get('iban').widget.value = read_only_fields['iban']
        elif 'iban' in writable_field_values:
            self.get('iban').widget.value = writable_field_values['iban']
        else:
            self.children.remove(self.get('iban'))
        if 'date_erasure_all_data' in read_only_fields:
            self.get('date_erasure_all_data').widget = DateInputWidget(readonly = True)
            self.get('date_erasure_all_data').widget.value = read_only_fields['date_erasure_all_data']
        elif 'date_erasure_all_data' in writable_field_values:
            self.get('date_erasure_all_data').widget.value = writable_field_values['date_erasure_all_data']
        else:
            self.children.remove(self.get('date_erasure_all_data'))
        if 'password' in read_only_fields:
            self.get('password').widget = TextInputWidget(readonly = True)
            password = read_only_fields['password']
            self.get('password').widget.value = password if password else ""
        elif 'password' in writable_field_values:
            self.get('password').widget.value = writable_field_values['password']
        else:
            self.children.remove(self.get('password'))
        if 'password_confirm' in read_only_fields:
            self.get('password_confirm').widget = TextInputWidget(readonly = True)
            password_confirm = read_only_fields['password_confirm']
            self.get('password_confirm').widget.value = password_confirm if password_confirm else ""
        elif 'password_confirm' in writable_field_values:
            self.get('password_confirm').widget.value = writable_field_values['password_confirm']
        else:
            self.children.remove(self.get('password_confirm'))

        self.get('cooperative_number').widget = TextInputWidget(readonly = True)
        self.get('cooperative_number').widget.value = read_only_fields['cooperative_number']


