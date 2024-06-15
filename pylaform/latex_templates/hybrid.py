from pylaform.commands.db.query import Queries
from pylaform.commands.latex import Commands
from pylatex import Command, Document, Package
from pylatex.utils import NoEscape
from tenacity import retry, stop_after_delay
from .common import Common
import os


class Generator:
    """
    Class for generating the hybrid format resume.
    :return: None
    """

    def __init__(self) -> None:
        self.resume_data = Queries()
        self.cmd = Commands()
        self.common = Common()
        self.doc = Document()

    def run(self) -> None:
        """
        Class main logic.
        :return None: None
        """

        # DocumentClass
        self.doc.documentclass = Command("documentclass", options=["margin", "line"], arguments="res")
        # Margins
        self.doc.append(NoEscape(r"""
            \oddsidemargin - .5 in
            \evensidemargin - .5 in
            \voffset = 0 in
            \textwidth = 6.0 in
            \textheight = 9 in
            \itemsep = 0 in
            \parsep = 0 in

            \newenvironment
            {list1}
            {
            \begin
            {list}
            {\ding
            {113}}{ %
            \setlength
            {\itemsep}{0 in}
            \setlength
            {\parsep}{0 in} \setlength
            {\parskip}{0 in}
            \setlength
            {\topsep}{0 in} \setlength
            {\partopsep}{0 in}
            \setlength
            {\leftmargin}{0.17 in}}}{\end
            {list}}
            \newenvironment
            {list2}
            {
            \begin
            {list}
            {$\bullet$}{ %
            \setlength
            {\itemsep}{0 in}
            \setlength
            {\parsep}{0 in} \setlength
            {\parskip}{0 in}
            \setlength
            {\topsep}{0 in} \setlength
            {\partopsep}{0 in}
            \setlength
            {\leftmargin}{0.2 in}}}{\end
            {list}}
            \newenvironment
            {list3}
            {
            \begin
            {list}
            {$\circ$}{ %
            \setlength
            {\itemsep}{0 in}
            \setlength
            {\parsep}{0 in} \setlength
            {\parskip}{0 in}
            \setlength
            {\topsep}{0 in} \setlength
            {\partopsep}{0 in}
            \setlength
            {\leftmargin}{0.2 in}}}{\end
            {list}}"""))

        # Plugins
        self.doc.packages.append(Package("hyperref"))
        self.doc.packages.append(Package("xcolor"))
        self.doc.packages.append(Package("pdfcomment"))
        self.doc.append(NoEscape(
            r"""\hypersetup{
            pdfborder={0 0 0},
            pdfborderstyle={/S/U/W 1},
            urlbordercolor=blue
            }"""))
        # self.doc.append(NoEscape(r"\setlist[itemize]{itemjoin=\hspace*{0.5em},itemjoin*=\hspace*{0.5em}}"))

        # Start Page
        # Contact Information
        self.common.retro_contact_header(self.doc)

        # Summary
        self.common.retro_summary_details(self.doc)

        # Skills
        self.common.retro_skills(self.doc)

        # Work History
        self.common.retro_work_history(self.doc)

        # End Page
        self.doc.append(NoEscape(r"\end{resume}"))
        self.generate()

    @retry(stop=(stop_after_delay(10)))
    def generate(self) -> None:
        """
        Hammer PyLatex until it soulpos gives in.
        :return None: None
        """

        self.doc.generate_tex("data/hybrid")

        norelax = r"\let\nofiles\relax"
        with open("data/hybrid.tex", 'r+') as f:
            content = f.read()
            f.seek(0, 0)
            f.write(norelax.rstrip('\r\n') + '\n' + content)
        os.system("pdflatex -output-directory data/ data/hybrid.tex ")
        #self.doc.generate_pdf("data/hybrid", clean_tex=True)
