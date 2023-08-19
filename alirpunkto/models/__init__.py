from persistent.mapping import PersistentMapping


class AlirPunktoModel(PersistentMapping):
    __parent__ = __name__ = None


def appmaker(zodb_root):
    if 'app_root' not in zodb_root:
        app_root = AlirPunktoModel()
        zodb_root['app_root'] = app_root
    return zodb_root['app_root']
