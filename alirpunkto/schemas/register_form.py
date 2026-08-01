# Description: Schema for the register form.
# Creation date: 2024-04-19
# Author: Michaël Launay
from typing import Union
import copy
import datetime
import colander
from deform import schema
from deform.widget import SelectWidget, TextAreaWidget, TextInputWidget, DateInputWidget, PasswordWidget
from alirpunkto.constants_and_globals import (
    _,
    EUROPEAN_LOCALES,
    MIN_PSEUDONYM_LENGTH,
    MAX_PSEUDONYM_LENGTH,
    SITE_INFORMATION_MAPPING,
    MIN_PASSWORD_LENGTH,
    MAX_PASSWORD_LENGTH
)
from alirpunkto.utils import is_valid_password
from alirpunkto.models.permissions import Permissions
from alirpunkto.models.model_permissions import MemberDataPermissionsType, MemberPermissionsType
from dataclasses import fields

locales_as_choices = [(key, value) for key, value in EUROPEAN_LOCALES.items()]
optional_locales_as_choices = [
    ('', _('language_none_option')),
] + locales_as_choices

@colander.deferred
def deferred_password_missing(node, kw):
    """The password fields are mandatory except on profile modification.

    The schema also serves the profile-modification form, where an empty
    password means "unchanged": the fields are therefore required by default
    (registration, password reset) and optional only when the caller binds
    with password_optional=True — which also drives the mandatory-field
    asterisk, since deform derives it from the colander requirement
    (issue #107).
    """
    return '' if (kw or {}).get('password_optional') else colander.required


@colander.deferred
def deferred_preferred_language_default(node, kw):
    """Preselect the language negotiated for the request (issue #171).

    The selection list used to preselect its first entry — whatever locale
    the directory scan yielded first, "Esperanto" on the reporting
    deployment. The best guess at this stage of the registration is the
    browser language: the locale negotiator resolves Accept-Language when no
    explicit choice was made yet. Falls back to no preselection when the
    negotiated locale is not among the choices.
    """
    request = kw.get('request') if kw else None
    locale = getattr(request, 'locale_name', None) if request else None
    return locale if locale in EUROPEAN_LOCALES else colander.null


@colander.deferred
def deferred_birthdate_validator(node, kw):
    """Issue #80: resolved at bind time, request by request.

    The Range used to be built once at class definition — so
    ``get_majority_date()`` froze at process start, and after a few weeks
    of uptime the form refused candidates who had since come of age. A
    deferred validator recomputes the bound on every bind, and carries
    the ticket's own refusal message instead of colander's generic one.
    """
    return colander.Range(
        min=datetime.date(1900, 1, 1),
        max=get_majority_date(),
        max_err=_('cooperator_underage_error',
                  mapping=SITE_INFORMATION_MAPPING),
    )


def get_majority_date():
    """Return the date exactly 18 years ago (the latest birthdate of a major).

    Using `today - timedelta(days=365*18)` ignores leap years and is off by the
    4-5 leap days accumulated over 18 years, mis-classifying candidates born near
    their 18th birthday. `replace(year=...)` gives the true calendar date; the
    only edge case is a Feb 29 "today" whose target year is not a leap year, in
    which case we fall back to Feb 28.
    """
    today = datetime.date.today()
    try:
        return today.replace(year=today.year - 18)
    except ValueError:
        # today is Feb 29 and (today.year - 18) is not a leap year
        return today.replace(year=today.year - 18, day=28)


def _validate_password(value):
    """Adapt :func:`is_valid_password` to ``colander.Function``'s contract.

    ``colander.Function`` raises ``Invalid`` when the callback returns a falsy
    value or a string (used as the error message), and considers a truthy
    non-string result to be valid. ``is_valid_password`` does the opposite: it
    returns ``None`` when the password is valid and an error mapping otherwise.
    Return ``True`` when valid, and the error message (which colander turns into
    an ``Invalid``) when not.
    """
    error = is_valid_password(value)
    if error is None:
        return True
    return error.get('error', _('invalid_password'))


