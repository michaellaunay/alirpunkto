# Description: Permissions model
# A Parmission is an object that represents the permissions of object attributes.
# Creation date: 2024-04-06
# Author: Michaël Launay

from typing import Type, Tuple, List, Any, Optional, Dict, Iterator, Final
from dataclasses import dataclass, fields, make_dataclass
from enum import IntFlag, unique
from alirpunkto.constants_and_globals import log

@unique
class Permissions(IntFlag):
    """Access permissions to attributes for any member.
    This class represents the permissions for member attributes.
    Each permission is represented as a bit flag, allowing for easy combination
    of multiple permissions.

    Attributes:
        NONE: No access permission.
        ACCESS: The field is accessible but the value is not shown like a
            password.
        READ: Read permission.
        WRITE: Write permission.
        EXECUTE: Execute permission.
        CREATE: Create permission.
        DELETE: Delete permission.
        TRAVERSE: Traverse permission.
        RENAME: Rename permission.
        DELETE_CHILD: Delete child permission.
        ADMIN: Admin permission.
    """
    # None: No permission
    NONE =         0b00000000000000000000
    # Access: The field is accessible but the value is not shown like password
    ACCESS =       0B00000000000000000001
    # Read: Read permission
    READ =         0B00000000000000000010
    # Write: Write permission
    WRITE =        0B00000000000000000100
    # Execute: Execute permission
    EXECUTE =      0B00000000000000001000
    # Create: Create permission
    CREATE =       0B00000000000000010000
    # Delete: Delete permission
    DELETE =       0B00000000000000100000
    # Traverse: Traverse permission
    TRAVERSE =     0B00000000000001000000
    # Rename: Rename permission
    RENAME =       0B00000000000010000000
    # Delete_child: Delete child permission
    DELETE_CHILD = 0B00000000000100000000
    # Admin: Admin permission
    ADMIN =        0B00000000001000000000

    @classmethod
    def get_i18n_id(cls, name:Type['Permissions']) -> str:
        """Get the i18n id of the permission.
        Args:
            name: The name of the permission.
            get_value: If True, return the name of the permission, else return the name.
        Returns:
            The i18n id of the permission.
        """
        match name:
            case cls.NONE.name :
                return "access_permissions_none"
            case cls.NONE.value :
                return "access_permissions_none_value"
            case cls.ACCESS.name:
                return "access_permissions_access"
            case cls.ACCESS.value:
                return "access_permissions_access_value"
            case cls.READ.name :
                return "access_permissions_read"
            case cls.READ.value :
                return "access_permissions_read_value"
            case cls.WRITE.name :
                return "access_permissions_write"
            case cls.WRITE.value :
                return "access_permissions_write_value"
            case cls.EXECUTE.name :
                return "access_permissions_execute"
            case cls.EXECUTE.value :
                return "access_permissions_execute_value"
            case cls.CREATE.name :
                return "access_permissions_create"
            case cls.CREATE.value :
                return "access_permissions_create_value"
            case cls.DELETE.name :
                return "access_permissions_delete"
            case cls.DELETE.value :
                return "access_permissions_delete_value"
            case cls.TRAVERSE.name :
                return "access_permissions_traverse"
            case cls.TRAVERSE.value :
                return "access_permissions_traverse_value"
            case cls.RENAME.name :
                return "access_permissions_rename"
            case cls.RENAME.value :
                return "access_permissions_rename_value"
            case cls.DELETE_CHILD.name :
                return "access_permissions_delete_child"
            case cls.DELETE_CHILD.value :
                return "access_permissions_delete_child_value"
            case cls.ADMIN.name :
                return "access_permissions_admin"
            case cls.ADMIN.value :
                return "access_permissions_admin_value"
            case _ :
                # should never happen
                log.error(f"Unknown access permission: {name}")
                return(f"name.lower()")
    @staticmethod
    def get_names() -> List[str]:
        """Get the names of the access permissions.
        Returns:
            The names of the access permissions.
        """
        return Permissions.__members__.keys()
    @staticmethod
    def get_permissions(permission:int) \
        -> Iterator[Type['Permissions']]:
        """Get the permissions from int.
        Returns:
            The access permissions as a list.
        """
        return (perm
            for perm in Permissions.__members__.values()
            if permission & perm.value
        )

