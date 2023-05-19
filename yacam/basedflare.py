import subprocess
import time

import requests


# TODO change the flow, the session must make the requests to store the cookies automatically and enforce its headers,
#  timeout etc.
#  this file must only solve the challenge and provide an easy way to request the challenge and post the solution

def __solve_argon2_challenge(salt: str, password: str, difficulty: int, time_cost: int, memory_cost: int) -> int:
    print(f'Solving challenge: {salt} {password} {difficulty} {time_cost} {memory_cost}')
    start = time.time()

    prefix: bytes = b'0' * difficulty
    i = 0
    while True:
        # TODO find a python library to solve this, this makes argon2 a system dependency
        cmd = f'echo -n {password}{i} | argon2 {salt} -id -t {time_cost} -k {memory_cost} -p 1 -l 32 -r'
        hashed = subprocess.check_output(cmd, shell=True).strip()
        if hashed.startswith(prefix):
            print(f'Found solution: {i}, took {int(time.time() - start)} seconds')
            return i

        i += 1


def solve_challenge(challenge: str, options: str) -> (str, int):
    algorithm, params = options.split('#', 1)
    if algorithm == 'argon2':
        return challenge, __solve_argon2_challenge(*challenge.split('#')[0:2], *map(int, params.split('#')))
    else:
        raise Exception(f'Unknown algorithm: {algorithm}')


def get_challenge(domain: str) -> (str, str):
    # TODO return request instead and let the session handle it (see above)
    res = requests.get(
        f'https://{domain}/.basedflare/bot-check',
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0',
            'Accept': 'application/json'
        }
    )

    if res.status_code != 200 and res.status_code != 403:
        raise Exception(f'Failed to get bot-check: {res.status_code}')

    content = res.json()
    if content['ca']:
        raise Exception('Bot-check requires captcha, not implemented yet')

    # ch = challenge: password#salt#timestamp#user_id
    # pow = options: algorithm#difficulty#memory_cost#time_cost
    return content['ch'], content['pow']


def bot_check(domain: str) -> requests.PreparedRequest:
    # TODO remove this (see above)
    challenge, answer = solve_challenge(*get_challenge(domain))
    return requests.Request(
        method='POST',
        url=f'https://{domain}/.basedflare/bot-check',
        data={'pow_response': f'{challenge}#{answer}'},
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
    ).prepare()
