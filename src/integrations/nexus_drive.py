"""
Nexus Drive Manager para SuperNEXUS v2
Google Drive integration async
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class NexusDriveManager:
    """Gestor de Google Drive async"""

    SCOPES = ['https://www.googleapis.com/auth/drive.file',
              'https://www.googleapis.com/auth/drive.metadata.readonly']

    def __init__(self, credentials_path: str = None, token_path: str = None):
        base = Path(__file__).parent.parent.parent / "config" / "drive"
        self.credentials_path = Path(credentials_path) if credentials_path else base / "credentials.json"
        self.token_path = Path(token_path) if token_path else base / "token.pickle"
        self.service = None

    async def authenticate(self) -> bool:
        try:
            import pickle
            import google.auth.transport.requests
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            creds = None
            if self.token_path.exists():
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(google.auth.transport.requests.Request())
                else:
                    if not self.credentials_path.exists():
                        logger.error(f"No se encontro {self.credentials_path}")
                        return False
                    flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_path), self.SCOPES)
                    creds = flow.run_local_server(port=0)

                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)

            loop = asyncio.get_event_loop()
            self.service = await loop.run_in_executor(None, lambda: build('drive', 'v3', credentials=creds))
            logger.info("Google Drive autenticado")
            return True
        except ImportError:
            logger.error("google-api-python-client no disponible. pip install google-api-python-client google-auth-oauthlib")
            return False
        except Exception as e:
            logger.error(f"Drive auth error: {e}")
            return False

    async def create_folder(self, folder_name: str) -> Optional[str]:
        if not self.service:
            if not await self.authenticate():
                return None

        loop = asyncio.get_event_loop()
        file_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}

        def _create():
            return self.service.files().create(body=file_metadata, fields='id').execute()

        try:
            folder = await loop.run_in_executor(None, _create)
            folder_id = folder.get('id')
            logger.info(f"Carpeta creada: {folder_name} (ID: {folder_id})")
            return folder_id
        except Exception as e:
            logger.error(f"Error creando carpeta: {e}")
            return None

    async def upload_file(self, file_path: str, folder_id: str = None) -> Optional[str]:
        if not self.service:
            if not await self.authenticate():
                return None

        from googleapiclient.http import MediaFileUpload

        file_name = os.path.basename(file_path)
        file_metadata = {'name': file_name}
        if folder_id:
            file_metadata['parents'] = [folder_id]

        loop = asyncio.get_event_loop()
        media = await loop.run_in_executor(None, lambda: MediaFileUpload(file_path, resumable=True))

        def _upload():
            return self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()

        try:
            file = await loop.run_in_executor(None, _upload)
            file_id = file.get('id')
            logger.info(f"Archivo subido: {file_name} (ID: {file_id})")
            return file_id
        except Exception as e:
            logger.error(f"Error subiendo archivo: {e}")
            return None

    def get_status(self) -> dict:
        return {
            "authenticated": self.service is not None,
            "credentials_path": str(self.credentials_path),
        }
