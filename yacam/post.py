from datetime import datetime


class Country:
    def __init__(self, name: str, code: str, is_custom: bool = False):
        self.name = name
        self.code = code
        self.is_custom = is_custom

    @classmethod
    def from_raw(cls, country: dict):
        return cls(
            name=country["name"],
            code=country["code"],
            is_custom=country.get("custom", False)
        )


class Author:
    def __init__(self, name: str, tripcode: str = "", capcode: str = "", email: str = "",
                 country: Country = None):
        self.name = name
        self.tripcode = tripcode
        self.capcode = capcode
        self.email = email
        self.country = country

    @classmethod
    def from_raw(cls, post: dict):
        return cls(
            name=post["name"],
            tripcode=post.get("tripcode", ""),
            capcode=post.get("capcode", ""),
            email=post.get("email", ""),
            country=Country.from_raw(post["country"]) if post["country"] else None,
        )


class File:
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
        return cls(
            filename=file["filename"],
            original_filename=file["originalFilename"],
            content_hash=file["hash"],
            extension=file["extension"],
            mime_type=file["mimetype"],
            size=file["size"],
            width=file["geometry"]["width"],
            height=file["geometry"]["height"],
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
            timestamp=datetime.fromisoformat(post["date"][:-1]),  # Drops the Z
            board=post["board"],
            post_id=post["postId"],
            message=post["nomarkup"],
            author=Author.from_raw(post),
            thread=post.get("thread", ""),
            subject=post.get("subject", ""),
            files=[File.from_raw(file) for file in post.get("files", [])],
        )

    def has_capcode(self):
        # For some reason capcode is None in boards (e.g. None if empty in /b/ but not in global management)
        if self.author.capcode is None:
            return False
        return self.author.capcode != ""

    def has_files(self):
        return len(self.files) > 0

    def is_from_country(self, codes: list[str]):
        return self.author.country is not None and not self.author.country.is_custom and self.author.country.code in codes

    def url(self):
        thread_url = f"{self.board}/thread/{self.thread_id}.html"
        if self.is_thread:
            return thread_url
        return f"{thread_url}#{self.post_id}"

    def manage_url(self):
        thread_url = f"{self.board}/manage/thread/{self.thread_id}"
        if self.is_thread:
            return thread_url
        return f"{thread_url}/#{self.post_id}"
