from pylaform.commands.latex import Commands
from pylaform.utilities.dbConnector import Queries
from pylatex import Document, Itemize, NewLine, Package, Section, Subsection, Tabular, Tabularx
from pylatex import escape_latex, NoEscape


class Common:
    """
    Common methods used to generate ports of the resume that are shared between templates
    :return: None
    """

    def __init__(self):
        self.resume_data = Queries()
        self.cmd = Commands()

    def contact_header(self, doc):
        """
        Print header containing the contact information
        :return:
        """

        phone = self.resume_data.identification()["phone"]
        with doc.create(Section(self.resume_data.identification()["name"], False)):
            doc.append(self.cmd.vspace("-0.12"))
            with doc.create(Tabularx("X X")) as table1:
                table1.add_hline()
                table1.add_row((
                    self.cmd.hyperlink(
                        "https://"
                        + self.resume_data.identification()["www"],
                        self.resume_data.identification()["www"]),
                    "",
                ))
            doc.append(self.cmd.vspace("-0.1"))
            doc.append(self.cmd.hspace("-24.0"))
            with doc.create(Tabular("r r r")) as table2:
                table2.add_row((
                    f"({phone[0:3]}) {phone[3:6]}-{phone[6:10]}",
                    f"{self.resume_data.identification()['email']}",
                    f"{self.resume_data.identification()['location']}"))

    def summary_details(self, doc):
        """
        Print detailed summary.
        :param object doc: doc handler
        :return: object
        """

        summaries = self.resume_data.summary()
        with (doc.create(Section("Summary", False))) as summary_sub:
            summary_sub.append(NoEscape(r"\begin{itemize}"))
            for summary in summaries:
                summary_sub.append(NoEscape(r"\item\textbf{" + summary["short_desc"] + r":} " + summary["long_desc"]))
            summary_sub.append(NoEscape(r"\end{itemize}"))

    def work_history(self, doc):
        """
        :param object doc: doc handler
        Print standard detail work history.
        :return:
        """

        with (doc.create(Section("Employment", False))):
            companies = self.cmd.unique([sub["employer"] for sub in self.resume_data.achievements()])
            for employer in companies:
                with doc.create(Subsection(employer, False)) as employer_sub:
                    for position in self.resume_data.positions():
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
                                for achievement in self.resume_data.achievements():
                                    if employer == achievement["employer"] and position["position"] == achievement[
                                        "position"]:
                                        with doc.create(Itemize()) as itemize:
                                            itemize.add_item(
                                                NoEscape(self.cmd.glossary_inject(achievement["short_desc"])))
