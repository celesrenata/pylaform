from datetime import datetime

from pylaform.utilities.commands import listify
from pylaform.commands.db.query import Get
from pylatex import escape_latex, NoEscape
import re


class Commands:
    """
    Package of commands build from pylatex
    :return: None
    """

    def __init__(self):
        self.queries = Get()

    @staticmethod
    def unique(list1):
        """
        Returns only unique values of a list
        :param list list1: source list
        :return: list
        """
        # initialize a null list
        unique_list = []

        # traverse for all elements
        for x in list1:
            # check if exists in unique_list or not
            if x not in unique_list:
                unique_list.append(x)

        return unique_list

    @staticmethod
    def format_date(date_date):
        """
        Reformat ('YYYY-MM-DD') into 'Month - Year'
        :param Any date_date:
        :return: str
        """
        if isinstance(date_date, str):
            date_date = datetime.strptime(date_date, "%Y-%m-%d")
        if datetime.strftime(date_date, "%Y-%m-%d") == '9999-01-01':
            return ""

        return datetime.strftime(date_date, "%B %Y")

    @staticmethod
    def hyperlink(text, url):
        """
        Create a hyperlink in the document
        :param str url:
        :param str text:
        :return: object
        """
        text = escape_latex(text)
        return NoEscape(r'\href{' + url + '}{' + text + '}')

    @staticmethod
    def textbox(short, long):
        concat = NoEscape(
            r"\pdfmarkupcomment[markup=Underline,opacity=0.2]{"
            + f"{short}"
            + r"}{"
            + f"{long}"
            + r"}")
        return concat

    @staticmethod
    def vspace(size):
        return NoEscape(r"\vspace{" + size + r" in}")

    @staticmethod
    def hspace(size):
        return NoEscape(r"\nobreak\hspace{" + str(size) + r" em}")

    def glossary_inject(self, text, link_type):
        """
        Scan source text for matching substrings and add pdfcomments to them.
        :param str text: source text
        :param str link_type: available options are modern and retro
        :return: Any
        """

        glossary = listify(self.queries.get_glossary())
        search_terms = Commands.unique([sub['term'] for sub in glossary])
        updated_text = r"" + text
        for term in search_terms:
            if re.search(f" {term} ", text):
                if link_type == "modern":
                    updated_text = updated_text.replace(
                        term, Commands.textbox(
                            term, [sub['description'] for sub in glossary if sub['term'] == term][0]))
                else:
                    updated_text = updated_text.replace(
                        term, Commands.hyperlink(
                            term, [sub['url'] for sub in glossary if sub['term'] == term][0]))

        return updated_text
