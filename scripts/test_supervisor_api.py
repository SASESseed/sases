import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

BASE = 'http://127.0.0.1:8001'

def login():
    r = httpx.post(BASE + '/token', data={'username': '222222', 'password': '123456'})
    print('login:', r.status_code)
    return r.json()['access_token']

def propose(token):
    r = httpx.post(BASE + '/supervisor/propose',
        headers={'Authorization': 'Bearer ' + token},
        json={'conversation_id': 40, 'supervisor_id': 'sases_assistant_2', 'goal': 'test proposed run'})
    print('propose:', r.status_code, r.json())
    return r.json().get('run_id')

def confirm(token, run_id):
    r = httpx.post(BASE + '/supervisor/confirm',
        headers={'Authorization': 'Bearer ' + token},
        json={'run_id': run_id})
    print('confirm:', r.status_code, r.json())

def get_proposed(token):
    r = httpx.get(BASE + '/supervisor/proposed?conversation_id=40',
        headers={'Authorization': 'Bearer ' + token})
    print('proposed:', r.status_code, r.json())

def main():
    token = login()
    get_proposed(token)
    rid = propose(token)
    if rid:
        get_proposed(token)
        confirm(token, rid)

if __name__ == '__main__':
    main()