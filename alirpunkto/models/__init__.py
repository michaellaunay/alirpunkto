from persistent.mapping import PersistentMapping


class AlirPunktoModel(PersistentMapping):
    """The root object of the ZODB database.
    """
    __parent__ = __name__ = None


def appmaker(zodb_root):
    """appmaker is used to create the root object of the ZODB database

    Args:
        zodb_root (ZODB.DB): the root of the ZODB database

    Returns:
        AlirPunktoModel: the root object of the ZODB database
    """
    if 'app_root' not in zodb_root:
        app_root = AlirPunktoModel()
        zodb_root['app_root'] = app_root
    return zodb_root['app_root']
