import unittest
from alirpunkto.models.member import MemberStates, Permissions, EmailSendStatus, MemberTypes

class TestMemberStates(unittest.TestCase):
    def test_get_i18n_id(self):
        self.assertEqual(MemberStates.get_i18n_id(MemberStates.CREATED.name), "member_state_created_name")
        self.assertEqual(MemberStates.get_i18n_id(MemberStates.DRAFT.name), "member_state_draft_name")
        self.assertEqual(MemberStates.get_i18n_id(MemberStates.REGISTRED.name), "member_state_registred_name")
        self.assertEqual(MemberStates.get_i18n_id(MemberStates.REGISTRED.value), "member_state_registred_value")
        self.assertEqual(MemberStates.get_i18n_id(MemberStates.DATA_MODIFICATION_REQUESTED.name), "member_data_modification_request_name")
        self.assertEqual(MemberStates.get_i18n_id(MemberStates.DATA_MODIFIED.name), "member_datas_modified_name")
        self.assertEqual(MemberStates.get_i18n_id(MemberStates.CREATED.value), "member_state_created_value")
        self.assertEqual(MemberStates.get_i18n_id(MemberStates.DRAFT.name), "member_state_draft_value")
        self.assertEqual(MemberStates.get_i18n_id(MemberStates.DATA_MODIFICATION_REQUESTED.name), "member_data_modification_request_value")
        self.assertEqual(MemberStates.get_i18n_id(MemberStates.DATA_MODIFIED.name), "member_datas_modified_value")
        self.assertEqual(MemberStates.get_i18n_id(MemberStates.EXCLUDED.name), "member_datas_excluded_name")
        self.assertEqual(MemberStates.get_i18n_id(MemberStates.DELETED.name), "member_datas_deleted_name")
        self.assertEqual(MemberStates.get_i18n_id(MemberStates.EXCLUDED.value), "member_datas_excluded_value")
        self.assertEqual(MemberStates.get_i18n_id(MemberStates.DELETED.value), "member_datas_deleted_value")
        self.assertEqual(MemberStates.get_i18n_id("unknown_state"), "name.lower()")

    def test_get_names(self):
        names = MemberStates.get_names()
        self.assertEqual(len(names), 8)
        self.assertIn(MemberStates.CREATED.name, names)
        self.assertIn(MemberStates.DRAFT.name, names)
        self.assertIn(MemberStates.REGISTRED.name, names)
        self.assertIn(MemberStates.DATA_MODIFICATION_REQUESTED.name, names)
        self.assertIn(MemberStates.DATA_MODIFIED.name, names)
        self.assertIn(MemberStates.EXCLUDED.name, names)
        self.assertIn(MemberStates.DELETED.name, names)

class TestMemberPermissions(unittest.TestCase):
    def test_get_i18n_id(self):
        self.assertEqual(Permissions.get_i18n_id(Permissions.NONE.name), "access_permissions_none")
        self.assertEqual(Permissions.get_i18n_id(Permissions.NONE.value), "access_permissions_none_value")
        self.assertEqual(Permissions.get_i18n_id(Permissions.ACCESS.name), "access_permissions_access")
        self.assertEqual(Permissions.get_i18n_id(Permissions.ACCESS.value), "access_permissions_access_value")
        self.assertEqual(Permissions.get_i18n_id(Permissions.READ.name), "access_permissions_read")
        self.assertEqual(Permissions.get_i18n_id(Permissions.READ.value), "access_permissions_read_value")
        self.assertEqual(Permissions.get_i18n_id(Permissions.WRITE.name), "access_permissions_write")
        self.assertEqual(Permissions.get_i18n_id(Permissions.WRITE.value), "access_permissions_write_value")
        self.assertEqual(Permissions.get_i18n_id(Permissions.EXECUTE.name), "access_permissions_execute")
        self.assertEqual(Permissions.get_i18n_id(Permissions.EXECUTE.value), "access_permissions_execute_value")
        self.assertEqual(Permissions.get_i18n_id(Permissions.CREATE.name), "access_permissions_create")
        self.assertEqual(Permissions.get_i18n_id(Permissions.CREATE.value), "access_permissions_create_value")
        self.assertEqual(Permissions.get_i18n_id(Permissions.DELETE.name), "access_permissions_delete")
        self.assertEqual(Permissions.get_i18n_id(Permissions.DELETE.value), "access_permissions_delete_value")
        self.assertEqual(Permissions.get_i18n_id(Permissions.TRAVERSE.name), "access_permissions_traverse")
        self.assertEqual(Permissions.get_i18n_id(Permissions.TRAVERSE.value), "access_permissions_traverse_value")
        self.assertEqual(Permissions.get_i18n_id(Permissions.RENAME.name), "access_permissions_rename")
        self.assertEqual(Permissions.get_i18n_id(Permissions.RENAME.value), "access_permissions_rename_value")
        self.assertEqual(Permissions.get_i18n_id(Permissions.DELETE_CHILD.name), "access_permissions_delete_child")
        self.assertEqual(Permissions.get_i18n_id(Permissions.DELETE_CHILD.value), "access_permissions_delete_child_value")
        self.assertEqual(Permissions.get_i18n_id(Permissions.ADMIN.name), "access_permissions_admin")
        self.assertEqual(Permissions.get_i18n_id(Permissions.ADMIN.value), "access_permissions_admin_value")
        self.assertEqual(Permissions.get_i18n_id("unknown_permission"), "name.lower()")

    def test_get_names(self):
        names = Permissions.get_names()
        self.assertEqual(len(names), 12)
        self.assertIn(Permissions.NONE.name, names)
        self.assertIn(Permissions.ACCESS.name, names)
        self.assertIn(Permissions.READ.name, names)
        self.assertIn(Permissions.WRITE.name, names)
        self.assertIn(Permissions.EXECUTE.name, names)
        self.assertIn(Permissions.CREATE.name, names)
        self.assertIn(Permissions.DELETE.name, names)
        self.assertIn(Permissions.TRAVERSE.name, names)
        self.assertIn(Permissions.RENAME.name, names)
        self.assertIn(Permissions.DELETE_CHILD.name, names)
        self.assertIn(Permissions.ADMIN.name, names)

class TestEmailSendStatus(unittest.TestCase):
    def test_enum_values(self):
        self.assertEqual(EmailSendStatus.IN_PREPARATION.value, "email_send_status_in_preparation_value")
        self.assertEqual(EmailSendStatus.SENT.value, "email_send_status_sent_value")
        self.assertEqual(EmailSendStatus.ERROR.value, "email_send_status_error_value")

class TestMemberTypes(unittest.TestCase):
    def test_get_i18n_id(self):
        self.assertEqual(MemberTypes.get_i18n_id(MemberTypes.ORDINARY.name), "member_types_ordinary")
        self.assertEqual(MemberTypes.get_i18n_id(MemberTypes.COOPERATOR.name), "member_types_cooperator")
        self.assertEqual(MemberTypes.get_i18n_id(MemberTypes.ORDINARY.value), "member_types_ordinary_value")
        self.assertEqual(MemberTypes.get_i18n_id(MemberTypes.COOPERATOR.value), "member_types_cooperator_value")

if __name__ == '__main__':
    unittest.main()