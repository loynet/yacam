import atexit
import logging

from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests.sessions import merge_setting
from requests.structures import CaseInsensitiveDict

logger = logging.getLogger(__name__)


class ModSession(Session):
    def __init__(self, domain: str, username: str, password: str,
                 retries: int = 3, timeout: int = 10, backoff_factor: float = 0.3) -> None:
        super(ModSession, self).__init__()

        self.domain = domain
        self.url = f"https://{self.domain}"
        self.auth_params = {'username': username, 'password': password}
        self.csrf_token = None

        # Overwrites session default behaviour
        self.mount(self.url, HTTPAdapter(max_retries=Retry(total=retries, backoff_factor=backoff_factor)))
        self.default_timeout = timeout
        # TODO make the user agent configurable
        self.headers = merge_setting(
            self.headers,
            {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0'},
            dict_class=CaseInsensitiveDict)

        # Try to authenticate the mod
        self.__login()

        # Logout and close the session on exit
        atexit.register(lambda: (
            self.__logout(),
            self.close()
        ))

    # Overwrites request function
    def request(self, method, url, **kwargs):
        # Add timeout if not specified
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.default_timeout

        # Make the request
        res = super().request(method, url, **kwargs)

        # Catch these erros and try to recover
        if res.status_code == 403 and 'login.html?goto=' in res.url:
            # Make sure we don't get stuck in a loop
            kwargs['TTL'] = 3 if 'TTL' not in kwargs else kwargs['TTL'] - 1
            self.__login()
            res = self.request(method, url, **kwargs)

        else:
            res.raise_for_status()

        return res

    def __login(self) -> None:
        """
        Authenticates the current session as a mod with the given credentials.
        :return: None
        """
        self.post(url=f'{self.url}/forms/login', data=self.auth_params,
                  headers={'Referer': f'{self.url}/login.html'})
        logger.info('Logged in')

    def __logout(self) -> None:
        """
        Logs out the current session.
        :return: None
        """
        self.post(
            url=f'https://{self.domain}/forms/logout',
            headers={'Referer': f'https://{self.domain}/account.html'}
        )
        logger.info('Logged out')

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
        :param board: The board where the post is located
        :param post_id: The id of the post to delete
        :param hide_username: (optional) Whether to hide the moderator name
        :param log_message: (optional) The reason for the deletion (publicly visible)
        :return: The status code and the response body
        """
        body = {
            'checkedposts': post_id,
            'delete': '1',
            'log_message': log_message
        }

        if hide_username:
            body['hide_name'] = '1'

        return self.perform(board, body)

    def delete_ban(self, board: str, post_id: str, hide_username: bool = True, log_message: str = '',
                   ban_reason: str = '', ban_duration: str = '1y') -> (int, dict):
        """
        Deletes a post and bans the poster.
        :param board: The board where the post is located
        :param post_id: The id of the post to delete
        :param hide_username: (optional) Whether to hide the moderator name
        :param log_message: (optional) The reason for the action (publicly visible)
        :param ban_reason: (optional) The reason for the ban (visable to the banned user)
        :param ban_duration: (optional) The duration of the ban
        :return: The status code and the response body
        """
        form = {
            'checkedposts': post_id,
            'delete': '1',
            'global_ban': '1',
            'ban_reason': ban_reason,
            'ban_duration': ban_duration,
            'log_message': log_message
        }

        if hide_username:
            form['hide_name'] = '1'

        return self.perform(board, form)

    def perform(self, board: str, action_form: dict) -> (int, dict):
        """
        Performs a mod action.
        :param board: The board where the action will be performed
        :param action_form: The form data
        :return: The status code and the response body
        """

        # TODO maybe the csrf doesn't need to be updated every time but that's how Tom did it
        # Update csrf token
        self.update_csrf()
        action_form['_csrf'] = self.csrf_token

        res = self.post(
            url=f'{self.url}/forms/board/{board}/modactions',
            headers={'Referer': f'{self.url}/forms/board/{board}/modactions', 'x-using-xhr': 'true'},
            data=action_form
        )

        return res.status_code, res.json()