class RegisterForm(schema.CSRFSchema):
    """Register form schema."""
    fullname = colander.SchemaNode(
        colander.String(),
        title = _('full_name_as_in_id_label'),
        description = _('full_name_as_in_id_description',
            mapping=SITE_INFORMATION_MAPPING),
        messages = {'required': _('full_name_as_in_id_required',
            mapping=SITE_INFORMATION_MAPPING)},
        widget = TextInputWidget(maxlength=125),
        missing = ""
    )
    fullsurname = colander.SchemaNode(
        colander.String(),
        title = _('full_surname_as_in_id_label'),
        description = _('full_surname_as_in_id_description',
            mapping=SITE_INFORMATION_MAPPING),
        messages = {'required': _('full_surname_as_in_id_required',
            mapping=SITE_INFORMATION_MAPPING)},
        widget = TextInputWidget(maxlength=125),
        missing = ""
    )
    # The avatar lives outside this deform schema (issue #150):
    # uploaded as multipart to the avatar_upload view and stored as the
    # jpegPhoto LDAP attribute — no deform tmpstore needed.

    description = colander.SchemaNode(
        colander.String(),
        title = _('description_label'),
        description = _('description_description',
            mapping=SITE_INFORMATION_MAPPING),
        # A single-line input for a 5000-character profile text was
        # unusable (issue #165): a resizable 10-row textarea, with the
        # 5000-character limit now enforced server-side as well.
        widget = TextAreaWidget(rows=10, attributes={'maxlength': '5000'}),
        validator = colander.Length(max=5000),
        missing = ""
    )
    birthdate = colander.SchemaNode(
        colander.Date(),
        title = _('birthdate_label'),
        description = _('birthdate_description',
            mapping=SITE_INFORMATION_MAPPING),
        messages = {'required': _('birthdate_required',
            mapping=SITE_INFORMATION_MAPPING)},
        widget = DateInputWidget(),
        validator = deferred_birthdate_validator,
        missing = ""
    )
    nationality = colander.SchemaNode(
        colander.String(),
        title = _('nationality_label'),
        description = _('nationality_description',
            mapping={**SITE_INFORMATION_MAPPING,
                'MIN_PSEUDONYM_LENGTH': MIN_PSEUDONYM_LENGTH,
                'MAX_PSEUDONYM_LENGTH': MAX_PSEUDONYM_LENGTH}),
        messages = {'required': _('nationality_required',
            mapping={**SITE_INFORMATION_MAPPING,
                'MIN_PSEUDONYM_LENGTH': MIN_PSEUDONYM_LENGTH,
                'MAX_PSEUDONYM_LENGTH': MAX_PSEUDONYM_LENGTH})},
        widget = SelectWidget(values=[
            ('', _('select_a_country')),
            ('AT', _('Austria')),
            ('BE', _('Belgium')),
            ('BG', _('Bulgaria')),
            ('CY', _('Cyprus')),
            ('CZ', _('Czech_Republic')),
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
        description = _('cooperator_number_description',
            mapping=SITE_INFORMATION_MAPPING),
        widget = TextInputWidget(readonly = True),  # The field is visible but not editable
        messages = {'required': _('cooperator_number_required')},
    )
    pseudonym = colander.SchemaNode(
        colander.String(),
        title = _('pseudonym_label'),
        description = _('pseudonym_description',
            mapping={**SITE_INFORMATION_MAPPING,
                "MIN_PSEUDONYM_LENGTH":MIN_PSEUDONYM_LENGTH,
                "MAX_PSEUDONYM_LENGTH":MAX_PSEUDONYM_LENGTH}),
        widget = TextInputWidget(),
        #validator = colander.Function(is_valid_unique_pseudonym),
        messages = {'required': _('pseudonym_required')},
    )
    password = colander.SchemaNode(
        colander.String(),
        title = _('password_label'),
        description = _('password_description',
            mapping={**SITE_INFORMATION_MAPPING,
                "password_minimum_length":MIN_PASSWORD_LENGTH,
                "password_maximum_length":MAX_PASSWORD_LENGTH}),
        widget = PasswordWidget(),
        validator = colander.Function(_validate_password),
        messages = {'required': _('password_required')},
        missing = deferred_password_missing
    )
    # @TODO replace by the use of CheckedPasswordWidget
    password_confirm = colander.SchemaNode(
        colander.String(),
        title = _('password_confirm_label'),
        description = _('password_confirm_description',
            mapping=SITE_INFORMATION_MAPPING),
        widget = PasswordWidget(),
        messages = {'required': _('confirm_password_required')},
        missing = deferred_password_missing
    )
    email = colander.SchemaNode(
        colander.String(),
        title = _('email_label'),
        description = _('email_description',
            mapping=SITE_INFORMATION_MAPPING),
        widget = TextInputWidget(readonly = True),  # The field is visible but not editable
    )
    lang1 = colander.SchemaNode(
        colander.String(),
        title = _('first_interaction_language_label'),
        description = _('first_interaction_language_description',
            mapping=SITE_INFORMATION_MAPPING),
        widget = SelectWidget(values=locales_as_choices),
        default = deferred_preferred_language_default,
        messages = {'required': _('first_interaction_language_required')},
    )
    lang2 = colander.SchemaNode(
        colander.String(),
        title = _('second_interaction_language_label'),
        description = _('second_interaction_language_description',
            mapping=SITE_INFORMATION_MAPPING),
        widget = SelectWidget(
            values=optional_locales_as_choices,
            null_value='',
        ),
        missing='',
    )
    lang3 = colander.SchemaNode(
        colander.String(),
        title = _('third_interaction_language_label'),
        description = _('third_interaction_language_description',
            mapping=SITE_INFORMATION_MAPPING),
        widget = SelectWidget(
            values=optional_locales_as_choices,
            null_value='',
        ),
        missing='',
    )
    cooperative_behaviour_mark = colander.SchemaNode(
        colander.Float(),
        title = _('cooperative_behaviour_mark_label'),
        description = _('cooperative_behaviour_mark_description',
            mapping=SITE_INFORMATION_MAPPING),
        widget = TextInputWidget(hidden=True, type='number', readonly = True),  # The field is visible but not editable
        missing=0.0
    )
    cooperative_behaviour_mark_update = colander.SchemaNode(
        colander.Date(),
        title = _('cooperative_behaviour_mark_update_label'),
        description = _('cooperative_behaviour_mark_update_description',
            mapping=SITE_INFORMATION_MAPPING),
        messages = {'required': _('cooperative_behaviour_mark_update_required')},
        widget = DateInputWidget(hidden=True, readonly = True),
        validator = colander.Range(
            min = datetime.date(2020, 1, 1)
        ),
        missing = ""
    )
    number_shares_owned = colander.SchemaNode(
        colander.Integer(),
        title = _('number_shares_owned_label'),
        description = _('number_shares_owned_description',
            mapping=SITE_INFORMATION_MAPPING),
        widget = TextInputWidget(hidden=True, readonly = True),  # The field is visible but not editable
        messages = {'required': _('number_shares_owned_required')},
        missing=0
    )
    date_end_validity_yearly_contribution = colander.SchemaNode(
        colander.Date(),
        title = _('date_end_validity_yearly_contribution_label'),
        description = _('date_end_validity_yearly_contribution_description',
            mapping=SITE_INFORMATION_MAPPING),
        messages = {'required': _('date_end_validity_yearly_contribution_required')},
        widget = DateInputWidget(hidden=True, readonly = True),
        validator = colander.Range(
            min = datetime.date(2020, 1, 1)
        ),
        missing = ""
    )
    iban = colander.SchemaNode(
        colander.String(),
        title = _('iban_label'),
        description = _('iban_description',
            mapping=SITE_INFORMATION_MAPPING),
        widget = TextInputWidget(hidden=True, readonly=True),
        messages = {'required': _('iban_required')},
        missing = ""
    )
    date_erasure_all_data = colander.SchemaNode(
        colander.Date(),
        title = _('date_erasure_all_data_title'),
        description = _('date_erasure_all_data_description',
            mapping=SITE_INFORMATION_MAPPING),
        widget = DateInputWidget(hidden=True,readonly = True),
        missing = ""
    )
    def _use_instance_widgets(self):
        """Give this schema instance its own private widget copies.

        colander's ``clone()``/``bind()`` shallow-copies schema nodes: the
        ``widget`` attribute still points to the very object created at class
        definition time, shared by every ``RegisterForm`` instance in the
        process. Mutating ``widget.readonly``/``widget.hidden``/``widget.value``
        without copying first therefore leaks the current request's permission
        profile into every later render that does not re-apply permissions -
        the "pseudonym field read-only right after the e-mail challenge until
        a page refresh re-applies permissions" symptom.

        Called before any widget mutation so the flags stay per-instance and
        per-request. Idempotent (copying a copy is harmless) and thread-safe
        for the shared class-level widgets, which are now never written to.
        """
        for child in self.children:
            widget = getattr(child, 'widget', None)
            if widget is not None:
                child.widget = copy.copy(widget)

    def apply_permissions(
            self,
            permissions: Union[MemberPermissionsType, MemberDataPermissionsType],
            force_permissions: dict[str, Permissions] = {'password_confirm': Permissions.ACCESS, 'password': Permissions.ACCESS}
        ):
        """
        Apply permissions to the form fields based on the provided permissions and force permissions.

        This method iterates over the form fields and applies the specified permissions to each field. It also considers
        any force permissions that need to be applied regardless of the provided permissions.

        Args:
            permissions (Union[MemberPermission, MemberDataPermissionsType]): An object or dictionary containing the permissions for each form field.
            force_permissions (dict[str, Permissions], optional): A dictionary of force permissions that override the
                provided permissions for specific fields. The default is to grant ACCESS permission to the 'password_confirm'
                and 'password' fields.

        Example:
            Given a permissions object with read and write permissions for specific fields, and an optional dictionary of
            force permissions, this method will set the appropriate access and visibility settings for each form field.

        Note:
            - If a field's permission is set to `Permissions.NONE`, the field will be removed from the form.
            - If a field's permission includes `Permissions.WRITE`, the field will be editable.
            - If a field's permission includes `Permissions.READ`, the field will be visible but not editable.
            - Force permissions take precedence over the provided permissions and ensure that specific fields have the desired
            access level.

        Raises:
            KeyError: If a specified field in the permissions or force_permissions is not present in the form.
            TypeError: If the permissions argument is not of the expected type.

        Implementation Details:
            - The method first creates a dictionary of form children keyed by their names.
            - It then iterates over the fields in the permissions object.
            - For each field, it retrieves the corresponding form attribute.
            - If a force permission exists for the field, it overrides the provided permission.
            - Based on the determined permission, the form attribute's visibility and editability are set accordingly:
                - If the permission is `Permissions.NONE`, the field is removed from the form.
                - If the permission includes `Permissions.WRITE`, the field is set to editable and visible.
                - If the permission includes `Permissions.READ` but not `Permissions.WRITE`, the field is set to read-only and visible.
                - If the permission includes neither `Permissions.READ` nor `Permissions.WRITE`, the field is hidden and read-only.
        """
        self._use_instance_widgets()
        children = {child.name: child for child in self.children}
        for field in fields(permissions):
            name = field.name
            attribute = children.get(name, None)
            if attribute:
                permission = getattr(permissions, name, None)
                if name in force_permissions:
                    permission = force_permissions[name]
                # Permissions may not contain all the children
                if permission == None:
                    continue
                if permission == Permissions.NONE:
                    self.children.remove(attribute)
                elif attribute.widget:
                    if ((permission & Permissions.ACCESS) and
                        (permission & Permissions.READ) and
                        (permission & Permissions.WRITE)):
                        attribute.widget.readonly = False
                        attribute.widget.hidden = False
                    elif ((permission & Permissions.ACCESS) and
                        (permission & Permissions.READ)):
                        attribute.widget.hidden = False
                        attribute.widget.readonly = True
                    else:
                        attribute.widget.hidden = True
                        attribute.widget.readonly = True

    def prepare_for_ordinary(self):
        """Prepare the form for an ordinary user."""
        field_names = [item.name for item in self.children]
        if 'fullname' in field_names:
            self.children.remove(self.get('fullname'))
        if 'fullsurname' in field_names:
            self.children.remove(self.get('fullsurname'))
        if 'birthdate' in field_names:
            self.children.remove(self.get('birthdate'))
        if 'nationality' in field_names:
            self.children.remove(self.get('nationality'))
        if 'cooperative_behaviour_mark' in field_names:
            self.children.remove(self.get('cooperative_behaviour_mark'))
        if 'cooperative_behaviour_mark_update' in field_names:
            self.children.remove(self.get('cooperative_behaviour_mark_update'))
        if 'number_shares_owned' in field_names:
            self.children.remove(self.get('number_shares_owned'))
        if 'date_end_validity_yearly_contribution' in field_names:
            self.children.remove(self.get('date_end_validity_yearly_contribution'))
        if 'iban' in field_names:
            self.children.remove(self.get('iban'))

    def prepare_for_modification(self, read_only_fields: dict, writable_field_values: dict):
        """Prepare the form for an ordinary user."""
        self._use_instance_widgets()
        if 'pseudonym' in read_only_fields:
            self.get('pseudonym').widget.readonly = True
            self.get('pseudonym').widget.value = read_only_fields['pseudonym']
        elif 'pseudonym' in writable_field_values:
            self.get('pseudonym').widget.readonly = False
            self.get('pseudonym').widget.value = writable_field_values['pseudonym']
        else:
            self.children.remove(self.get('pseudonym'))

        if 'fullname' in read_only_fields:
            self.get('fullname').widget.readonly = True
            self.get('fullname').widget.value = read_only_fields['fullname']
        elif 'fullname' in writable_field_values:
            self.get('fullname').widget.readonly = False
            self.get('fullname').widget.value = writable_field_values['fullname']
        else:
            self.children.remove(self.get('fullname'))

        if 'fullsurname' in read_only_fields:
            self.get('fullsurname').widget.readonly = True
            self.get('fullsurname').widget.value = read_only_fields['fullsurname']
        elif 'fullsurname' in writable_field_values:
            self.get('fullsurname').widget.readonly = False
            self.get('fullsurname').widget.value = writable_field_values['fullsurname']
        else:
            self.children.remove(self.get('fullsurname'))

        if 'birthdate' in read_only_fields:
            self.get('birthdate').widget.readonly = True
            self.get('birthdate').widget.value = read_only_fields['birthdate']
        elif 'birthdate' in writable_field_values:
            self.get('birthdate').widget.readonly = False
            self.get('birthdate').widget.value = writable_field_values['birthdate']
        else:
            self.children.remove(self.get('birthdate'))

        if 'nationality' in read_only_fields:
            self.get('nationality').widget.readonly = True
            self.get('nationality').widget.value = read_only_fields['nationality']
        elif 'nationality' in writable_field_values:
            self.get('nationality').widget.readonly = False
            self.get('nationality').widget.value = writable_field_values['nationality']
        else:
            self.children.remove(self.get('nationality'))

        if 'lang1' in read_only_fields:
            self.get('lang1').widget.readonly = True
            self.get('lang1').widget.value = read_only_fields['lang1']
        elif 'lang1' in writable_field_values:
            self.get('lang1').widget.readonly = False
            self.get('lang1').widget.value = writable_field_values['lang1']
        else:
            self.children.remove(self.get('lang1'))

        if 'lang2' in read_only_fields:
            self.get('lang2').widget.readonly = True
            self.get('lang2').widget.value = read_only_fields['lang2']
        elif 'lang2' in writable_field_values:
            self.get('lang2').widget.readonly = False
            self.get('lang2').widget.value = writable_field_values['lang2']
        else:
            self.children.remove(self.get('lang2'))

        if 'lang3' in read_only_fields:
            self.get('lang3').widget.readonly = True
            self.get('lang3').widget.value = read_only_fields['lang3']
        elif 'lang3' in writable_field_values:
            self.get('lang3').widget.readonly = False
            self.get('lang3').widget.value = writable_field_values['lang3']
        else:
            self.children.remove(self.get('lang3'))

        if 'description' in read_only_fields:
            self.get('description').widget.readonly = True
            self.get('description').widget.value = read_only_fields['description']
        elif 'description' in writable_field_values:
            self.get('description').widget.readonly = False
            self.get('description').widget.value = writable_field_values['description']
        else:
            self.children.remove(self.get('description'))

        if 'cooperative_behaviour_mark' in read_only_fields:
            self.get('cooperative_behaviour_mark').widget.readonly = True
            self.get('cooperative_behaviour_mark').widget.value = read_only_fields['cooperative_behaviour_mark']
        elif 'cooperative_behaviour_mark' in writable_field_values:
            self.get('cooperative_behaviour_mark').widget.readonly = False
            self.get('cooperative_behaviour_mark').widget.value = writable_field_values['cooperative_behaviour_mark']
        else:
            self.children.remove(self.get('cooperative_behaviour_mark'))

        if 'cooperative_behaviour_mark_update' in read_only_fields:
            self.get('cooperative_behaviour_mark_update').widget.readonly = True
            self.get('cooperative_behaviour_mark_update').widget.value = read_only_fields['cooperative_behaviour_mark_update']
        elif 'cooperative_behaviour_mark_update' in writable_field_values:
            self.get('cooperative_behaviour_mark_update').widget.readonly = False
            self.get('cooperative_behaviour_mark_update').widget.value = writable_field_values['cooperative_behaviour_mark_update']
        else:
            self.children.remove(self.get('cooperative_behaviour_mark_update'))

        if 'number_shares_owned' in read_only_fields:
            self.get('number_shares_owned').widget.readonly = True
            self.get('number_shares_owned').widget.value = read_only_fields['number_shares_owned']
        elif 'number_shares_owned' in writable_field_values:
            self.get('number_shares_owned').widget.readonly = False
            self.get('number_shares_owned').widget.value = writable_field_values['number_shares_owned']
        else:
            self.children.remove(self.get('number_shares_owned'))

        if 'date_end_validity_yearly_contribution' in read_only_fields:
            self.get('date_end_validity_yearly_contribution').widget.readonly = True
            self.get('date_end_validity_yearly_contribution').widget.value = read_only_fields['date_end_validity_yearly_contribution']
        elif 'date_end_validity_yearly_contribution' in writable_field_values:
            self.get('date_end_validity_yearly_contribution').widget.readonly = False
            self.get('date_end_validity_yearly_contribution').widget.value = writable_field_values['date_end_validity_yearly_contribution']
        else:
            self.children.remove(self.get('date_end_validity_yearly_contribution'))

        if 'iban' in read_only_fields:
            self.get('iban').widget.readonly = True
            self.get('iban').widget.value = read_only_fields['iban']
        elif 'iban' in writable_field_values:
            self.get('iban').widget.readonly = False
            self.get('iban').widget.value = writable_field_values['iban']
        else:
            self.children.remove(self.get('iban'))

        if 'date_erasure_all_data' in read_only_fields:
            self.get('date_erasure_all_data').widget.readonly = True
            self.get('date_erasure_all_data').widget.value = read_only_fields['date_erasure_all_data']
        elif 'date_erasure_all_data' in writable_field_values:
            self.get('date_erasure_all_data').widget.readonly = False
            self.get('date_erasure_all_data').widget.value = writable_field_values['date_erasure_all_data']
        else:
            self.children.remove(self.get('date_erasure_all_data'))

        if 'email' in read_only_fields:
            self.get('email').widget.readonly = True
            self.get('email').widget.value = read_only_fields['email']
        elif 'email' in writable_field_values:
            self.get('email').widget.readonly = False
            self.get('email').widget.value = writable_field_values['email']
        else:
            self.children.remove(self.get('email'))

        if 'password' in read_only_fields:
            self.get('password').widget.readonly = True
            password = read_only_fields['password']
            self.get('password').widget.value = password if password else ""
        elif 'password' in writable_field_values:
            self.get('password').widget.readonly = False
            self.get('password').widget.value = writable_field_values['password']
        else:
            self.children.remove(self.get('password'))

        if 'password_confirm' in read_only_fields:
            self.get('password_confirm').widget.readonly = True
            password_confirm = read_only_fields['password_confirm']
            self.get('password_confirm').widget.value = password_confirm if password_confirm else ""
        elif 'password_confirm' in writable_field_values:
            self.get('password_confirm').widget.readonly = False
            self.get('password_confirm').widget.value = writable_field_values['password_confirm']
        else:
            self.children.remove(self.get('password_confirm'))

        self.get('cooperative_number').widget.readonly = True
        self.get('cooperative_number').widget.value = read_only_fields['cooperative_number']
