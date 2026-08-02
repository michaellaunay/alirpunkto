# docker/ldif_records.sh — the ONE copy of the LDIF transport contract.
#
# Tenth audit pass (2026-08-02, §10/§11): the eighth-pass rework moved
# every user value onto the generator's standard input, but the record
# emitter lived inline in docker/init.sh — and the interface change
# silently broke the two other callers (docker/init_test.sh and the
# smoke workflow), which no test inspected. This file is now sourced
# by EVERY caller of docker/generate_ldif.py: changing the transport
# changes all of them together, and tests/test_ldif_callers.py locks
# the set.
#
# Contract: the generator's command line carries the two file paths
# only; every user value crosses the pipe as NUL-delimited NAME=VALUE
# records. A pipe is hidden from ordinary process inspection — unlike
# argv, world-readable in /proc/<pid>/cmdline for the whole process
# lifetime — though root or an authorised tracer can still read a
# process's memory; no transport changes that. Required values are NOT
# checked here: the generator is the single authority and aborts,
# before writing anything, on any required field that is missing or
# empty (a forgotten password must never become the hash of the empty
# string). Optional records are only emitted when non-empty.
#
# Callers set the canonical shell variables below, source this file,
# then run:  generate_ldif_records | python3 docker/generate_ldif.py \
#                TEMPLATE OUT

generate_ldif_records() {
    emit() { printf '%s=%s\0' "$1" "$2"; }
    emit LDAP_BASE_DN     "${LDAP_BASE_DN:-}"
    emit ADMIN_UUID       "${ADMIN_UUID:-}"
    emit ADMIN_LOGIN      "${ADMIN_LOGIN:-}"
    emit ADMIN_PSEUDONYM  "${ADMIN_PSEUDONYM:-}"
    emit ADMIN_EMAIL      "${ADMIN_EMAIL:-}"
    emit ADMIN_PW         "${ADMIN_PASSWORD:-}"
    emit U1_UUID          "${USER1_UUID:-}"
    emit U1_ROLE          "${USER1_ROLE:-}"
    emit U1_PSEUDONYM     "${USER1_PSEUDONYM:-}"
    emit U1_FIRST         "${USER1_FIRSTNAME:-}"
    emit U1_LAST          "${USER1_LASTNAME:-}"
    emit U1_LANG          "${USER1_LANG:-}"
    emit U1_NAT           "${USER1_NATIONALITY:-}"
    emit U1_EMAIL         "${USER1_EMAIL:-}"
    emit U1_PW            "${USER1_PASSWORD:-}"
    emit U2_UUID          "${USER2_UUID:-}"
    emit U2_ROLE          "${USER2_ROLE:-}"
    emit U2_PSEUDONYM     "${USER2_PSEUDONYM:-}"
    emit U2_FIRST         "${USER2_FIRSTNAME:-}"
    emit U2_LAST          "${USER2_LASTNAME:-}"
    emit U2_LANG          "${USER2_LANG:-}"
    emit U2_NAT           "${USER2_NATIONALITY:-}"
    emit U2_EMAIL         "${USER2_EMAIL:-}"
    emit U2_PW            "${USER2_PASSWORD:-}"
    emit TODAY            "${TODAY:-}"
    [ -n "${USER1_SECOND_LANG:-}" ] && emit U1_SECOND_LANG "${USER1_SECOND_LANG}"
    [ -n "${USER1_THIRD_LANG:-}" ]  && emit U1_THIRD_LANG  "${USER1_THIRD_LANG}"
    [ -n "${USER1_BIRTHDATE:-}" ]   && emit U1_BIRTHDATE   "${USER1_BIRTHDATE}"
    [ -n "${USER1_DESCRIPTION:-}" ] && emit U1_DESCRIPTION "${USER1_DESCRIPTION}"
    [ -n "${USER2_SECOND_LANG:-}" ] && emit U2_SECOND_LANG "${USER2_SECOND_LANG}"
    [ -n "${USER2_THIRD_LANG:-}" ]  && emit U2_THIRD_LANG  "${USER2_THIRD_LANG}"
    [ -n "${USER2_BIRTHDATE:-}" ]   && emit U2_BIRTHDATE   "${USER2_BIRTHDATE}"
    [ -n "${USER2_DESCRIPTION:-}" ] && emit U2_DESCRIPTION "${USER2_DESCRIPTION}"
    true
}
