from pylaform.commands.db.query import Queries
from pylaform.commands.latex import Commands
from pylatex import Command, Document, Package
from pylatex.utils import NoEscape
from tenacity import retry, stop_after_delay
from .common import Common
import os
import shutil
import subprocess
import logging


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

        # Margins and list environments
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

        # Hyperref setup
        self.doc.append(NoEscape(
            r"""\hypersetup{
            pdfborder={0 0 0},
            pdfborderstyle={/S/U/W 1},
            urlbordercolor=blue
            }"""))

        # Start Page
        # Contact Information
        self.common.retro_contact_header(self.doc)

        # Summary
        self.common.retro_summary_details(self.doc)

        # Skills
        self.common.retro_skills(self.doc)

        # Work History
        self.common.retro_work_history(self.doc)

        # Education
        self.common.retro_education(self.doc)

        # End Page
        self.doc.append(NoEscape(r"\end{resume}"))

        # Generate the page with better error handling
        try:
            # First generate the tex file
            self.doc.generate_tex("data/hybrid")

            try:
                # Try the standard PyLaTeX PDF generation
                self.doc.generate_pdf("data/hybrid", clean_tex=False)
            except Exception as e:
                import logging
                logging.warning(f"PyLaTeX PDF generation had issues: {str(e)}")
                logging.info("Attempting direct LaTeX compilation as fallback...")

                # Use direct compilation method instead
                from pylaform.commands.latex import Commands
                pdf_path = Commands.compile_latex_document("data/hybrid.tex")
                if not pdf_path:
                    raise Exception("Both PDF generation methods failed")
        except Exception as e:
            import logging
            logging.error(f"Error generating PDF: {str(e)}")
            raise

    # Modified generate method for hybrid.py
    @Commands.with_limited_retries(max_attempts=1)
    def generate(self) -> None:
        """
        Generate hybrid document with proper error handling.
        :return None: None
        """
        try:
            # First generate the tex file to make sure it's created
            self.doc.generate_tex("data/hybrid")

            # Use our enhanced LaTeX compilation
            tex_file_path = "data/hybrid.tex"

            # Try to generate the PDF but don't let it retry infinitely
            try:
                # Original PyLaTeX call
                self.doc.generate_pdf("data/hybrid", clean_tex=False)
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

    def _create_minimal_res_cls(self, output_path):
        """
        Create a minimal res.cls file that provides the basic functionality needed
        :param output_path: Path where to save the res.cls file
        """
        print("Creating minimal res.cls file as fallback")
        minimal_res_cls = r"""
% RESUME DOCUMENT STYLE -- Released 23 Nov 1989
%    for LaTeX version 2.09
% Copyright (C) 1988,1989 by Michael DeCorte

\typeout{Document Style `res' <26 Sep 89>.}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% res.sty
%
% \documentstyle{res}
%
% Copyright (c) 1988 by Michael DeCorte
% Permission to copy all or part of this work is granted, provided that the
% copies are not made or distributed for resale, and that the copyright
% notice and this notice are retained.
%
% THIS WORK IS PROVIDED ON AN "AS IS" BASIS.  THE AUTHOR PROVIDES NO
% WARRANTY WHATSOEVER, EITHER EXPRESS OR IMPLIED, REGARDING THE WORK,
% INCLUDING WARRANTIES WITH RESPECT TO ITS MERCHANTABILITY OR FITNESS
% FOR ANY PARTICULAR PURPOSE.
%
% If you make any improvements, I'd like to hear about them.
%
% Michael DeCorte
% P.O. Box 652
% Potsdam NY 13676
% mrd@sun.soe.clarkson.edu
% mrd@clutx.bitnet
%
% Changes for LaTeX2e -- Venkat Krishnamurthy (Aug 7, 2001)
%
% Added \usepackage{hyperref} and stick the URL into \href{URL}{text}
%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\NeedsTeXFormat{LaTeX2e}[1995/12/01]
\ProvidesClass{res}[2000/05/19 v1.4b Resume class]

\PassOptionsToClass{11pt,12pt}{article}
\LoadClassWithOptions{article}

\newif\if@line
\newif\if@margin

\DeclareOption{line}{\@linetrue}
\DeclareOption{margin}{\@margintrue}

\ExecuteOptions{line}
\ProcessOptions\relax

\if@line
  \newcommand{\myskip}{\smallskip}
\else
  \newcommand{\myskip}{\medskip}
\fi

\newenvironment{resume}{\begin{document}}{\end{document}}

\def\name#1{\def\@name{#1}}
\def\@name{}
\def\section#1{\@startsection{section}{1}{\z@}{2ex plus .5ex}{1ex}{\centering\large\bf #1}}

\let\oldtext\textbf
\renewcommand{\textbf}[1]{{\oldtext{#1}}}

\renewcommand{\em}[1]{{\textit{#1}}}
\renewcommand{\sc}[1]{{\scshape #1}}

% Default margin
\if@margin
  \setlength{\topmargin}{-0.5in}
  \setlength{\evensidemargin}{-0.5in}
  \setlength{\oddsidemargin}{-0.5in}
  \setlength{\textwidth}{6.0in}
  \setlength{\textheight}{9.0in}
\fi

% We're working on a resume, so don't show date in header if not explicitly specified
\date{}
        """

        with open(output_path, 'w') as f:
            f.write(minimal_res_cls)

        print(f"Created minimal res.cls file at {output_path}")