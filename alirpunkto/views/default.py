from pyramid.view import view_config

from alirpunkto.models import AlirPunktoModel


@view_config(context=AlirPunktoModel, renderer='alirpunkto:templates/mytemplate.pt')
def my_view(request):
    return {'project': 'alirpunkto'}
