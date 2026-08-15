"""Member avatar as jpegPhoto in the LDAP directory (issue #150).

A picture conveys a lot of the person's personality: members can upload a
JPEG-only avatar from their own profile page, stored as the standard
inetOrgPerson ``jpegPhoto`` attribute — never in ZODB, so the resignation
purge erases it with the LDAP entry. The upload is checked three ways:
the .jpg/.jpeg extension (with the exact error message the ticket
specifies), the JPEG magic bytes (an extension alone proves nothing), and
a size ceiling. Any logged-in member can see any member's avatar; only
the owner can change or remove theirs.
"""
from __future__ import annotations

import json
import zlib

from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.response import Response
from pyramid.view import view_config

from alirpunkto.constants_and_globals import (
    _,
    AVATAR_MAX_BYTES,
)
from alirpunkto.utils import (
    delete_member_avatar,
    get_member_avatar,
    set_member_avatar,
)

def avatar_url(request, oid):
    """Versioned avatar URL (issue #259): the v token is the CRC32 of
    the image bytes, so the URL changes the instant the avatar does —
    browsers refetch immediately after an upload, while the 5-minute
    cache keeps serving unchanged avatars. Any storage hiccup degrades
    to a stable v=0 URL (the pre-#259 behaviour)."""
    try:
        jpeg = get_member_avatar(request, oid)
    except Exception:
        jpeg = None
    version = format(zlib.crc32(jpeg) & 0xffffffff, 'x') if jpeg else '0'
    return request.route_url('member_avatar',
                             _query={'oid': str(oid), 'v': version})


JPEG_MAGIC = b'\xff\xd8\xff'
JPEG_EXTENSIONS = ('.jpg', '.jpeg')


def _session_oid(request):
    user = request.session.get('user')
    if isinstance(user, str):
        try:
            user = json.loads(user)
        except (TypeError, ValueError):
            user = None
    return user.get('oid') if isinstance(user, dict) else None


@view_config(route_name='member_avatar')
def member_avatar(request):
    """Serve the jpegPhoto of a member to logged-in members."""
    if not request.session.get('logged_in'):
        return HTTPFound(location=request.route_url('home'))
    oid = request.params.get('oid') or _session_oid(request)
    if not oid:
        raise HTTPNotFound()
    jpeg = get_member_avatar(request, oid)
    if not jpeg:
        raise HTTPNotFound()
    return Response(body=jpeg, content_type='image/jpeg',
                    cache_expires=300)


@view_config(route_name='avatar_upload')
def avatar_upload(request):
    """Upload (or remove) one's own avatar; JPEG only, per the ticket."""
    if not request.session.get('logged_in'):
        return HTTPFound(location=request.route_url('home'))
    oid = _session_oid(request)
    if not oid:
        return HTTPFound(location=request.route_url('home'))

    if 'remove' in request.POST:
        delete_member_avatar(request, oid)
        request.session.flash(_('avatar_removed_message'), 'success')
        return HTTPFound(location=request.route_url('modify_member', _query={'self': '1'}))

    field = request.POST.get('avatar')
    filename = getattr(field, 'filename', None)
    if not filename:
        request.session.flash(_('avatar_format_error'), 'error')
        return HTTPFound(location=request.route_url('modify_member', _query={'self': '1'}))
    if not filename.lower().endswith(JPEG_EXTENSIONS):
        # The exact requirement of issue #150: JPEG only, .JPG or .JPEG.
        request.session.flash(_('avatar_format_error'), 'error')
        return HTTPFound(location=request.route_url('modify_member', _query={'self': '1'}))

    jpeg = field.file.read(AVATAR_MAX_BYTES + 1)
    if len(jpeg) > AVATAR_MAX_BYTES:
        request.session.flash(_('avatar_too_large_error'), 'error')
        return HTTPFound(location=request.route_url('modify_member', _query={'self': '1'}))
    if not jpeg.startswith(JPEG_MAGIC):
        # The extension alone proves nothing: the content must be JPEG too.
        request.session.flash(_('avatar_format_error'), 'error')
        return HTTPFound(location=request.route_url('modify_member', _query={'self': '1'}))

    result = set_member_avatar(request, oid, jpeg)
    if result.get('status') == 'success':
        request.session.flash(_('avatar_updated_message'), 'success')
    else:
        request.session.flash(result.get('message'), 'error')
    return HTTPFound(location=request.route_url('modify_member', _query={'self': '1'}))
