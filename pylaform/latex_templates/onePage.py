from pylaform.commands.db.query import Queries
from pylaform.commands.latex import Commands
from pylatex import Document, Package
from pylatex.utils import NoEscape
from tenacity import retry, stop_after_delay
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
        self.doc.packages.append(Package("enumitem", "inline"))
        self.doc.append(NoEscape(r"""\hypersetup{
                                pdfborder={0 0 0},
                                pdfborderstyle={/S/U/W 0}
                                }"""))
        self.doc.append(NoEscape(r"\linespread{0.4}"))
        self.doc.append(NoEscape(r"\setlist{nosep}"))
        self.doc.append(NoEscape(r"\setlist[itemize]{itemjoin=\hspace*{0.5em},itemjoin*=\hspace*{0.5em}}"))
        
        # Start page
        # Contact Information
        self.common.modern_contact_header(self.doc)

        # Summary
        self.common.modern_summary_details(self.doc)
        
        # Skills
        self.common.modern_skills(self.doc)
        
        # Work History
        self.common.modern_work_history(self.doc)
        
        # End page
        self.doc.create(NoEscape(r"\end{document}"))

        # Generate the page
        self.generate()

    @retry(stop=(stop_after_delay(10)))
    def generate(self) -> None:
        """
        Hammer PyLatex until it soulpos gives in.
        :return None: None
        """
        
        self.doc.generate_pdf("data/one-page", clean_tex=True)
        self.doc.generate_tex("data/one-page")
