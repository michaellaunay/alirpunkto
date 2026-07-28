"""Consistency lock on the DKIM signing chain (issue #220).

The e-mails of the test deployment reached Gandi with dkim=none. The whole
signing chain now lives in docker/ — key generation per ${DOMAIN}, KeyTable/
SigningTable, the OpenDKIM milter wired to Postfix, OpenDKIM started before
Postfix, the DNS TXT record printed at boot, and the keys persisted in a named
volume so a container recreate does not silently rotate them away from the
published record. These tests parse the docker files so a future edit cannot
break one link of the chain unnoticed; the remaining step is operational
(publish the TXT record shown at boot, see docker/README.md).
"""
from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    return open(os.path.join(ROOT, *parts), encoding='utf-8').read()


START = _read('docker', 'start_postfix.sh')
COMPOSE = _read('docker', 'docker-compose.yaml')
OPENDKIM = _read('docker', 'etc', 'opendkim.conf')


def test_key_is_generated_for_the_deployment_domain():
    assert re.search(r'if \[ ! -f "/etc/dkimkeys/dkim\.private" \]', START)
    assert 'opendkim-genkey -D /etc/dkimkeys -d "${DOMAIN}" -s dkim' in START


def test_key_and_signing_tables_reference_the_same_selector():
    assert 'dkim._domainkey.${DOMAIN} ${DOMAIN}:dkim:/etc/dkimkeys/dkim.private' in START
    assert '*@${DOMAIN} dkim._domainkey.${DOMAIN}' in START


def test_postfix_milter_and_opendkim_share_the_same_socket():
    sockets = set(re.findall(
        r'(?:smtpd_milters|non_smtpd_milters) = ([^\"\s]+)', START))
    assert sockets == {'unix:/run/opendkim/opendkim.sock'}
    assert re.search(r'^Socket\s+local:/run/opendkim/opendkim\.sock',
                     OPENDKIM, re.M)


def test_opendkim_starts_before_postfix_and_prints_the_dns_record():
    i_dkim = START.index('start_opendkim\n')
    i_txt = START.index('cat /etc/dkimkeys/dkim.txt')
    i_postfix = START.index('start_postfix\n')
    assert i_dkim < i_txt < i_postfix


def test_the_keys_survive_a_container_recreate():
    """A named volume holds /etc/dkimkeys: recreating the container must not
    rotate the key away from the DNS record the operator published."""
    assert 'alirpunkto_postfix_dkim:/etc/dkimkeys' in COMPOSE
    assert re.search(r'^volumes:\n(?:.*\n)*?  alirpunkto_postfix_dkim:',
                     COMPOSE, re.M)


def test_the_postfix_container_receives_the_domain():
    block = COMPOSE.split('  postfix:', 1)[1].split('\n  pyramid:', 1)[0]
    assert re.search(r'DOMAIN:\s*\$\{DOMAIN\}', block)


def test_the_readme_documents_the_txt_record():
    readme = _read('docker', 'README.md')
    assert 'dkim._domainkey' in readme
