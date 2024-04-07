# 

from permissions import Permissions
from dataclasses import make_dataclass
from typing import Type, Final
from member import MemberStates, MemberDatas, Member

# MemberDataPermissions is a frozen dataclass that stores the permissions for
# each attribute of the MemberDatas dataclass.
MemberDataPermissions = make_dataclass(
    "MemberDataPermissions",
    [(name, Permissions, Permissions.NONE)
        for name in MemberDatas.get_field_names()],
    frozen=True
)
MemberDataPermissionsType = Type[MemberDataPermissions]

# NO_MEMBER_DATA_PERMISSIONS is a MemberDataPermissions instance with all
# permissions set to NONE.
# It can be used for testing if a MemberDataPermissions instance has no
# permissions.
NO_MEMBER_DATA_PERMISSIONS : Final = MemberDataPermissions()

def define_member_data_permissions(
    fullname=Permissions.NONE,
    fullsurname=Permissions.NONE,
    description=Permissions.NONE,
    nationality=Permissions.NONE,
    birthdate=Permissions.NONE,
    password=Permissions.NONE,
    password_confirm=Permissions.NONE,
    lang1=Permissions.NONE,
    lang2=Permissions.NONE,
    lang3=Permissions.NONE,
    cooperative_behaviour_mark=Permissions.NONE,
    cooperative_behaviour_mark_updated=Permissions.NONE,
    number_shares_owned=Permissions.NONE,
    date_end_validity_yearly_contribution=Permissions.NONE,
    iban=Permissions.NONE,
    role=Permissions.NONE        
    ) -> MemberDataPermissionsType:
    """Define the permissions for a member data.
    """
    if all(value == Permissions.NONE for value in [
        fullname, fullsurname, description, nationality, birthdate,
        password, password_confirm, lang1, lang2, lang3,
        cooperative_behaviour_mark, cooperative_behaviour_mark_updated,
        number_shares_owned, date_end_validity_yearly_contribution,
        iban, role]):
        # If all permissions are NONE return NO_DATA_PERMISSIONS
        # for allowing instance comparison (faster than comparing all values)
        return NO_MEMBER_DATA_PERMISSIONS
    else :
        return MemberDataPermissions(
            fullname=fullname,
            fullsurname=fullsurname,
            description=description,
            nationality=nationality
            birthdate=birthdate,
            password=password,
            password_confirm=password_confirm,
            lang1=lang1,
            lang2=lang2,
            lang3=lang3,
            cooperative_behaviour_mark=cooperative_behaviour_mark,
            cooperative_behaviour_mark_updated=cooperative_behaviour_mark_updated,
            number_shares_owned=number_shares_owned,
            date_end_validity_yearly_contribution=date_end_validity_yearly_contribution,
            iban=iban,
            role=role
        )

# MemberPermissions is a frozen dataclass that stores the permissions for each
# attribute of the Member dataclass.
MemberPermissions = make_dataclass(
    "MemberPermissions", [
        ((name, Permissions, Permissions.NONE) if name != 'data'
            else (name, MemberDataPermissions, NO_MEMBER_DATA_PERMISSIONS)
        ) for name in Member.get_field_names()],
    frozen=True
)
MemberPermissionsType = Type[MemberPermissions]

# NO_MEMBER_PERMISSIONS is a MemberPermissions instance with all permissions
# set to NONE.
# It can be used for testing if a MemberPermissions instance has no
# permissions directly by instance comparison.
NO_MEMBER_PERMISSIONS : Final = MemberPermissions()

def define_member_permissions(
    data=NO_MEMBER_DATA_PERMISSIONS,
    oid=Permissions.NONE,
    member_state=Permissions.NONE,
    type=Permissions.NONE,
    email=Permissions.NONE,
    votes=Permissions.NONE,
    seed=Permissions.NONE,
    email_send_status_history=Permissions.NONE,
    challenge=Permissions.NONE,
    pseudonym=Permissions.NONE,
    modifications=Permissions.NONE
    ) -> MemberPermissionsType:
    """Define the permissions for a member.
    """
    if data == NO_MEMBER_DATA_PERMISSIONS and all(
        value == Permissions.NONE for value in [
            oid, member_state, type, email, votes, seed,
            email_send_status_history, challenge, pseudonym, modifications]):
        # If all permissions are NONE return NO_MEMBER_PERMISSIONS
        # for allowing instance comparison (faster than comparing all values)
        return NO_MEMBER_PERMISSIONS
    return MemberPermissions(
        data=data,
        oid=oid,
        member_state=member_state,
        type=type,
        email=email,
        votes=votes,
        seed=seed,
        email_send_status_history=email_send_status_history,
        challenge=challenge,
        pseudonym=pseudonym,
        modifications=modifications
    )

# The permissions for reading only oid, pseudonym, type, role and state.
# Access to basic member data.
BASIC_PERMISSIONS : Final = define_member_permissions(
    data=define_member_data_permissions(
        role=Permissions.ACCESS | Permissions.READ
    ),
    oid=Permissions.ACCESS | Permissions.READ,
    member_state=Permissions.ACCESS | Permissions.READ,
    type=Permissions.ACCESS | Permissions.READ,
    pseudonym=Permissions.ACCESS | Permissions.READ,
)

