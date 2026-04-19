"""Unit tests for Jira enrichment URL resolution logic."""

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from confluence_markdown_exporter.confluence import _jira_base_url_from_href


class TestJiraBaseUrlFromHref:
    """Tests for the _jira_base_url_from_href helper."""

    @pytest.mark.parametrize(
        ("href", "expected"),
        [
            # Standard Jira Cloud URL
            (
                "https://company.atlassian.net/browse/PROJ-123",
                "https://company.atlassian.net",
            ),
            # Self-hosted Jira on its own subdomain
            (
                "https://jira.company.com/browse/PROJ-123",
                "https://jira.company.com",
            ),
            # Self-hosted Jira with a non-standard port
            (
                "https://jira.company.com:8443/browse/PROJ-123",
                "https://jira.company.com:8443",
            ),
            # HTTP (standard port stripped)
            (
                "http://jira.internal/browse/PROJ-1",
                "http://jira.internal",
            ),
            # Standard HTTPS port 443 is stripped
            (
                "https://jira.company.com:443/browse/PROJ-1",
                "https://jira.company.com",
            ),
            # Standard HTTP port 80 is stripped
            (
                "http://jira.company.com:80/browse/PROJ-1",
                "http://jira.company.com",
            ),
        ],
    )
    def test_extracts_base_url(self, href: str, expected: str) -> None:
        assert _jira_base_url_from_href(href) == expected

    @pytest.mark.parametrize(
        "href",
        [
            None,
            "",
            "/browse/PROJ-123",  # relative URL - no scheme/host
            "not-a-url",
        ],
    )
    def test_returns_none_for_invalid_or_relative(self, href: str | None) -> None:
        assert _jira_base_url_from_href(href) is None


class TestConvertJiraIssueUrlResolution:
    """Verify that convert_jira_issue resolves the Jira server URL correctly."""

    def _make_page_mock(self, base_url: str) -> MagicMock:
        page = MagicMock()
        page.base_url = base_url
        page.body_export = ""
        return page

    def _make_el(self, issue_key: str, href: str) -> MagicMock:
        """Build a minimal BeautifulSoup-like element for a Jira issue macro."""
        from bs4 import BeautifulSoup

        html = (
            f'<span data-jira-key="{issue_key}">'
            f'<a class="jira-issue-key" href="{href}">{issue_key}</a>'
            f"</span>"
        )
        return BeautifulSoup(html, "html.parser").find("span")

    @patch("confluence_markdown_exporter.confluence.JiraIssue.from_key")
    @patch("confluence_markdown_exporter.confluence.get_settings")
    def test_uses_href_base_url_when_no_config_override(
        self,
        mock_get_settings: MagicMock,
        mock_from_key: MagicMock,
    ) -> None:
        """URL derived from link href is used when jira_base_url is not configured."""
        from confluence_markdown_exporter.confluence import Page
        from confluence_markdown_exporter.utils.app_data_store import ExportConfig

        export_cfg = ExportConfig(jira_base_url="", enable_jira_enrichment=True)
        settings = MagicMock()
        settings.export = export_cfg
        mock_get_settings.return_value = settings

        mock_issue = MagicMock()
        mock_issue.key = "PROJ-42"
        mock_issue.summary = "Fix everything"
        mock_from_key.return_value = mock_issue

        page = self._make_page_mock("https://confluence.company.com")
        el = self._make_el("PROJ-42", "https://jira.company.com/browse/PROJ-42")

        converter = Page.Converter(page=page)
        result = converter.convert_jira_issue(el, "PROJ-42", [])

        mock_from_key.assert_called_once_with("PROJ-42", "https://jira.company.com")
        assert "PROJ-42" in result
        assert "Fix everything" in result

    @patch("confluence_markdown_exporter.confluence.JiraIssue.from_key")
    @patch("confluence_markdown_exporter.confluence.get_settings")
    def test_config_jira_base_url_takes_precedence_over_href(
        self,
        mock_get_settings: MagicMock,
        mock_from_key: MagicMock,
    ) -> None:
        """Explicit jira_base_url config override takes priority over href-derived URL."""
        from confluence_markdown_exporter.confluence import Page
        from confluence_markdown_exporter.utils.app_data_store import ExportConfig

        export_cfg = ExportConfig(
            jira_base_url="https://jira.override.com", enable_jira_enrichment=True
        )
        settings = MagicMock()
        settings.export = export_cfg
        mock_get_settings.return_value = settings

        mock_issue = MagicMock()
        mock_issue.key = "PROJ-7"
        mock_issue.summary = "Override test"
        mock_from_key.return_value = mock_issue

        page = self._make_page_mock("https://confluence.company.com")
        el = self._make_el("PROJ-7", "https://jira.company.com/browse/PROJ-7")

        converter = Page.Converter(page=page)
        converter.convert_jira_issue(el, "PROJ-7", [])

        mock_from_key.assert_called_once_with("PROJ-7", "https://jira.override.com")

    @patch("confluence_markdown_exporter.confluence.JiraIssue.from_key")
    @patch("confluence_markdown_exporter.confluence.get_settings")
    def test_falls_back_to_page_base_url_when_href_is_relative(
        self,
        mock_get_settings: MagicMock,
        mock_from_key: MagicMock,
    ) -> None:
        """page.base_url is used as a last resort when the href is relative."""
        from confluence_markdown_exporter.confluence import Page
        from confluence_markdown_exporter.utils.app_data_store import ExportConfig

        export_cfg = ExportConfig(jira_base_url="", enable_jira_enrichment=True)
        settings = MagicMock()
        settings.export = export_cfg
        mock_get_settings.return_value = settings

        mock_issue = MagicMock()
        mock_issue.key = "PROJ-1"
        mock_issue.summary = "Relative href fallback"
        mock_from_key.return_value = mock_issue

        page = self._make_page_mock("https://atlassian-instance.company.com")
        el = self._make_el("PROJ-1", "/browse/PROJ-1")

        converter = Page.Converter(page=page)
        converter.convert_jira_issue(el, "PROJ-1", [])

        mock_from_key.assert_called_once_with("PROJ-1", "https://atlassian-instance.company.com")
