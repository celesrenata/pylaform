from pylaform.commands.latex import Commands
from pylaform.commands.db.query import Get
from pylatex import Command, Document, Package, Section, Subsection
from pylatex.utils import NoEscape
from tenacity import stop_after_delay, retry
from .common import Common


class Generator:
    """
    Main logic for generating the hybrid format resume.
    :return: None
    """

    def __init__(self):
        self.resume_data = Get()
        self.cmd = Commands()
        self.common = Common()
        self.doc = Document()

    def run(self):
        # DocumentClass
        self.doc.documentclass = Command('documentclass', options=['margin', 'line'], arguments='res')

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
        self.doc.packages.append(Package('hyperref'))
        self.doc.packages.append(Package('xcolor'))
        self.doc.packages.append(Package('pdfcomment'))
        self.doc.append(NoEscape(
            r"""\hypersetup{
            pdfborder={0 0 0},
            pdfborderstyle={/S/U/W 1},
            urlbordercolor=blue
            }"""))
        # self.doc.append(NoEscape(r"\let\nofiles\relax"))
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
        self.doc.create(NoEscape(r'\end{resume}'))
        self.generate()

    @retry(stop=(stop_after_delay(10)))
    def generate(self):
        """
        Hammer PyLatex until it soulpos gives in.
        :return:
        """

        self.doc.generate_pdf('data/hybrid', clean_tex=True)
        self.doc.generate_tex('data/hybrid')
