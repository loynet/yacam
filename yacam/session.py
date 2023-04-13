import logging

import requests
from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


class ModSession(Session):
    def __init__(self, domain: str, username: str, password: str, retries: int = 3, timeout: int = 10,
                 backoff_factor: float = 0.3) -> None:
        super(ModSession, self).__init__()

        self.domain = domain
        self.url = f"https://{self.domain}"

        self.auth_params = {'username': username, 'password': password}
        self.csrf_token = None

        # Overwrites session default behaviour
        self.mount(self.url, HTTPAdapter(max_retries=Retry(total=retries, backoff_factor=backoff_factor)))
        self.hooks = {'response': [lambda response, *args, **kwargs: response.raise_for_status()]}
        self.default_timeout = timeout

        # Tries to authenticate the mod.
        self.authenticate_mod()

    # Overwrites request function to add a timeout if not specified
    def request(self, method, url, **kwargs):
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.default_timeout
        return super().request(method, url, **kwargs)

    def authenticate_mod(self) -> None:
        """
        Authenticates the session as a mod with the given credentials.
        :return: None
        :raises: Exception if the authentication request fails
        """
        self.post(url=f'{self.url}/forms/login', data=self.auth_params,
                  headers={'Referer': f'{self.url}/login.html'})

    def update_csrf(self) -> None:
        """
        Updates the csrf token.
        :return: None
        :raises: Exception if the csrf token is not found in the response or the request fails
        """
        res = self.get(url=f'{self.url}/csrf.json',
                       headers={'Referer': f'{self.url}/csrf.json'}).json()
        if 'token' not in res:
            raise Exception('Unable to update csrf token')
        self.csrf_token = res['token']

    def delete_post(self, board: str, post_id: str, hide_username: bool = True, log_message: str = '') -> (int, dict):
        """
        Deletes a post.
        The log message is always prefixed with 'yacam' to make it easier to filter.
        :param board: The board where the post is located
        :param post_id: The id of the post to delete
        :param hide_username: (optional) Whether to hide the moderator name
        :param log_message: (optional) The reason for the deletion
        :return: The status code and the response body
        """
        body = {
            'checkedposts': post_id,
            '_csrf': self.csrf_token,
            'delete': '1',
            'log_message': log_message
        }

        return self.mod_action(board, body, hide_username)

    def delete_ban(self, board: str, post_id: str, hide_username: bool = True, log_message: str = '',
                   ban_reason: str = '', ban_duration: str = '1y') -> (int, dict):
        form = {
            'checkedposts': post_id,
            '_csrf': self.csrf_token,
            'delete': '1',
            'global_ban': '1',
            'ban_reason': ban_reason,
            'ban_duration': ban_duration,
            'log_message': log_message
        }

        return self.mod_action(board, form, hide_username)

    def mod_action(self, board: str, form: dict, hide_username) -> (int, dict):
        """
        Performs a mod action.
        :param board: The board where the action will be performed
        :param form: The form data
        :param hide_username: (optional) Whether to hide the moderator name
        :return: The status code and the response body
        """
        if hide_username:
            form['hide_name'] = '1'

        res = self.post(
            url=f'{self.url}/forms/board/{board}/modactions',
            headers={'Referer': f'{self.url}/forms/board/{board}/modactions', 'x-using-xhr': 'true'},
            data=form
        )

        return res.status_code, res.json()