# Permissions for admin members to access member properties.
ADMIN_PERMISSIONS : Final = define_member_permissions(
    data=MemberDataPermissions(
        fullname=Permissions.ACCESS | Permissions.READ,
        fullsurname=Permissions.ACCESS | Permissions.READ,
        description=Permissions.ACCESS | Permissions.READ,
        nationality=Permissions.ACCESS | Permissions.READ,
        birthdate=Permissions.ACCESS | Permissions.READ,
        password=Permissions.ACCESS | Permissions.WRITE,
        password_confirm=Permissions.ACCESS | Permissions.WRITE,
        lang1=Permissions.ACCESS | Permissions.READ,
        lang2=Permissions.ACCESS | Permissions.READ,
        lang3=Permissions.ACCESS | Permissions.READ,
        cooperative_behaviour_mark=Permissions.ACCESS | Permissions.READ,
        cooperative_behaviour_mark_updated=Permissions.ACCESS | Permissions.READ,
        number_shares_owned=Permissions.ACCESS | Permissions.READ,
        date_end_validity_yearly_contribution=Permissions.ACCESS | Permissions.READ,
        iban=Permissions.NONE,
        role=Permissions.ACCESS | Permissions.READ,
    ),
    oid=Permissions.ACCESS | Permissions.READ,
    member_state=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
    type=Permissions.ACCESS | Permissions.READ,
    email=Permissions.ACCESS | Permissions.READ,
    votes=Permissions.ACCESS | Permissions.READ,
    seed=Permissions.ACCESS,
    email_send_status_history=Permissions.ACCESS | Permissions.READ,
    challenge=Permissions.ACCESS | Permissions.READ,
    pseudonym=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
    modifications=Permissions.ACCESS | Permissions.READ
)

