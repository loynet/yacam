from datetime import datetime


class Flag:
    """
    Represents a flag, it may be a geographic flag or a custom one. It contains the name of the flag and the
    code of the flag.
    """

    def __init__(self, name: str, code: str, is_custom: bool = False):
        self.name = name
        self.code = code
        self.is_custom = is_custom

    @classmethod
    def from_raw(cls, flag: dict):
        return cls(
            name=flag["name"],
            code=flag["code"],
            is_custom=flag.get("custom", False)
        )


class Author:
    """
    Represents an author of a post, most of the time an anon, but the author
    can have a name, a tripcode, a capcode, an email and a flag.
    """

    def __init__(self, name: str, tripcode: str = "", capcode: str = "", email: str = "",
                 flag: Flag = None):
        self.name = name
        self.tripcode = tripcode
        self.capcode = capcode
        self.email = email
        self.flag = flag

    @classmethod
    def from_raw(cls, post: dict):
        return cls(
            name=post["name"],
            tripcode=post.get("tripcode", ""),
            capcode=post.get("capcode", ""),
            email=post.get("email", ""),
            flag=Flag.from_raw(post["country"]) if post["country"] else None,
        )


class File:
    """
    Represents a file attached to a post. It contains the filename, the original filename, the hash, the extension, the
    mime type, the size, the width and the height of the image. It also contains a boolean to know if the file is a
    spoiler.
    """

    def __init__(self, filename: str, original_filename: str, content_hash: str, extension: str, mime_type: str,
                 size: int, width: int, height: int, is_spoiler: bool = False):
        self.filename = filename
        self.original_filename = original_filename
        self.content_hash = content_hash
        self.extension = extension
        self.mime_type = mime_type
        self.size = size
        self.width = width
        self.height = height
        self.is_spoiler = is_spoiler

    @classmethod
    def from_raw(cls, file: dict):
        geometry = file.get("geometry", None)
        return cls(
            filename=file["filename"],
            original_filename=file["originalFilename"],
            content_hash=file["hash"],
            extension=file["extension"],
            mime_type=file["mimetype"],
            size=file["size"],
            width=geometry["width"] if geometry and "width" in geometry else -1,
            height=geometry["height"] if geometry and "height" in geometry else -1,
            is_spoiler=file.get("spoiler", False)
        )


class Post:
    def __init__(self, timestamp: datetime, board: str, post_id: str, message: str,
                 author: Author, thread: str = "", subject: str = "", files: list[File] = None):
        self.timestamp = timestamp
        self.board = board
        self.post_id = post_id
        self.is_thread = thread == ""
        self.thread_id = thread or post_id
        self.subject = subject
        self.message = message
        self.author = author
        self.files = files or []

    @classmethod
    def from_raw(cls, post: dict):
        return cls(
            # timestamp=datetime.fromisoformat(post["date"][:-1]),  # Drops the Z
            timestamp=datetime.strptime(post["date"], '%Y-%m-%dT%H:%M:%S.%fZ'),
            board=post["board"],
            post_id=post["postId"],
            message=post["nomarkup"],
            author=Author.from_raw(post),
            thread=post.get("thread", ""),
            subject=post.get("subject", ""),
            files=[File.from_raw(file) for file in post.get("files", [])],
        )

    def has_capcode(self) -> bool:
        """
        Indicates if the post has a capcode.
        :return: True if the post has a capcode, False otherwise
        """
        # For some reason capcode is None in boards (e.g. None if empty in /b/ but not in global management)
        if self.author.capcode is None:
            return False
        return self.author.capcode != ""

    def has_files(self) -> bool:
        """
        Indicates if the post has files.
        :return: True if the post has files, False otherwise
        """
        return len(self.files) > 0

    def has_geo_flag(self) -> bool:
        """
        Indicates if the post has a geographic flag.
        :return: True if the post has a geographic flag, False otherwise
        """
        return self.author.flag is not None and not self.author.flag.is_custom

    def get_url(self) -> str:
        """
        Returns the URL of the post.
        :return: The relative URL of the post
        """
        thread_url = f"{self.board}/thread/{self.thread_id}.html"
        if self.is_thread:
            return thread_url
        return f"{thread_url}#{self.post_id}"

    def get_manage_url(self) -> str:
        """
        Returns the URL of the post in the management view.
        :return: The relative URL of the post in the management view
        """
        thread_url = f"{self.board}/manage/thread/{self.thread_id}"
        if self.is_thread:
            return thread_url
        return f"{thread_url}/#{self.post_id}"
