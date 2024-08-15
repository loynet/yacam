import logging

import socketio
from requests import Session

logger = logging.getLogger(__name__)


def delete(
    post_id: str,
    hide_username: bool = True,
    log_message: str = "",
) -> dict:
    """
    Deletes a post.
    :param post_id: The id of the post to delete
    :param hide_username: (optional) Whether to hide the moderator name
    :param log_message: (optional) The reason for the deletion (publicly visible)
    :return: The status code and the response body
    """
    action = {"checkedposts": post_id, "delete": "1", "log_message": log_message}

    if hide_username:
        action["hide_name"] = "1"
    return action


def delete_and_ban(
    post_id: str,
    hide_username: bool = True,
    log_message: str = "",
    ban_reason: str = "",
    ban_duration: str = "1y",
) -> dict:
    """
    Deletes a post and bans the poster.
    :param post_id: The id of the post to delete
    :param hide_username: (optional) Whether to hide the moderator name
    :param log_message: (optional) The reason for the action (publicly visible)
    :param ban_reason: (optional) The reason for the ban (visible to the banned user)
    :param ban_duration: (optional) The duration of the ban
    :return: The status code and the response body
    """
    action = {
        "checkedposts": post_id,
        "delete": "1",
        "global_ban": "1",
        "ban_h": "1",
        "ban_reason": ban_reason,
        "ban_duration": ban_duration,
        "log_message": log_message,
    }

    if hide_username:
        action["hide_name"] = "1"

    return action


class Moderator:

    def __init__(
        self, session: Session, url: str, username: str, password: str
    ) -> None:
        self.session = session
        self.auth_params = {
            "username": username,
            "password": password,
        }
        self.url = url

    def login(self):
        res = self.session.post(
            url=f"{self.url}/forms/login",
            data=self.auth_params,
            headers={"Referer": f"{self.url}/login.html"},
        )
        res.raise_for_status()
        logger.info("Logged in")

    def logout(self):
        res = self.session.post(
            url=f"{self.url}/forms/logout",
            headers={"Referer": f"{self.url}/account.html"},
        )
        res.raise_for_status()
        logger.info("Logged out")

    def do(self, board: str, action: dict[str, str]) -> (int, dict):
        def post_action():
            return self.session.post(
                url=f"{self.url}/forms/board/{board}/modactions",
                headers={
                    "Referer": f"{self.url}/forms/board/{board}/modactions",
                    "x-using-xhr": "true",
                },
                data=action,
            )

        # We might be able to cache the CSRF token, but Tom didn't
        action["_csrf"] = self.__get_csrf_token()
        res = post_action()

        # Try to recover from an expired session, which is somewhat common
        if res.status_code == 403 and "login.html?goto=" in res.url:
            self.login()
            res = post_action()

        return res.status_code, res.json()

    def __get_csrf_token(self):
        res = self.session.get(
            url=f"{self.url}/csrf.json",
            headers={"Referer": f"{self.url}/csrf.json"},
        )
        res.raise_for_status()
        return res.json()["token"]

    def listen(self, callback: callable):
        sio = socketio.Client(http_session=self.session)

        @sio.event
        def connect():
            sio.emit("room", "globalmanage-recent-hashed")

        @sio.on("newPost")
        def new_post(*data):
            callback(data)

        sio.connect(
            self.url,
            headers={"User-Agent": self.session.headers["User-Agent"]},
            transports=["websocket"],
        )
        logger.info("Listener connected")

        tries = 3
        while True:
            try:
                sio.sleep(10)
                sio.call("ping", timeout=5)
                tries = 3
            except:
                tries -= 1
                if tries == 0:
                    sio.shutdown()
                    raise Exception("Socket client failed to ping the server")
