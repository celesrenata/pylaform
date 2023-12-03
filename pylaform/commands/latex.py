from datetime import datetime
from pylaform.commands.db.query import Get
from pylaform.utilities.commands import listify, unique
from pylatex import escape_latex, NoEscape
import re


class Commands:
    """
    Package of commands build from PyLatex.
    :return: None
    """

    def __init__(self) -> None:
        self.queries = Get()

    @staticmethod
    def format_date(date_date: datetime | str) -> str:
        """
        Reformat ('YYYY-MM-DD') into 'Month - Year.'
        :param datetime | str date_date: Date object.
        :return str: Stringified version of date.
        """

        if isinstance(date_date, str):
            date_date = datetime.strptime(date_date, "%Y-%m-%d")
        if datetime.strftime(date_date, "%Y-%m-%d") == '9999-01-01':
            return ""

        return datetime.strftime(date_date, "%B %Y")

    @staticmethod
    def hyperlink(text: str, url: str) -> str:
        """
        Create a hyperlink in the document
        :param str url: URL.
        :param str text: Description.
        :return str: PyLatex compiled text.
        """

        text = escape_latex(text)
        return NoEscape(r"\href{" + url + "}{" + text + "}")

    @staticmethod
    def textbox(short: str, long: str) -> str:
        """
        Create pdfcomment text box.
        Used for glossary terms.
        :param str short: Short description.
        :param str long: Long description.
        :return str: PyLatex compiled text.
        """

        concat = NoEscape(
            r"\pdfmarkupcomment[markup=Underline,opacity=0.2]{"
            + f"{short}"
            + r"}{"
            + f"{long}"
            + r"}")
        return concat

    @staticmethod
    def vspace(size: str) -> str:
        """
        Moves vertical position of text.
        :param str size: Positive or negative float as string.
        :return str: PyLatex compiled text.
        """

        return NoEscape(r"\vspace{" + size + r" in}")

    @staticmethod
    def hspace(size: str) -> str:
        """
        Moves horizontal position of text.
        :param str size: Positive or negative float as string.
        :return str: PyLatex compiled text.
        """

        return NoEscape(r"\nobreak\hspace{" + str(size) + r" em}")

    def glossary_inject(self, text: str, link_type: str) -> str:
        """
        Scan source text for matching substrings and add pdfcomments to them.
        :param str text: source text
        :param str link_type: available options are modern and retro
        :return str: PyLatex compiled text
        """

        glossary = listify(self.queries.get_glossary())
        search_terms = unique([sub["term"] for sub in glossary])
        updated_text = r"" + text
        for term in search_terms:
            if re.search(f" {term} ", text):
                if link_type == "modern":
                    updated_text = updated_text.replace(
                        term, Commands.textbox(
                            term, [sub["description"] for sub in glossary if sub["term"] == term][0]))
                else:
                    updated_text = updated_text.replace(
                        term, Commands.hyperlink(
                            term, [sub["url"] for sub in glossary if sub["term"] == term][0]))

        return updated_text
