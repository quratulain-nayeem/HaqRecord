"""Run locally once; passwords are entered privately and never written as text."""
from getpass import getpass
from auth import connect, provision_account
from contextlib import closing


def main():
    with closing(connect()) as db:
        if db.execute('SELECT 1 FROM account').fetchone():
            print('The caseworker account already exists. No changes made.')
            return
    username = input('Caseworker username [caseworker]: ').strip() or 'caseworker'
    password = getpass('Choose a password (12 to 128 characters): ')
    confirm = getpass('Enter it again: ')
    if password != confirm:
        print('Passwords do not match. Run this command again.')
        return
    try:
        provision_account(username, password)
    except ValueError as error:
        print(error)
        return
    print('Account created. Open http://127.0.0.1:8000/login to sign in.')


if __name__ == '__main__':
    main()
