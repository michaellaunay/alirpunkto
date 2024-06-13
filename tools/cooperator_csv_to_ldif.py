#!/bin/python3
# Description: Convert a CSV file to LDIF format for importing members into an LDAP server.
# Author: Michael Launay
# Date: 2024-06-11

import csv
from datetime import datetime
import argparse
import os, sys, re, random
import string
from uuid import uuid4

from alirpunkto.utils import get_ldap_member_list

default_csv_file_path = '/home/michaellaunay/tmp/FoundingMembers_2022_LDAP-data.csv'
default_ldif_dir = '/home/michaellaunay/tmp/ldif'
# reserved uids that should not be used
reserved_uids = ["00000000-0000-0000-0000-000000000000"]
reserved_uids.extend([member['uid'] for member in get_ldap_member_list()])

# Dictionary to map French months to their numerical equivalents
french_months = {
    "janv.": "01", "févr.": "02", "mars": "03", "avr.": "04", "mai": "05", "juin": "06",
    "juil.": "07", "août": "08", "sept.": "09", "oct.": "10", "nov.": "11", "déc.": "12"
}

def convert_french_date_to_iso(date_francaise):
    """Converts a French date to ISO format (YYYY-MM-DD)"""
    # Example of a French date: 21 févr. 1963
    match = re.search(r'(\d{1,2}) (\w+)\. (\d{4})', date_francaise)
    if match:
        day, month, year = match.groups()
        month = french_months[month.lower()] if month in french_months else french_months[month.lower()+"."]
        date_iso = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        return date_iso
    return date_francaise

def remove_inner_spaces(text):
    return re.sub(r'\s+', '', text)

def convert_date(date_str):
    """
    Convert a date string to LDIF format.

    Args:
        date_str (str): The date string to convert.

    Returns:
        str: The date string in LDIF format.

    Raises:
        ValueError: If the date string cannot be converted.

    """
    try:
        date_obj = datetime.strptime(date_str, '%d %b %Y')
        return date_obj.strftime('%Y%m%d%H%M%SZ')
    except ValueError:
        return date_str

def convert_csv_to_ldif(csv_file_path, print_dest=sys.stdout):
    with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            pseudonym = row['Pseudonyme']
            if not pseudonym:
                continue
            given_name = row['Prénoms']
            family_name = row['Noms']
            function = row['Fonction dans la Coopérative']
            birthdate = convert_date(convert_french_date_to_iso(row['Date de naissance']))
            nationality = row['Nationalité'].split('–')[0].strip()
            email = row['Adresse de courriel']
            lang1 = row['Langue 1']
            lang2 = row['Langue 2']
            lang3 = row['Langue 3']
            num_shares = remove_inner_spaces(row['Nombre de parts'])
            uid = uuid4()
            while uid in reserved_uids:
                uid = uuid4()

            # Generate a random password with 20 characters
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=32))

            ldif_entry = f"""
            dn: uid={uid},dc=ecreall,dc=com
            objectClass: top
            objectClass: inetOrgPerson
            objectClass: alirpunktoPerson
            uid: {uid}
            mail: {email}
            userPassword: {password}
            sn: {family_name}
            cn: {pseudonym}
            description: {function}
            employeeNumber: {uid}
            employeeType: COOPERATOR
            isActive: 'False'
            preferredLanguage: {lang1}
            secondLanguage: {lang2}
            thirdLanguage: {lang3}
            givenName: {given_name}
            nationality: {nationality}
            birthdate: {birthdate}
            cooperativeBehaviourMark: 0
            numberSharesOwned: {num_shares.replace(',', '')}
            dateEndValidityYearlyContribution: {convert_date('2024-04-23')}
            uniqueMemberOf: cn=cooperatorsGroup,dc=cosmopolitical,dc=coop
            """
            print(ldif_entry.strip(), file=print_dest)
            print('\n', file=print_dest)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert a CSV file to LDIF format for importing into an LDAP server.')
    parser.add_argument('-csv_file', type=str, default=default_csv_file_path, help='Path to the CSV file')
    parser.add_argument('-ldif_dir', type=str, default=default_ldif_dir, help='Path to the directory where LDIF files will be saved')

    args = parser.parse_args()

    csv_file_path = args.csv_file
    ldif_dir = args.ldif_dir

    # Check if the CSV file exists, exit with an error if it doesn't
    if not os.path.exists(csv_file_path):
        print(f"Error: CSV file '{csv_file_path}' does not exist.")
        exit(1)

    # Check if the LDIF directory exists, create it if it doesn't
    if not os.path.exists(ldif_dir):
        os.makedirs(ldif_dir)

    # Call the convert_csv_to_ldif function with the provided arguments
    convert_csv_to_ldif(csv_file_path)