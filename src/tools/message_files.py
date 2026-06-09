import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from src.tools.encryption import decrypt_bytes, encrypt_bytes
from src.tools.settings import Settings

DEFAULT_MESSAGE_UPLOAD_FOLDER = 'startup/message_files'


@dataclass(frozen=True)
class SavedAttachment:
    file_path: str
    file_ext: str | None


def _reject_unsafe_upload_folder(path: Path) -> None:
    resolved = path.resolve(strict=False)
    if resolved == Path(resolved.anchor) or resolved == Path.cwd().resolve():
        raise ValueError('Message upload folder must be a dedicated subdirectory')


def message_upload_folder_path(settings: Settings | None = None) -> Path:
    settings = settings or Settings()
    configured = settings.get('settings', {}).get(
        'message_upload_folder',
        DEFAULT_MESSAGE_UPLOAD_FOLDER,
    )
    path = Path(configured)
    _reject_unsafe_upload_folder(path)
    return path


def ensure_message_upload_folder(settings: Settings | None = None) -> Path:
    path = message_upload_folder_path(settings)
    path.mkdir(parents=True, exist_ok=True)
    return path


def prepare_message_upload_folder(settings: Settings | None = None) -> Path:
    """Create the message upload folder and clear previous runtime files."""
    path = message_upload_folder_path(settings)
    if path.exists() and not path.is_dir():
        raise NotADirectoryError(f'Message upload path is not a directory: {path}')

    if path.is_dir():
        for child in path.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
    else:
        path.mkdir(parents=True, exist_ok=True)

    return path


def save_message_attachment(
    attachment: FileStorage | None,
    settings: Settings | None = None,
) -> SavedAttachment | None:
    if attachment is None or not attachment.filename:
        return None

    upload_folder = ensure_message_upload_folder(settings)
    filename = secure_filename(attachment.filename) or 'attachment'
    file_ext = Path(filename).suffix or None
    storage_name = f'{uuid.uuid4().hex}_{filename}.enc'
    path = upload_folder / storage_name
    encrypted = encrypt_bytes(attachment.read())
    path.write_bytes(encrypted)
    return SavedAttachment(file_path=str(path), file_ext=file_ext)


def read_message_attachment(file_path: str) -> bytes:
    return decrypt_bytes(Path(file_path).read_bytes())