# Create a mapping to store the permissions for each member state.
# The mapping is structured as follows:
# - The key is the member state.
# - The value is a MemberPermissions dataclass that stores
#   the permissions for each attribute of the Member dataclass.
access = {
    'Owner' : {
        MemberStates.CREATED:{
            define_member_permissions(
                data=NO_MEMBER_DATA_PERMISSIONS,
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.NONE,
                email=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                votes=Permissions.NONE,
                seed=Permissions.ACCESS,
                email_send_status_history=Permissions.ACCESS | Permissions.READ,
                challenge=Permissions.NONE,
                pseudonym=Permissions.NONE,
                modifications=Permissions.ACCESS | Permissions.READ
            )
        },
        MemberStates.DRAFT:{
            MemberPermissions(
                    data=MemberDataPermissions(
                    fullname=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    fullsurname=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    description=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    nationality=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    birthdate=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    password=Permissions.ACCESS | Permissions.WRITE,
                    password_confirm=Permissions.ACCESS | Permissions.WRITE,
                    lang1=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    lang2=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    lang3=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.ACCESS | Permissions.READ,
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                email=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                votes=Permissions.NONE,
                seed=Permissions.ACCESS,
                email_send_status_history=Permissions.ACCESS | Permissions.READ,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                modifications=Permissions.ACCESS | Permissions.READ
            )
        },
        MemberStates.REGISTRED:{
            MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.ACCESS | Permissions.READ,
                    fullsurname=Permissions.ACCESS | Permissions.READ,
                    description=Permissions.ACCESS | Permissions.READ,
                    nationality=Permissions.ACCESS | Permissions.READ,
                    birthdate=Permissions.ACCESS | Permissions.READ,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.ACCESS | Permissions.READ,
                    lang2=Permissions.ACCESS | Permissions.READ,
                    lang3=Permissions.ACCESS | Permissions.READ,
                    cooperative_behaviour_mark=Permissions.READ,
                    cooperative_behaviour_mark_updated=Permissions.READ,
                    number_shares_owned=Permissions.READ,
                    date_end_validity_yearly_contribution=Permissions.READ,
                    iban=Permissions.READ,
                    role=Permissions.READ,
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.ACCESS | Permissions.READ,
                email=Permissions.ACCESS | Permissions.READ,
                votes=Permissions.NONE,
                seed=Permissions.ACCESS,
                email_send_status_history=Permissions.ACCESS | Permissions.READ,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.ACCESS | Permissions.READ
            )
        },
        MemberStates.DATA_MODIFICATION_REQUESTED:{
            MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.ACCESS | Permissions.READ,
                    fullsurname=Permissions.ACCESS | Permissions.READ,
                    description=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    nationality=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    birthdate=Permissions.ACCESS | Permissions.READ,
                    password=Permissions.NONE | Permissions.WRITE,
                    password_confirm=Permissions.NONE | Permissions.WRITE,
                    lang1=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    lang2=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    lang3=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    cooperative_behaviour_mark=Permissions.ACCESS | Permissions.READ,
                    cooperative_behaviour_mark_updated=Permissions.ACCESS | Permissions.READ,
                    number_shares_owned=Permissions.ACCESS | Permissions.READ,
                    date_end_validity_yearly_contribution=Permissions.ACCESS | Permissions.READ,
                    iban=Permissions.READ | Permissions.WRITE,
                    role=Permissions.ACCESS | Permissions.READ,
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.ACCESS | Permissions.READ,
                email=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                votes=Permissions.NONE,
                seed=Permissions.ACCESS,
                email_send_status_history=Permissions.ACCESS | Permissions.READ,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.ACCESS | Permissions.READ
            )
        },
        MemberStates.DATA_MODIFIED:{
            MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.ACCESS | Permissions.READ,
                    fullsurname=Permissions.ACCESS | Permissions.READ,
                    description=Permissions.ACCESS | Permissions.READ,
                    nationality=Permissions.ACCESS | Permissions.READ,
                    birthdate=Permissions.ACCESS | Permissions.READ,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.ACCESS | Permissions.READ,
                    lang2=Permissions.ACCESS | Permissions.READ,
                    lang3=Permissions.ACCESS | Permissions.READ,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE,
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.ACCESS | Permissions.READ,
                email=Permissions.ACCESS | Permissions.READ,
                votes=Permissions.NONE,
                seed=Permissions.ACCESS,
                email_send_status_history=Permissions.ACCESS | Permissions.READ,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.ACCESS | Permissions.READ
            )
        },
        MemberStates.EXCLUDED:{
            MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.ACCESS | Permissions.READ,
                    fullsurname=Permissions.ACCESS | Permissions.READ,
                    description=Permissions.ACCESS | Permissions.READ,
                    nationality=Permissions.ACCESS | Permissions.READ,
                    birthdate=Permissions.ACCESS | Permissions.READ,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.ACCESS | Permissions.READ,
                    lang2=Permissions.ACCESS | Permissions.READ,
                    lang3=Permissions.ACCESS | Permissions.READ,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE,
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.ACCESS | Permissions.READ,
                email=Permissions.ACCESS | Permissions.READ,
                votes=Permissions.NONE,
                seed=Permissions.ACCESS,
                email_send_status_history=Permissions.ACCESS | Permissions.READ,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.ACCESS | Permissions.READ
            )
        },
        MemberStates.DELETED:{
            MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.ACCESS | Permissions.READ,
                    fullsurname=Permissions.ACCESS | Permissions.READ,
                    description=Permissions.ACCESS | Permissions.READ,
                    nationality=Permissions.ACCESS | Permissions.READ,
                    birthdate=Permissions.ACCESS | Permissions.READ,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.ACCESS | Permissions.READ,
                    lang2=Permissions.ACCESS | Permissions.READ,
                    lang3=Permissions.ACCESS | Permissions.READ,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE,
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.ACCESS | Permissions.READ,
                email=Permissions.ACCESS | Permissions.READ,
                votes=Permissions.NONE,
                seed=Permissions.ACCESS,
                email_send_status_history=Permissions.ACCESS | Permissions.READ,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.ACCESS | Permissions.READ
            )
        }        
    },
    'Admin' : {
        MemberStates.CREATED:{BASIC_PERMISSIONS},
        MemberStates.DRAFT:{
            MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    fullsurname=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    description=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    nationality=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    birthdate=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    password=Permissions.ACCESS | Permissions.WRITE,
                    password_confirm=Permissions.ACCESS | Permissions.WRITE,
                    lang1=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    lang2=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    lang3=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.ACCESS | Permissions.READ,
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                type=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                email=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                votes=Permissions.NONE,
                seed=Permissions.ACCESS,
                email_send_status_history=Permissions.ACCESS | Permissions.READ,
                challenge=Permissions.ACCESS | Permissions.READ,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.ACCESS | Permissions.READ
            )
        },
        MemberStates.REGISTRED:{
            ADMIN_PERMISSIONS
        },
        MemberStates.DATA_MODIFICATION_REQUESTED:{
            ADMIN_PERMISSIONS
        },
        MemberStates.DATA_MODIFIED:{
            ADMIN_PERMISSIONS
        },
        MemberStates.EXCLUDED:{
            ADMIN_PERMISSIONS
        },
        MemberStates.DELETED:{
            ADMIN_PERMISSIONS
        }
    },
    'Ordinary' : {
        MemberStates.CREATED:{NO_MEMBER_DATA_PERMISSIONS},
        MemberStates.DRAFT:{NO_MEMBER_DATA_PERMISSIONS},
        MemberStates.REGISTRED:{BASIC_PERMISSIONS},
        MemberStates.DATA_MODIFICATION_REQUESTED:{BASIC_PERMISSIONS},
        MemberStates.DATA_MODIFIED:{BASIC_PERMISSIONS},
        MemberStates.EXCLUDED:{NO_MEMBER_DATA_PERMISSIONS},
        MemberStates.DELETED:{NO_MEMBER_DATA_PERMISSIONS}
    },
    'Cooperator' : {
        MemberStates.CREATED:{NO_MEMBER_DATA_PERMISSIONS},
        MemberStates.DRAFT:{NO_MEMBER_DATA_PERMISSIONS},
        MemberStates.REGISTRED:{BASIC_PERMISSIONS},
        MemberStates.DATA_MODIFICATION_REQUESTED:{BASIC_PERMISSIONS},
        MemberStates.DATA_MODIFIED:{BASIC_PERMISSIONS},
        MemberStates.EXCLUDED:{NO_MEMBER_DATA_PERMISSIONS},
        MemberStates.DELETED:{NO_MEMBER_DATA_PERMISSIONS}
    },
    'voter' : {
        MemberStates.CREATED:{NO_MEMBER_DATA_PERMISSIONS},
        MemberStates.DRAFT:{
            MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.ACCESS | Permissions.READ,
                    fullsurname=Permissions.ACCESS | Permissions.READ,
                    description=Permissions.ACCESS | Permissions.READ,
                    nationality=Permissions.ACCESS | Permissions.READ,
                    birthdate=Permissions.ACCESS | Permissions.READ,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.ACCESS | Permissions.READ,
                    lang2=Permissions.ACCESS | Permissions.READ,
                    lang3=Permissions.ACCESS | Permissions.READ,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.ACCESS | Permissions.READ,
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.ACCESS | Permissions.READ,
                email=Permissions.ACCESS | Permissions.READ,
                votes=Permissions.ACCESS | Permissions.WRITE,
                seed=Permissions.ACCESS,
                email_send_status_history=Permissions.NONE,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.NONE
            )
        },
        MemberStates.REGISTRED:{BASIC_PERMISSIONS},
        MemberStates.DATA_MODIFICATION_REQUESTED:{BASIC_PERMISSIONS},
        MemberStates.DATA_MODIFIED:{BASIC_PERMISSIONS},
        MemberStates.EXCLUDED:{NO_MEMBER_DATA_PERMISSIONS},
        MemberStates.DELETED:{NO_MEMBER_DATA_PERMISSIONS}
    },
    'Board' : {
        MemberStates.CREATED:{
             MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.NONE,
                    fullsurname=Permissions.NONE,
                    description=Permissions.NONE,
                    nationality=Permissions.NONE,
                    birthdate=Permissions.NONE,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.NONE,
                    lang2=Permissions.NONE,
                    lang3=Permissions.NONE,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.NONE,
                email=Permissions.NONE,
                votes=Permissions.NONE,
                seed=Permissions.NONE,
                email_send_status_history=Permissions.NONE,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.NONE
            )    
        }
    },
    'MediationArbitrationCouncil' : {
        MemberStates.CREATED:{
             MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.NONE,
                    fullsurname=Permissions.NONE,
                    description=Permissions.NONE,
                    nationality=Permissions.NONE,
                    birthdate=Permissions.NONE,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.NONE,
                    lang2=Permissions.NONE,
                    lang3=Permissions.NONE,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.NONE,
                email=Permissions.NONE,
                votes=Permissions.NONE,
                seed=Permissions.NONE,
                email_send_status_history=Permissions.NONE,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.NONE
            )    
        }
    },
    'CandidatesMissingShareYearContrib' : {
        MemberStates.CREATED:{
             MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.NONE,
                    fullsurname=Permissions.NONE,
                    description=Permissions.NONE,
                    nationality=Permissions.NONE,
                    birthdate=Permissions.NONE,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.NONE,
                    lang2=Permissions.NONE,
                    lang3=Permissions.NONE,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.NONE,
                email=Permissions.NONE,
                votes=Permissions.NONE,
                seed=Permissions.NONE,
                email_send_status_history=Permissions.NONE,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.NONE
            )    
        }
    },
    'CandidatesMissingShare' : {
        MemberStates.CREATED:{
             MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.NONE,
                    fullsurname=Permissions.NONE,
                    description=Permissions.NONE,
                    nationality=Permissions.NONE,
                    birthdate=Permissions.NONE,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.NONE,
                    lang2=Permissions.NONE,
                    lang3=Permissions.NONE,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.NONE,
                email=Permissions.NONE,
                votes=Permissions.NONE,
                seed=Permissions.NONE,
                email_send_status_history=Permissions.NONE,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.NONE
            )    
        }
    },
    'CandidatesMissingYearContrib' : {
        MemberStates.CREATED:{
             MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.NONE,
                    fullsurname=Permissions.NONE,
                    description=Permissions.NONE,
                    nationality=Permissions.NONE,
                    birthdate=Permissions.NONE,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.NONE,
                    lang2=Permissions.NONE,
                    lang3=Permissions.NONE,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.NONE,
                email=Permissions.NONE,
                votes=Permissions.NONE,
                seed=Permissions.NONE,
                email_send_status_history=Permissions.NONE,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.NONE
            )    
        }
    },
    'Sanctioned' : {
        MemberStates.CREATED:{
             MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.NONE,
                    fullsurname=Permissions.NONE,
                    description=Permissions.NONE,
                    nationality=Permissions.NONE,
                    birthdate=Permissions.NONE,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.NONE,
                    lang2=Permissions.NONE,
                    lang3=Permissions.NONE,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.NONE,
                email=Permissions.NONE,
                votes=Permissions.NONE,
                seed=Permissions.NONE,
                email_send_status_history=Permissions.NONE,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.NONE
            )    
        }
    },
    'SanctionedMissingYearContrib' : {
        MemberStates.CREATED:{
             MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.NONE,
                    fullsurname=Permissions.NONE,
                    description=Permissions.NONE,
                    nationality=Permissions.NONE,
                    birthdate=Permissions.NONE,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.NONE,
                    lang2=Permissions.NONE,
                    lang3=Permissions.NONE,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.NONE,
                email=Permissions.NONE,
                votes=Permissions.NONE,
                seed=Permissions.NONE,
                email_send_status_history=Permissions.NONE,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.NONE
            )    
        }
    }
}


