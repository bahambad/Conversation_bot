class UserFacingError(Exception):
    """Ошибка, текст которой (HTML) можно показать пользователю как есть."""

    text = "⛔️ <b>Something went wrong.</b>\nPlease try again later."

    def __init__(self, text: str | None = None) -> None:
        if text is not None:
            self.text = text
        super().__init__(self.text)


class FileTooBigError(UserFacingError):
    text = ("⛔️ <b>The file is too big.</b>\n"
            "Please send a file smaller than <b>20 MB</b>.")


class ProcessingError(UserFacingError):
    text = ("⛔️ <b>Failed to process the file.</b>\n"
            "It may be damaged or in an unsupported format.")


class VideoTooLongError(UserFacingError):
    text = "⛔️ The bot can <b>ONLY</b> process videos <b>SHORTER than 60 seconds!</b>"


class UserBusyError(UserFacingError):
    text = "⏳ Your previous request is still being processed. Please wait until it's finished."


class UnsupportedUrlError(UserFacingError):
    text = "⛔️ <b>This link is not supported.</b>"


class MediaTooBigError(UserFacingError):
    text = ("⛔️ <b>The media is too big.</b>\n"
            "I can only download files smaller than <b>20 MB</b>.")


class MediaDownloadError(UserFacingError):
    text = ("⛔️ <b>I can't download it.</b>\n"
            "The link may be private, unavailable or not supported.")
