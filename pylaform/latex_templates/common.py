from pylaform.commands.latex import Commands
from pylaform.utilities.dbCommands import Queries
from pylatex import Document, Itemize, NewLine, Package, Section, Subsection, Tabular, Tabularx
from pylatex.utils import bold, italic, NoEscape
from pylaform.commands.latex import Commands


class Common:
    """
    Common methods used to generate ports of the resume that are shared between templates
    :return: None
    """

    def __init__(self):
        self.resume_data = Queries()
        self.cmd = Commands()

    def modern_contact_header(self, doc):
        """
        Print header containing the modern contact information
        :return:
        """

        phone = self.resume_data.get_identification()["phone"]
        with doc.create(Section(self.resume_data.get_identification()["name"], False)):
            doc.append(self.cmd.vspace("-0.12"))
            with doc.create(Tabularx("X X")) as table1:
                table1.add_hline()
                table1.add_row((
                    self.cmd.hyperlink(
                        self.resume_data.get_identification()["www"],
                        "https://"
                        + self.resume_data.get_identification()["www"]),
                    "",
                ))
            doc.append(self.cmd.vspace("-0.1"))
            doc.append(self.cmd.hspace("-24.0"))
            with doc.create(Tabular("r r r")) as table2:
                table2.add_row((
                    f"({phone[0:3]}) {phone[3:6]}-{phone[6:10]}",
                    f"{self.resume_data.get_identification()['email']}",
                    f"{self.resume_data.get_identification()['location']}"))

    def retro_contact_header(self, doc):
        """
        Print header containing the retro contact information
        :return:
        """
        phone_sub = self.resume_data.get_identification()['phone']
        phone_number = italic("Phone:  ") + f"({phone_sub[0:3]}) {phone_sub[3:6]}-{phone_sub[6:10]}"
        email = italic("E-mail:  ") + self.cmd.hyperlink(
                self.resume_data.get_identification()['email'], "mailto:" + self.resume_data.get_identification()['email'])
        www = italic("WWW: ") + self.cmd.hyperlink(
            self.resume_data.get_identification()['www'], "https://" + self.resume_data.get_identification()['www'])

        # Start Writing
        doc.append(NoEscape(r"\name{" + self.resume_data.get_identification()['name'] + r"}") + self.cmd.vspace("0.1"))

        doc.append(NoEscape(r"\begin{resume}"))
        doc.append(NoEscape(r"\section{\sc Contact Information}"))
        doc.append(self.cmd.vspace(".05"))
        with doc.create(Tabular("l")) as table1:
            table1.add_row([NoEscape(phone_number)])
            table1.add_row([NoEscape(email)])
            table1.add_row([NoEscape(www)])

    def modern_summary_details(self, doc):
        """
        Print detailed modern summary.
        :param object doc: doc handler
        :return: object
        """

        summaries = self.resume_data.get_summary()
        with (doc.create(Section("Summary", False))) as summary_sub:
            summary_sub.append(NoEscape(r"\begin{itemize}"))
            for summary in summaries:
                summary_sub.append(NoEscape(r"\item\textbf{" + summary["short_desc"] + r":} " + self.cmd.glossary_inject(summary["long_desc"], "modern")))
            summary_sub.append(NoEscape(r"\end{itemize}"))

    def retro_summary_details(self, doc):
        """
        Print detailed retro summary.
        :param object doc: doc handler
        :return: object
        """

        summaries = self.resume_data.get_summary()
        doc.append(NoEscape(r"\section{\sc Summary}"))
        for summary in summaries:
            doc.append(NoEscape(
                r"\textbf{" + summary["short_desc"] + r":} " + self.cmd.glossary_inject(summary["long_desc"], "retro")))
            doc.append(NewLine())
        doc.append(NoEscape(r"\end{itemize}"))

    def retro_skills(self, doc):
        """
        Print detailed retro professional_experience.
        :param object doc: doc handler
        :return: object
        """

        doc.append(NoEscape(r"\section{\sc Experience}"))
        categories = self.cmd.unique([sub['category'] for sub in self.resume_data.get_skills()])
        subcategories = self.cmd.unique([{"subcategory": sub['subcategory'], "category": sub['category']} for sub in self.resume_data.get_skills()])
        for category in categories:
            doc.append(bold(category))
            for subcategory in subcategories:
                if category == subcategory['category']:
                    doc.append(NewLine())
                    doc.append(NoEscape(r"{\textit {" + subcategory['subcategory'] + r"}}"))
                    doc.append(NoEscape(r"\begin{list2}"))
                    for skill in self.resume_data.get_skills():
                        if subcategory['subcategory'] == skill['subcategory']:
                            doc.append(NoEscape(r"\item " + self.cmd.glossary_inject(skill['long_desc'], "retro")))
                    doc.append(NoEscape(r"\end{list2}"))

    def work_history(self, doc):
        """
        :param object doc: doc handler
        Print standard detail work history.
        :return:
        """

        with (doc.create(Section("Employment", False))):
            companies = self.cmd.unique([sub["employer"] for sub in self.resume_data.get_achievements()])
            for employer in companies:
                with doc.create(Subsection(employer, False)) as employer_sub:
                    for position in self.resume_data.get_positions():
                        if employer == position["employer"]:
                            with doc.create(Subsection(position["position"], False)) as position_sub:
                                position_sub.append(self.cmd.vspace("-0.25"))
                                position_sub.append(NoEscape(
                                    r"\hfill \textbf{"
                                    + f"{self.cmd.format_date(position['start_date'])} "
                                    + r"{--} "
                                    + f" {self.cmd.format_date(position['end_date'])}"
                                    + r"}"))

                                position_sub.append(NewLine())
                                for achievement in self.resume_data.get_achievements():
                                    if employer == achievement["employer"] and position["position"] == achievement["position"]:
                                        with doc.create(Itemize()) as itemize:
                                            itemize.add_item(NoEscape(
                                                self.cmd.glossary_inject(achievement["short_desc"], "modern")))

    def retro_work_history(self, doc):
        """
        :param object doc: doc handler
        Print standard detail work history, however for res.cls.
        :return:
        """
        doc.append(NoEscape(r"\section{\sc Employment}"))
        companies = self.cmd.unique([sub["employer"] for sub in self.resume_data.get_achievements()])
        for employer in companies:
            doc.append(bold(employer))
            doc.append(NewLine())
            for position in self.resume_data.get_positions():
                if employer == position["employer"]:
                    # doc.append(self.cmd.vspace("-0.16"))
                    doc.append(NoEscape(
                        r"{\em "
                        + position['position']
                        + r"} \hfill {\textbf {"
                        + self.cmd.format_date(position['start_date'])
                        + r" {--} "
                        + self.cmd.format_date(position['end_date'])
                        + r"}}"))
                    # doc.append(NewLine())
                    doc.append(NoEscape(r"\begin{list2}"))
                    for achievement in self.resume_data.get_achievements():
                        if employer == achievement["employer"] and position["position"] == achievement["position"]:
                            doc.append(NoEscape(r"\item " + self.cmd.glossary_inject(achievement['long_desc'], "retro")))
                    doc.append(NoEscape(r"\end{list2}"))