def get_member_data_access_permissions(acceded: Member, accessor : Member) -> MemberPermissionsType:
    """Get the data access permissions for a member accessing another member's data.
    Args:
        acceded (Member): The member whose data is being accessed.
        accessor (Member): The member accessing the data.
    Returns:
        MemberPermissions: The data access permissions for the accessor.
    """
    permissions = []
    is_owner = acceded == accessor
    # Check if the accessor is the same as the acceded member
    if is_owner:
        return access['Owner'][acceded.member_state]        
    else:
        return access[accessor.type.name][acceded.member_state]

"""_summary_
Explanation of permissions by roles and states of Members and Applications

## Anonymous

The anonymous user can only see what is made public.
They can view the registration procedure.

## States in alirpunkto

### Here are the states of Members in alirpunkto, these states are used to manage the modification of member data.

- CREATED
- DRAFT
- REGISTRED
- DATA_MODIFICATION_REQUESTED
- DATA_MODIFIED
- EXCLUDED
- DELETED

### Here are the states of Applications (states that are added to the previous ones)

- DRAFT
- EMAIL_VALIDATION
- CONFIRMED_HUMAN
- UNIQUE_DATA
- PENDING
- APPROVED
- REFUSED

### Here are the groups a Member can belong to

- ordinaryMembersGroup
- cooperatorsGroup
- boardMembersGroup
- mediationArbitrationCouncilGroup
- candidatesMissingShareYearContribGroup
- candidatesMissingShareGroup
- candidatesMissingYearContribGroup
- sanctionedGroup
- sanctionedMissingYearContribGroup

## List of variables

- First names (as they appear in official identity documents)
- Last names (as they appear in official identity documents)
- Date of birth
- Nationality (from the Member States of the European Union)
- Display name
- Password
- Confirm password
- Cooperator number
- Cooperative Behavior Note
- Date and time of last update of the Cooperative Behavior Note
- Email address
- Rank 1 interaction language
- Rank 2 interaction language (@TODO Add the option "not specified" in the form)
- Rank 3 interaction language (@TODO Add the option "not specified" in the form)
- User profile text
- User profile picture / avatar
- Role in the Cooperative: * None, * Ordinary Member of the Community, * Cooperator, * Member of the Board, * Member of the Mediation and Arbitration Council
- uniqueMemberOf
- Number of shares held
- End date of current annual contribution validity
- Date when data of resigning or excluded user must be erased

- Bank account IBAN number

## Draft Ordinary Candidate

The state of the Application in AlirPunkto is EMAIL_VALIDATION.
The Member part of the Application is in the DRAFT state.
The Member type in AlirPunkto is ORDINARY.
The Ordinary Candidate must validate their email address.
They can only enter their email and cannot see any other fields.

### List of visible or editable variables

- First names: invisible - not editable
- Last names: invisible - not editable
- Date of birth: invisible - not editable
- Nationality: invisible - not editable
- Username: invisible - not editable
- Password: invisible - not editable
- Confirm password: invisible - not editable
- Cooperator number: invisible - not editable
- Cooperative Behavior Note: invisible - not editable
- Date and time of last update of the Cooperative Behavior Note: invisible - not editable
- Email address: VISIBLE - EDITABLE - REQUIRED
- Rank 1 interaction language: invisible - not editable
- Rank 2 interaction language: invisible - not editable
- Rank 3 interaction language: invisible - not editable
- User profile text: invisible - not editable
- User profile picture / avatar: invisible - not editable
- Role in the Cooperative: invisible - not editable
- uniqueMemberOf: invisible - not editable
- Number of shares held: invisible - not editable
- End date of current annual contribution validity: invisible - not editable
- Date when data of resigning or excluded user must be erased: invisible - not editable
- Bank account IBAN number: invisible - not editable
Once the email is entered, alirpunkto sends the Challenge email.
The list of possible states is as follows:

## Human Ordinary Candidate

The state of the Application in AlirPunkto is CONFIRMED_HUMAN.
The Member part of the Application is in the DRAFT state.
The Human Ordinary Candidate is an Ordinary Candidate who has validated their address and human
character by answering the mathematical challenge, but has not yet entered their data.

### List of visible or editable variables

- First names: invisible - not editable
- Last names: invisible - not editable
- Date of birth: invisible - not editable
- Nationality: invisible - not editable
- Username: VISIBLE - EDITABLE - REQUIRED (Leading and trailing spaces are removed)
- Password: VISIBLE - EDITABLE - REQUIRED
- Confirm password: VISIBLE - EDITABLE - REQUIRED
- Cooperator number: VISIBLE - not editable
- Cooperative Behavior Note: invisible - not editable
- Date and time of last update of the Cooperative Behavior Note: invisible - not editable
- Email address: VISIBLE - not editable
- Rank 1 interaction language: VISIBLE - EDITABLE - REQUIRED
- Rank 2 interaction language: VISIBLE - EDITABLE - optional
- Rank 3 interaction language: VISIBLE - EDITABLE - optional
- User profile text: invisible - not editable
- User profile picture / avatar: invisible - not editable
- Role in the Cooperative: invisible - not editable
- uniqueMemberOf: invisible - not editable
- Number of shares held: invisible - not editable
- End date of current annual contribution validity: invisible - not editable
- Date when data of resigning or excluded user must be erased: invisible - not editable
- Bank account IBAN number: invisible - not editable

## Ordinary Member

The state of the Application in AlirPunkto is APPROVED.
The member is part of the "ordinaryMembersGroup".
The Application part is cleared of its data once written to LDAP.
The Member part of the Application is in the REGISTRED state.
The Ordinary Member is a "Human Ordinary Candidate" who has registered their personal data.
They become an ordinary member of the community.
They can submit a request to become a cooperator, at most once every 30 days (configurable duration).
They can resign and they can be excluded.

Upon each login, alirpunkto offers them to modify or complete their data according to the following list.

### List of visible or editable variables

- First names: invisible - not editable
- Last names: invisible - not editable
- Date of birth: invisible - not editable
- Nationality: invisible - not editable
- Username: VISIBLE - not editable
- Password: invisible - not editable (modifiable only through the "forgot password" procedure)
- Confirm password: invisible - not editable (modifiable only through the "forgot password" procedure)
- Cooperator number: VISIBLE - not editable
- Cooperative Behavior Note: invisible - not editable
- Date and time of last update of the Cooperative Behavior Note: invisible - not editable
- Email address: VISIBLE - EDITABLE - optional
- Rank 1 interaction language: VISIBLE - EDITABLE - optional
- Rank 2 interaction language: VISIBLE - EDITABLE - optional
- Rank 3 interaction language: VISIBLE - EDITABLE - optional
- User profile text: VISIBLE - EDITABLE - optional
- User profile picture / avatar: VISIBLE - EDITABLE - optional
- Role in the Cooperative: VISIBLE - not editable
- uniqueMemberOf: VISIBLE - not editable
- Number of shares held: invisible - not editable
- End date of current annual contribution validity: invisible - not editable
- Date when data of resigning or excluded user must be erased: invisible - not editable
- Bank account IBAN number: invisible - not editable

## Deletion of Ordinary Member

Whether they have resigned or have been excluded by the administrator (without any particular guarantee,
as the Ordinary Member of the Community does not benefit from the protection provided by the Cooperative's bylaws to the Cooperators), alirpunkto deletes the account data of the Ordinary Member, but keeps the pseudonym, deletion date, and reason for deletion (resignation or exclusion). If they have resigned, their Member status is DELETED, if they have been excluded, their Member status is EXCLUDED.

## Draft Cooperative Candidate

The state of the Member part of the Application in AlirPunkto is DRAFT.
The state of the Application part in AlirPunkto is DRAFT.
Alirpunkto requests the email.

### List of visible or editable variables

(same as the Draft Ordinary Candidate)
The candidate submits their email.
Alirpunkto sends the challenge email.
The state of the Application in AlirPunkto is EMAIL_VALIDATION.

## Human Cooperative Candidate

The state of the Member part of the Application in AlirPunkto is DRAFT.
The user has answered the mathematical challenge and thus proved that they are human. The state of the Application part in AlirPunkto is CONFIRMED_HUMAN.

### List of visible or editable variables

- First names: VISIBLE - EDITABLE - REQUIRED
- Last names: VISIBLE - EDITABLE - REQUIRED
- Date of birth: VISIBLE - EDITABLE - REQUIRED
- Nationality: VISIBLE - EDITABLE - REQUIRED
- Username: VISIBLE - EDITABLE - REQUIRED (Leading and trailing spaces are removed)
- Password: VISIBLE - EDITABLE - REQUIRED
- Confirm password: VISIBLE - EDITABLE - REQUIRED
- Cooperator number: VISIBLE - not editable
- Cooperative Behavior Note: invisible - not editable
- Date and time of last update of the Cooperative Behavior Note: invisible - not editable
- Email address: VISIBLE - not editable
- Rank 1 interaction language: VISIBLE - EDITABLE - REQUIRED
- Rank 2 interaction language: VISIBLE - EDITABLE - optional
- Rank 3 interaction language: VISIBLE - EDITABLE - optional
- User profile text: invisible - not editable
- User profile picture / avatar: invisible - not editable
- Role in the Cooperative: invisible - not editable
- uniqueMemberOf: invisible - not editable
- Number of shares held: invisible - not editable
- End date of current annual contribution validity: invisible - not editable
- Date when data of resigning or excluded user must be erased: invisible - not editable
- Bank account IBAN number: invisible - not editable

## Human Cooperative Candidate awaiting verification

The state of the Member part of the Application in AlirPunkto is DRAFT.
The uniqueness of identity data (last name(s), first name(s), date of birth) has been verified in the list of existing Cooperators (cooperatorsGroup, candidatesMissingShareGroup, candidatesMissingYearContribGroup, candidatesMissingShareYearContribGroup, sanctionedGroup, sanctionedMissingYearContribGroup) and in former Cooperators (resigned or excluded) whose identity data is still in the database because they have not been reimbursed and the Quarantine period has not yet passed, so the Application part in AlirPunkto is in the UNIQUE_DATA state.
If the candidate does not declare having sent the verification email, alirpunkto does nothing until a verifier logs in with the voting URL. Alirpunkto can remind the candidate.
If the candidate indicates having sent the verification email, then alirpunkto notifies the verifiers in turn.
The state of the Application is then PENDING.

### List of visible or modifiable variables

- First names: VISIBLE - not modifiable
- Last names: VISIBLE - not modifiable
- Date of birth: VISIBLE - not modifiable
- Nationality: VISIBLE - not modifiable
- Username: VISIBLE - not modifiable
- Password: invisible - not modifiable (modifiable only through the "forgot password" procedure)
- Confirm password: invisible - not modifiable (modifiable only through the "forgot password" procedure)
- Cooperator number: VISIBLE - not modifiable
- Cooperative Behavior Note: invisible - not modifiable
- Date and time of last update of the Cooperative Behavior Note: invisible - not modifiable
- Email address: VISIBLE - MODIFIABLE - optional
- Rank 1 interaction language: VISIBLE - MODIFIABLE - optional
- Rank 2 interaction language: VISIBLE - MODIFIABLE - optional
- Rank 3 interaction language: VISIBLE - MODIFIABLE - optional
- User profile text: VISIBLE - MODIFIABLE - optional
- User profile picture / avatar: VISIBLE - MODIFIABLE - optional
- Role in the Cooperative: invisible - not modifiable
- uniqueMemberOf: invisible - not modifiable
- Number of shares held: invisible - not modifiable
- End date of current annual contribution validity: invisible - not modifiable
- Date when data of resigning or excluded user must be erased: invisible - not modifiable
- Bank account IBAN number: invisible - not modifiable

## Rejected human cooperative candidate

If the Verifiers have not validated the candidate's identity data, the member becomes an Ordinary Member of the Community with full rights (see above).
They are informed that the validation procedure for their identity data has failed, and that they are therefore only an Ordinary Member of the Community.
Their identity data (first name(s), last name(s), date of birth) is deleted.

## Candidate without share and without up-to-date annual contribution

The candidate's identity data has been validated by the Verifiers, and therefore the status of the Application in AlirPunkto is APPROVED.

## The member belongs to 2 groups: ordinaryMembersGroup, candidatesMissingShareYearContribGroup.
#### List of visible or modifiable variables

- First names: VISIBLE
- Last names: VISIBLE - not modifiable
- Date of birth: VISIBLE - not modifiable
- Nationality: VISIBLE - not modifiable

- Pseudonym: VISIBLE - not modifiable
- Password: invisible - not modifiable (modifiable only through the "forgot password" procedure)
- Confirm password: invisible - not modifiable (modifiable only through the "forgot password" procedure)
- Cooperator number: VISIBLE - not modifiable
- Cooperative Behavior Note: invisible - not modifiable
- Last update date and time of Cooperative Behavior Note: invisible - not modifiable
- Email address: VISIBLE - MODIFIABLE - optional
- Interaction language rank 1: VISIBLE - MODIFIABLE - optional
- Interaction language rank 2: VISIBLE - MODIFIABLE - optional
- Interaction language rank 3: VISIBLE - MODIFIABLE - optional
- User profile text: VISIBLE - MODIFIABLE - optional
- User profile image/avatar: VISIBLE - MODIFIABLE - optional
- Role in the Cooperative: VISIBLE - not modifiable
- uniqueMemberOf: VISIBLE - not modifiable
- Number of owned shares: VISIBLE - not modifiable (modification only through online sale on Drupal)
- End date of current annual contribution validity: VISIBLE - not modifiable (modification only through online sale on Drupal)
- Date when data of resigning or excluded user should be erased: invisible - not modifiable
- IBAN bank account number: VISIBLE - MODIFIABLE - optional

### Resignation of a member

In this case, alirpunkto does not ask for their IBAN, and keeps their personal data during the quarantine period, then retains their pseudonym, the account deletion date, and the reason for their departure (i.e., resignation).

The administrator can exclude them in the same way as excluding an ordinary member of the Community, as the person, not having any shares, is not legally a Cooperator and therefore does not benefit from the protections that the Cooperative's bylaws provide to its members.

## Candidate without shares but with up-to-date annual contribution

The status of the Candidate in AlirPunkto is APPROVED.

The member belongs to the 2 groups: ordinaryMembersGroup, candidatesMissingShareGroup.

### List of visible or modifiable variables

(same as the Candidate without shares and without up-to-date annual contribution)

They can resign and be excluded under the same conditions and for the same reasons as the candidate without shares or up-to-date annual contribution. Their annual contribution is lost.

## Candidate with shares but without up-to-date annual contribution

They belong to the 2 groups: ordinaryMembersGroup, candidatesMissingYearContribGroup.

### List of visible or modifiable variables

- First names: VISIBLE - not modifiable
- Last names: VISIBLE - not modifiable
- Date of birth: VISIBLE - not modifiable
- Nationality: VISIBLE - not modifiable
- Pseudonym: VISIBLE - not modifiable
- Password: invisible - not modifiable (modifiable only through the "forgot password" procedure)
- Confirm password: invisible - not modifiable (modifiable only through the "forgot password" procedure)
- Cooperator number: VISIBLE - not modifiable
- Cooperative Behavior Note: VISIBLE - not modifiable (only through KuneAgi instances)
- Last update date and time of Cooperative Behavior Note: VISIBLE - not modifiable (only through KuneAgi instances)
- Email address: VISIBLE - MODIFIABLE - optional
- Interaction language rank 1: VISIBLE - MODIFIABLE - optional
- Interaction language rank 2: VISIBLE - MODIFIABLE - optional
- Interaction language rank 3: VISIBLE - MODIFIABLE - optional
- User profile text: VISIBLE - MODIFIABLE - optional
- User profile image/avatar: VISIBLE - MODIFIABLE - optional
- Role in the Cooperative: VISIBLE - not modifiable
- uniqueMemberOf: VISIBLE - not modifiable
- Number of owned shares: VISIBLE - not modifiable (modification only through online sale on Drupal)
- End date of current annual contribution validity: VISIBLE - not modifiable (modification only through online sale on Drupal)
- Date when data of resigning or excluded user should be erased: invisible - not modifiable
- IBAN bank account number: VISIBLE - MODIFIABLE - optional

They can resign and be excluded under the conditions and procedures described below.

## Cooperator with shares and up-to-date annual contribution

They are considered a cooperative member, belong to the 2 groups: ordinaryMembersGroup, cooperatorsGroup.

### List of visible or modifiable variables

(same as the Candidate with shares but without up-to-date annual contribution)

They can resign and be excluded under the conditions and procedures described below.

## Sanctioned Cooperator

The Cooperator sanctioned by the Mediation and Arbitration Council following a procedure defined by the bylaws (this procedure is outside the scope of AlirPunkto) is in the groups: ordinaryMembersGroup and sanctionedGroup.

### List of visible or modifiable variables

(same as the Candidate with shares but without up-to-date annual contribution)

They can resign and be excluded under the conditions and procedures described below.

### Sanctioned Cooperator without up-to-date annual contribution

The Cooperator sanctioned by the Mediation and Arbitration Council following a procedure defined by the bylaws (this procedure is outside the scope of AlirPunkto) and whose annual contribution is no longer up-to-date, or the Candidate without up-to-date annual contribution sanctioned by the Mediation and Arbitration Council, is in the groups: ordinaryMembersGroup and sanctionedMissingYearContribGroup.

### List of visible or modifiable variables

(same as the Candidate with shares but without up-to-date annual contribution)

They can resign and be excluded under the conditions and procedures described below.

## Resignation of a member from the groups candidatesMissingYearContribGroup, cooperatorsGroup, sanctionedGroup, sanctionedMissingYearContribGroup

If the member resigns, they no longer belong to any group. Alirpunkto asks them to fill in their IBAN.

So, as long as they have not been reimbursed for their share (= as long as the number of shares they own is different from 0), they retain access to AlirPunkto (to fill in their IBAN details) and their identity data is retained.

Every time they log in, aliripunkto reminds them that their IBAN is needed for reimbursement.

Once they have been reimbursed and the Quarantine period has expired, alirpunkto informs them that their data has been deleted and then deletes all data from the account, retaining only their pseudonym, the date, and the reason for their departure (i.e., resignation).

### List of visible or modifiable variables

- First names: VISIBLE - not modifiable
- Last names: VISIBLE - not modifiable
- Date of birth: VISIBLE - not modifiable
- Nationality: VISIBLE - not modifiable
- Pseudonym: VISIBLE - not modifiable
- Password: invisible - not modifiable (modifiable only through the "forgot password" procedure)
- Confirm password: invisible - not modifiable (modifiable only through the "forgot password" procedure)
- Cooperator number: VISIBLE - not modifiable
- Cooperative Behavior Note: VISIBLE - not modifiable (only through KuneAgi instances)
- Last update date and time of Cooperative Behavior Note: VISIBLE - not modifiable (only through KuneAgi instances)
- Email address: VISIBLE - MODIFIABLE - optional
- Interaction language rank 1: VISIBLE - MODIFIABLE - optional
- Interaction language rank 2: VISIBLE - MODIFIABLE - optional
- Interaction language rank 3: VISIBLE - MODIFIABLE - optional
- User profile text: VISIBLE - not modifiable
- User profile image/avatar: VISIBLE - not modifiable
- Role in the Cooperative: VISIBLE - not modifiable
- uniqueMemberOf: VISIBLE - not modifiable
- Number of owned shares: VISIBLE - not modifiable (modification only through online sale on Drupal)
- End date of current annual contribution validity: VISIBLE - not modifiable (modification only through online sale on Drupal)
- Date when data of resigning or excluded user should be erased: VISIBLE - not modifiable
- IBAN bank account number: VISIBLE - MODIFIABLE - optional

## Exclusion of a member from the groups candidatesMissingYearContribGroup, cooperatorsGroup, sanctionedGroup, sanctionedMissingYearContribGroup

The member can be excluded by the Mediation and Arbitration Council, following the procedure defined in the Cooperative's bylaws (this procedure is outside the scope of AlirPunkto). The procedure to follow in case of exclusion, and the list of visible or modifiable variables, are identical to those in the case of resignation, with the only difference being that the reason for departure is exclusion.
"""