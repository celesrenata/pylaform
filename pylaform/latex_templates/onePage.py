from pylaform.commands.latex import Commands
from pylaform.utilities.commands import fatten, listify
from pylaform.commands.db.query import Get
from pylatex import Document, Package, Section, Subsection
from pylatex.utils import NoEscape
from tenacity import stop_after_delay, retry
from .common import Common


class Generator:
    """
    Main logic for generating the single page resume.
    :return: None
    """
    
    def __init__(self):
        self.resume_data = Get()
        self.cmd = Commands()
        self.common = Common()
        # Margins
        geometry_options = {
            "head": "0in",
            "margin": "0.5in",
            "bottom": "0.5in",
            "includeheadfoot": True
        }
        self.doc = Document(geometry_options={
            "head": "0in",
            "margin": "0.5in",
            "bottom": "0.5in",
            "includeheadfoot": True
        })

    def run(self):
        # Plugins
        self.doc.packages.append(Package('hyperref'))
        self.doc.packages.append(Package('bookmark'))
        self.doc.packages.append(Package('pdfcomment'))
        self.doc.packages.append(Package('setspace'))
        self.doc.packages.append(Package('enumitem', "inline"))
        self.doc.append(NoEscape(r"""\hypersetup{
                                pdfborder={0 0 0},
                                pdfborderstyle={/S/U/W 0}
                                }"""))
        self.doc.append(NoEscape(r"\linespread{0.4}"))
        self.doc.append(NoEscape(r"\setlist{nosep}"))
        self.doc.append(NoEscape(r"\setlist[itemize]{itemjoin=\hspace*{0.5em},itemjoin*=\hspace*{0.5em}}"))
        
        # Start Page
        # Contact Information
        self.common.modern_contact_header(self.doc)

        # Summary
        self.common.modern_summary_details(self.doc)
        
        # Skills
        self.common.modern_skills(self.doc)
        
        # Work History
        self.common.modern_work_history(self.doc)
        
        # End Page
        self.doc.create(NoEscape(r'\end{document}'))
        self.generate()

    @retry(stop=(stop_after_delay(10)))
    def generate(self):
        """
        Hammer PyLatex until it soulpos gives in.
        :return: 
        """
        
        self.doc.generate_pdf('data/one-page', clean_tex=True)
        self.doc.generate_tex('data/one-page')
