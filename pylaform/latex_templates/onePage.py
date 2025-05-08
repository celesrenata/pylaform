# onePage.py
from pylaform.commands.db.query import Queries
from pylaform.commands.latex import Commands
from pylatex import Document, Package
from pylatex.utils import NoEscape
import logging
import os
from .common import Common


class Generator:
    """
    Class for generating the single page resume.
    :return: None
    """

    def __init__(self) -> None:
        self.resume_data = Queries()
        self.cmd = Commands()
        self.common = Common()

        # Margins
        self.doc = Document(geometry_options={
            "head": "0in",
            "margin": "0.5in",
            "bottom": "0.5in",
            "includeheadfoot": True
        })

    def run(self) -> None:
        """
        Class main logic.
        :return None: None
        """

        # Let no files relax
        self.doc.append(NoEscape(r"\let\nofiles\relax"))

        # Plugins
        self.doc.packages.append(Package("hyperref"))
        self.doc.packages.append(Package("bookmark"))
        self.doc.packages.append(Package("pdfcomment"))
        self.doc.packages.append(Package("setspace"))

        # Fix: Use enumitem package without the inline option to avoid LaTeX errors
        self.doc.packages.append(Package("enumitem"))

        # Set up hyperref
        self.doc.append(NoEscape(r"""\hypersetup{
                                pdfborder={0 0 0},
                                pdfborderstyle={/S/U/W 0}
                                }"""))
        # Set line spacing
        self.doc.append(NoEscape(r"\linespread{0.4}"))
        self.doc.append(NoEscape(r"\setlist{nosep}"))

        # Configure inline itemized lists
        self.doc.append(NoEscape(r"\setlist[itemize*]{itemjoin=\hspace*{0.5em},itemjoin*=\hspace*{0.5em}}"))

        # Start page
        # Contact Information
        self.common.modern_contact_header(self.doc)

        # Summary
        self.common.modern_summary_details(self.doc)

        # Skills
        self.common.modern_skills(self.doc)

        # Work History
        self.common.modern_work_history(self.doc)

        # Education
        self.common.modern_education(self.doc)

        # End page
        self.doc.append(NoEscape(r"\end{document}"))

        # Generate the page with better error handling
        try:
            # First generate the tex file
            self.doc.generate_tex("data/one-page")

            try:
                # Try the standard PyLaTeX PDF generation
                self.doc.generate_pdf("data/one-page", clean_tex=False)
            except Exception as e:
                import logging
                logging.warning(f"PyLaTeX PDF generation had issues: {str(e)}")
                logging.info("Attempting direct LaTeX compilation as fallback...")

                # Use direct compilation method instead
                from pylaform.commands.latex import Commands
                pdf_path = Commands.compile_latex_document("data/one-page.tex")
                if not pdf_path:
                    raise Exception("Both PDF generation methods failed")
        except Exception as e:
            import logging
            logging.error(f"Error generating PDF: {str(e)}")
            raise

    @Commands.with_limited_retries(max_attempts=1)
    def generate(self) -> None:
        """
        Generate PDF with proper error handling.
        :return None: None
        """
        try:
            # First generate the tex file to make sure it's created
            self.doc.generate_tex("data/one-page")

            # Use our enhanced LaTeX compilation
            tex_file_path = "data/one-page.tex"

            # Try to generate the PDF but don't let it retry infinitely
            try:
                # Original PyLaTeX call
                self.doc.generate_pdf("data/one-page", clean_tex=False)
            except Exception as e:
                logging.warning(f"PyLaTeX PDF generation had issues: {str(e)}")
                logging.info("Attempting direct LaTeX compilation as fallback...")

                # Fallback to our direct compilation method
                pdf_path = Commands.compile_latex_document(tex_file_path)
                if pdf_path:
                    logging.info(f"Fallback PDF generation successful: {pdf_path}")
                else:
                    logging.error("Both PDF generation methods failed")
                    raise

        except Exception as e:
            logging.error(f"Error generating PDF: {str(e)}")
            # Let the decorator handle the retry
            raise
