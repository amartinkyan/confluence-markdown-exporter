"""Unit tests for Attachment class."""

from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from confluence_markdown_exporter.confluence import Attachment
from confluence_markdown_exporter.confluence import Space
from confluence_markdown_exporter.confluence import User
from confluence_markdown_exporter.confluence import Version


@pytest.fixture
def space() -> Space:
    """Return a minimal Space with no homepage to avoid API calls."""
    return Space(
        base_url="https://test.atlassian.net",
        key="TEST",
        name="Test Space",
        description="",
        homepage=None,
    )


@pytest.fixture
def version() -> Version:
    """Return a minimal Version."""
    user = User(
        account_id="",
        username="",
        display_name="",
        public_name="",
        email="",
    )
    return Version(
        number=1,
        when="2024-01-01T00:00:00.000Z",
        friendly_when="Jan 1, 2024",
        by=user,
    )


def _make_attachment(space: Space, version: Version, file_id: str, att_id: str) -> Attachment:
    return Attachment(
        base_url="https://test.atlassian.net",
        title="document.pdf",
        space=space,
        ancestors=[],
        version=version,
        id=att_id,
        file_size=1024,
        media_type="application/pdf",
        media_type_description="PDF",
        file_id=file_id,
        collection_name="",
        download_link="/download/attachments/123/document.pdf",
        comment="",
    )


class TestAttachmentFileIdFallback:
    """Tests that attachment_file_id falls back to attachment ID when fileId is absent."""

    @patch("confluence_markdown_exporter.confluence.settings")
    def test_export_path_uses_file_id_when_present(
        self, mock_settings: MagicMock, space: Space, version: Version
    ) -> None:
        """export_path uses file_id when it is non-empty."""
        mock_settings.export.attachment_path = (
            "attachments/{attachment_file_id}{attachment_extension}"
        )
        mock_settings.export.filename_encoding = ""
        mock_settings.export.filename_lowercase = False
        mock_settings.export.filename_length = 255

        att = _make_attachment(space, version, file_id="abc-uuid-123", att_id="att99")
        assert att.export_path == Path("attachments/abc-uuid-123.pdf")

    @patch("confluence_markdown_exporter.confluence.settings")
    def test_export_path_falls_back_to_attachment_id_when_file_id_empty(
        self, mock_settings: MagicMock, space: Space, version: Version
    ) -> None:
        """export_path uses attachment ID when file_id is empty (Confluence Server)."""
        mock_settings.export.attachment_path = (
            "attachments/{attachment_file_id}{attachment_extension}"
        )
        mock_settings.export.filename_encoding = ""
        mock_settings.export.filename_lowercase = False
        mock_settings.export.filename_length = 255

        att = _make_attachment(space, version, file_id="", att_id="att42")
        assert att.export_path == Path("attachments/att42.pdf")

    @patch("confluence_markdown_exporter.confluence.settings")
    def test_multiple_attachments_get_unique_paths_without_file_id(
        self, mock_settings: MagicMock, space: Space, version: Version
    ) -> None:
        """Two attachments without file_id but different IDs get distinct export paths."""
        mock_settings.export.attachment_path = (
            "attachments/{attachment_file_id}{attachment_extension}"
        )
        mock_settings.export.filename_encoding = ""
        mock_settings.export.filename_lowercase = False
        mock_settings.export.filename_length = 255

        att1 = _make_attachment(space, version, file_id="", att_id="att1")
        att2 = _make_attachment(space, version, file_id="", att_id="att2")
        assert att1.export_path != att2.export_path
        assert att1.export_path == Path("attachments/att1.pdf")
        assert att2.export_path == Path("attachments/att2.pdf")
