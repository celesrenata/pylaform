from pylaform.commands.db.query import Queries
from pylaform.commands.latex import Commands
from pylatex import Command, Document, Package
from pylatex.utils import NoEscape
from tenacity import retry, stop_after_delay
from .common import Common
import os
import shutil
import subprocess


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
        self.generate()

    @retry(stop=(stop_after_delay(10)))
    def generate(self) -> None:
        """
        Generate PDF using pdflatex with local res.cls file.
        :return None: None
        """
        try:
            # Generate the LaTeX file
            self.doc.generate_tex("data/hybrid")

            # Add \let\nofiles\relax at the beginning
            norelax = r"\let\nofiles\relax"
            with open("data/hybrid.tex", 'r+') as f:
                content = f.read()
                f.seek(0, 0)
                f.write(norelax.rstrip('\r\n') + '\n' + content)

            # Ensure data directory exists
            data_dir = os.path.abspath("data")
            os.makedirs(data_dir, exist_ok=True)

            # Copy res.cls to the data directory
            project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
            resources_dir = os.path.join(project_root, "resources")
            res_cls_path = os.path.join(resources_dir, "res.cls")

            # Check if res.cls exists in resources directory
            if os.path.exists(res_cls_path):
                print(f"Found res.cls at {res_cls_path}")
                shutil.copy(res_cls_path, os.path.join(data_dir, "res.cls"))
                print(f"Copied res.cls to {data_dir}")
            else:
                # Try to find res.cls in other possible locations
                print(f"res.cls not found in {res_cls_path}, searching in other locations...")

                # Look in current directory and parent directories
                found = False
                current_dir = os.path.abspath(os.path.dirname(__file__))
                for _ in range(5):  # Look up to 5 levels up
                    for search_dir in [
                        os.path.join(current_dir, "resources"),
                        current_dir
                    ]:
                        search_path = os.path.join(search_dir, "res.cls")
                        if os.path.exists(search_path):
                            print(f"Found res.cls in {search_path}")
                            shutil.copy(search_path, os.path.join(data_dir, "res.cls"))
                            print(f"Copied res.cls to {data_dir}")
                            found = True
                            break

                    if found:
                        break

                    current_dir = os.path.dirname(current_dir)

                if not found:
                    print("Warning: res.cls not found in any common location")
                    # Try to create a minimal res.cls based on common templates
                    self._create_minimal_res_cls(os.path.join(data_dir, "res.cls"))

            # Run pdflatex with TEXINPUTS to include current directory
            env = os.environ.copy()
            env['TEXINPUTS'] = f".:{data_dir}::"  # Add data dir to TEXINPUTS path

            print(f"Running pdflatex with TEXINPUTS={env['TEXINPUTS']}")
            cmd = ["pdflatex", "-interaction=nonstopmode", "-output-directory", data_dir, f"{data_dir}/hybrid.tex"]

            try:
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"Error running pdflatex (code {result.returncode}):")
                    print(result.stderr)
                    # Try direct command as fallback
                    fallback_cmd = f"TEXINPUTS=.:{data_dir}:: pdflatex -interaction=nonstopmode -output-directory {data_dir} {data_dir}/hybrid.tex"
                    print(f"Trying fallback: {fallback_cmd}")
                    os.system(fallback_cmd)
                else:
                    print("PDF generation successful")
            except Exception as e:
                print(f"Error running subprocess: {e}")
                # Fallback to os.system
                os.system(
                    f"TEXINPUTS=.:{data_dir}:: pdflatex -interaction=nonstopmode -output-directory {data_dir} {data_dir}/hybrid.tex")

        except Exception as e:
            print(f"Error in generate: {e}")
            # Last resort fallback
            os.system("pdflatex -output-directory data/ data/hybrid.tex")

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