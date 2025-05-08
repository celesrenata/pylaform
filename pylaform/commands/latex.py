from datetime import datetime
from pylaform.commands.db.query import Queries
from pylaform.utilities.commands import listify, unique
from pylatex import escape_latex, NoEscape
import re
import logging
import subprocess
import os
from functools import wraps


class Commands:
    """
    Package of commands build from PyLatex.
    :return: None
    """

    def __init__(self) -> None:
        self.queries = Queries()

    @staticmethod
    def with_limited_retries(max_attempts=2):
        """
        Decorator to limit retries on functions and continue on failure.
        """

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                attempts = 0
                last_error = None

                while attempts < max_attempts:
                    try:
                        result = func(*args, **kwargs)
                        # If we get here, the function succeeded
                        return result
                    except Exception as e:
                        last_error = e
                        logging.warning(f"Attempt {attempts + 1}/{max_attempts} failed: {str(e)}")
                        attempts += 1

                # If we get here, all attempts failed
                logging.error(
                    f"Function {func.__name__} failed after {max_attempts} attempts. Last error: {str(last_error)}")
                logging.info(f"Continuing execution despite LaTeX compilation errors")
                # Return a default value or None to allow execution to continue
                return None

            return wrapper

        return decorator

    @staticmethod
    def compile_latex_document(tex_file_path):
        """
        Compile a LaTeX document directly using latexmk.

        Args:
            tex_file_path: Path to the .tex file

        Returns:
            Path to the generated PDF file or None if compilation failed
        """
        import subprocess
        import os
        import logging

        if not os.path.exists(tex_file_path):
            logging.error(f"LaTeX file not found: {tex_file_path}")
            return None

        pdf_path = tex_file_path.replace('.tex', '.pdf')

        # If PDF is already up-to-date, skip compilation
        if os.path.exists(pdf_path):
            if os.path.getmtime(pdf_path) >= os.path.getmtime(tex_file_path):
                logging.info(f"PDF {pdf_path} is up-to-date. Skipping compilation.")
                return pdf_path

        # Directory containing the .tex file
        working_dir = os.path.dirname(tex_file_path)

        try:
            # Run latexmk with appropriate options
            result = subprocess.run(
                [
                    'latexmk',
                    '--pdf',
                    '--interaction=nonstopmode',
                    tex_file_path
                ],
                cwd=working_dir,
                capture_output=True,
                text=True
            )

            # Check if compilation succeeded
            if result.returncode == 0:
                if os.path.exists(pdf_path):
                    logging.info(f"Successfully compiled {tex_file_path} to {pdf_path}")
                    return pdf_path
                else:
                    logging.error(f"PDF file not created despite successful compilation: {pdf_path}")
                    return None
            else:
                logging.error(f"LaTeX compilation failed with return code {result.returncode}")
                logging.error(f"LaTeX compiler output: {result.stdout}\n{result.stderr}")
                return None

        except Exception as e:
            logging.error(f"Exception during LaTeX compilation: {str(e)}")
            return None

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

        escaped_text: str = escape_latex(text)
        return NoEscape(r"\href{" + url + "}{" + escaped_text + "}")

    @staticmethod
    def textbox(short: str, long: str) -> str:
        """
        Create pdfcomment text box.
        Used for glossary terms.
        :param str short: Short description.
        :param str long: Long description.
        :return str: PyLatex compiled text.
        """

        concat: str = NoEscape(
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

        glossary: list[dict[str, str | bool]] = listify(self.queries.get_glossary())
        search_terms: list[str] = unique([sub["term"] for sub in glossary])
        updated_text: str = r"" + text
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

    @staticmethod
    def cleanup_latex_files(directory):
        """
        Clean up auxiliary LaTeX files in the specified directory.
        """
        for file in os.listdir(directory):
            if file.endswith(('.aux', '.fls', '.fdb_latexmk', '.log', '.out', '.upa', '.upb')):
                try:
                    os.remove(os.path.join(directory, file))
                    logging.debug(f"Removed auxiliary LaTeX file: {file}")
                except OSError as e:
                    logging.warning(f"Failed to remove file {file}: {str(e)}")

    @staticmethod
    def contact_flatten(contact_data=None):
        """
        Flatten contact information from DB format to dict format.

        Args:
            contact_data (list, optional): Raw contact data. If None, data will be fetched.

        Returns:
            dict: Flattened contact information with keys like 'name', 'email', etc.
        """
        from pylaform.commands.db.queries import Queries
        import logging

        try:
            # If no data provided, fetch from database
            if contact_data is None:
                queries = Queries()
                contact_data = queries.get_contact_information()

            # Initialize result dictionary
            result = {}

            # Process each contact item
            for item in contact_data:
                # Only process active (state=1) items
                if item.get('state', 0) == 1:
                    contact_type = item.get('attr')

                    # Store value in result dictionary
                    result[contact_type] = {
                        'value': item.get('value', ''),
                        'state': item.get('state', 0)
                    }

                    # Also store the contacttype value if present
                    if contact_type == 'contacttype':
                        result['contacttype'] = {
                            'value': item.get('value', ''),
                            'state': item.get('state', 0)
                        }

            return result
        except Exception as e:
            logging.error(f"Error in contact_flatten: {str(e)}")
            # Return empty dictionary on error
            return {}

    @staticmethod
    def skills_flatten(skills_data=None):
        """
        Flatten skills information from DB format to a more usable dict format.

        Args:
            skills_data (list, optional): Raw skills data. If None, data will be fetched.

        Returns:
            dict: Dictionary of skills organized by category and subcategory.
        """
        from pylaform.commands.db.query import Queries
        import logging

        try:
            # If no data provided, fetch from database
            if skills_data is None:
                queries = Queries()
                skills_data = queries.get_skills()

            # Initialize result dictionary
            result = {}

            # Process each skill item
            for item in skills_data:
                # Only process active (state=1) items
                if item.get('state', 0) == 1:
                    skill_id = item.get('id')
                    attr = item.get('attr')
                    value = item.get('value', '')

                    # Initialize the skill if it doesn't exist in our result
                    if skill_id not in result:
                        result[skill_id] = {
                            'id': skill_id,
                            'state': item.get('state', 0)
                        }

                    # Add this attribute to the skill object
                    result[skill_id][attr] = value

            # Convert the dict of skills to a list
            skills_list = list(result.values())

            # Create a hierarchical structure organized by category and subcategory
            organized = {}
            for skill in skills_list:
                category = skill.get('category', 'Uncategorized')
                subcategory = skill.get('subcategory', 'General')

                if category not in organized:
                    organized[category] = {}

                if subcategory not in organized[category]:
                    organized[category][subcategory] = []

                organized[category][subcategory].append(skill)

            return organized
        except Exception as e:
            logging.error(f"Error in skills_flatten: {str(e)}")
            # Return empty dictionary on error
            return {}