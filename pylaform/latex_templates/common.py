from pylaform.commands.db.query import Queries
from pylaform.commands.latex import Commands
from pylaform.utilities.commands import contact_flatten, listify, slim, unique
from pylatex import Itemize, NewLine, Section, Subsection, Tabular, Tabularx, Document
from pylatex.utils import bold, italic, NoEscape


class Common:
    """
    Common methods used to generate ports of the resume that are shared between templates.
    :return None: None
    """

    def __init__(self) -> None:
        self.resume_data = Queries()
        self.cmd = Commands()

    def modern_contact_header(self, doc: Document) -> None:
        """
        Print header containing the modern contact information.
        :param Document doc: PyLatex document handler.
        :return None: None
        """

        # Setup values.
        data: dict[str, dict[str, str | bool]] = contact_flatten(self.resume_data.get_identification())
        phone: str = data["phone"]["value"]
        phone_number: str = f"({phone[0:3]}) {phone[3:6]}-{phone[6:10]}"
        
        # Start writing.
        with doc.create(Section(data["name"]["value"] if data["name"]["state"] else "", False)):
            doc.append(self.cmd.vspace("-0.12"))
            with doc.create(Tabularx("X X")) as table1:
                table1.add_hline()
                table1.add_row((
                    self.cmd.hyperlink(
                        data["www"]["value"] if data["www"]["state"] else "",
                        "https://"
                        + data["www"]["value"] if data["www"]["state"] else ""),
                    "",
                ))
            doc.append(self.cmd.vspace("-0.1"))
            doc.append(self.cmd.hspace("-24.0"))
            with doc.create(Tabular("r r r")) as table2:
                table2.add_row(
                    f"{phone_number if data['phone']['state'] else ''}",
                    f"{data['email']['value'] if data['email']['state'] else ''}",
                    f"{data['location']['value'] if data['location']['state'] else ''}")

    def retro_contact_header(self, doc: Document) -> None:
        """
        Print header containing the retro contact information.
        :param Document doc: PyLatex document handler.
        :return None: None
        """

        # Setup values.
        data: dict[str, dict[str, str | bool]] = contact_flatten(self.resume_data.get_identification())
        name: str = data["name"]["value"]
        phone: str = data["phone"]["value"]
        phone_number: str = italic("Phone:  ") + f"({phone[0:3]}) {phone[3:6]}-{phone[6:10]}"
        email: str = italic("E-mail:  ") + self.cmd.hyperlink(
                data["email"]["value"], "mailto:" + data["email"]["value"])
        www: str = italic("WWW: ") + self.cmd.hyperlink(
            data["www"]["value"], "https://" + data["www"]["value"])

        # Start writing.
        doc.append(NoEscape(r"\name{" + f"{name if data['name']['state'] else ''}" + r"}") + self.cmd.vspace("0.1"))
        doc.append(NoEscape(r"\begin{resume}"))
        doc.append(NoEscape(r"\section{\sc Contact Information}"))
        doc.append(self.cmd.vspace(".05"))
        with doc.create(Tabular("l")) as table1:
            table1.add_row([NoEscape(phone_number if data["phone"]["state"] else "")])
            table1.add_row([NoEscape(email if data["email"]["state"] else "")])
            table1.add_row([NoEscape(www if data["www"]["state"] else "")])

    def modern_summary_details(self, doc: Document) -> None:
        """
        Print detailed modern summary.
        :param Document doc: PyLatex document handler.
        :return None: None
        """

        summaries: list[dict[str, str | bool]] = slim(self.resume_data.get_summary())
        
        # Start writing.
        with (doc.create(Section("Summary", False))) as summary_sub:
            for summary in summaries:
                summary_sub.append(NoEscape(r"\begin{itemize}"))
                summary_sub.append(NoEscape(r"\item\textbf{" + summary["shortdesc"] + r":} "
                                            + self.cmd.glossary_inject(summary["longdesc"], "modern")))
                summary_sub.append(NoEscape(r"\end{itemize}"))

    def retro_summary_details(self, doc: Document) -> None:
        """
        Print detailed retro summary.
        :param Document doc: PyLatex document handler.
        :return None: None
        """

        summaries: list[dict[str, str | bool]] = slim(self.resume_data.get_summary())
        
        # Start writing
        doc.append(NoEscape(r"\section{\sc Summary}"))
        for summary in summaries:
            doc.append(NoEscape(
                r"\textbf{" + summary["shortdesc"] + r":} " 
                + self.cmd.glossary_inject(summary["longdesc"], "retro")))
            doc.append(self.cmd.vspace("0.06"))
            doc.append(NewLine())

    def modern_skills(self, doc: Document) -> None:
        """
        Print detailed modern professional_experience.
        :param Document doc: PyLatex document handler.
        :return None: None
        """
        try:
            # Start writing
            with doc.create(Section("Skills", False)):
                # Get the skills data with error handling
                skills_data = self.resume_data.get_skills()
                if not skills_data:
                    # Handle empty skills gracefully
                    doc.append("No skills data available.")
                    return

                categories = slim(skills_data)
                skills = listify(skills_data)

                # Get unique subcategories
                subcategory_list = unique([skill["subcategory"] for skill in skills])
                current_subcategory = ""

                for subcategory in subcategory_list:
                    relevant_skills = [skill for skill in skills if skill["subcategory"] == subcategory]

                    if relevant_skills:
                        category = relevant_skills[0]["category"]  # Get category from first skill in subcategory

                        with doc.create(Subsection(subcategory, False)) as skill_sub:
                            skill_sub.append(NoEscape(r"\begin{itemize*}"))

                            for skill in relevant_skills:
                                # Make sure shortdesc and longdesc exist before trying to use them
                                shortdesc = skill.get("shortdesc", "")
                                longdesc = skill.get("longdesc", "")

                                if shortdesc and longdesc:
                                    skill_sub.append(NoEscape(r"\item") +
                                                     self.cmd.textbox(shortdesc, longdesc))

                            skill_sub.append(NoEscape(r"\end{itemize*}"))
        except Exception as e:
            # Log the error and provide a graceful fallback
            print(f"Error in modern_skills: {e}")
            doc.append("Error loading skills data.")

    def retro_skills(self, doc: Document) -> None:
        """
        Print detailed retro professional_experience.
        :param Document doc: PyLatex document handler.
        :return None: None
        """
        try:
            doc.append(NoEscape(r"\section{\sc Experience}"))

            # Get the skills data with error handling
            skills_data = self.resume_data.get_skills()
            if not skills_data:
                # Handle empty skills gracefully
                doc.append("No experience data available.")
                return

            skills = listify(skills_data)

            # Safely extract categories - handle potential missing keys with .get()
            categories = []
            subcategories = []

            for skill in skills:
                if "category" in skill and skill.get("category") not in categories:
                    categories.append(skill.get("category"))

                if "category" in skill and "subcategory" in skill:
                    sub_entry = {
                        "category": skill.get("category"),
                        "subcategory": skill.get("subcategory")
                    }
                    if sub_entry not in subcategories:
                        subcategories.append(sub_entry)

            # Process each category
            for category in categories:
                doc.append(bold(category))
                doc.append(NewLine())

                # Get subcategories for this category
                category_subcategories = [sub for sub in subcategories if sub.get("category") == category]

                for subcategory in category_subcategories:
                    doc.append(NoEscape(r"{\textit {" + subcategory.get("subcategory", "") + r"}}"))
                    doc.append(NoEscape(r"\begin{list2}"))

                    # Get skills for this subcategory
                    for skill in skills:
                        if (skill.get("category") == category and
                                skill.get("subcategory") == subcategory.get("subcategory")):
                            # Make sure longdesc exists before trying to use it
                            longdesc = skill.get("longdesc", "")
                            if longdesc:
                                doc.append(NoEscape(
                                    r"\item " + self.cmd.glossary_inject(longdesc, "retro")))

                    doc.append(NoEscape(r"\end{list2}"))

        except Exception as e:
            # Log the error and provide a graceful fallback
            print(f"Error in retro_skills: {e}")
            doc.append("Error loading experience data.")

    def retro_work_history(self, doc: Document) -> None:
        """
        Print standard detail work history, however for res.cls.
        :param Document doc: PyLatex document handler.
        :return None: None
        """
        try:
            # Start writing
            doc.append(NoEscape(r"\section{\sc Employment}"))

            # Get data
            achievements_data = self.resume_data.get_achievements()
            positions_data = self.resume_data.get_positions()

            if not achievements_data or not positions_data:
                # Handle empty data gracefully
                doc.append("No employment history available.")
                return

            achievements = listify(achievements_data)
            positions = listify(positions_data)

            # Get unique employers safely - handle potential missing keys
            employers = []
            for ach in achievements:
                if "employer" in ach and ach.get("employer") not in employers and ach.get("employer"):
                    employers.append(ach.get("employer"))

            for employer in employers:
                employer_name = self.resume_data.query_name(employer, "employer")
                doc.append(bold(employer_name))
                doc.append(NewLine())

                # Get positions for this employer
                employer_positions = [pos for pos in positions
                                      if pos.get("employer") == employer]

                for position in employer_positions:
                    position_name = self.resume_data.query_name(position.get("position", ""), "position")

                    # Format dates safely
                    start_date = self.cmd.format_date(position.get("startdate", ""))
                    end_date = "Present" if self.cmd.format_date(
                        position.get("enddate", "")) == "" else self.cmd.format_date(position.get("enddate", ""))

                    doc.append(NoEscape(
                        r"{\em "
                        + position_name
                        + r"} \hfill {"
                        + r"\textbf {"
                        + start_date
                        + r" {--} "
                        + end_date
                        + r"}}"))
                    doc.append(NoEscape(r"\begin{list2}"))

                    # Get achievements for this position
                    position_achievements = [ach for ach in achievements
                                             if ach.get("employer") == employer
                                             and ach.get("position") == position.get("position")]

                    for achievement in position_achievements:
                        longdesc = achievement.get("longdesc", "")
                        if longdesc:
                            doc.append(NoEscape(
                                r"\item " + self.cmd.glossary_inject(longdesc, "retro")))

                    doc.append(NoEscape(r"\end{list2}"))
        except Exception as e:
            # Log the error and provide a graceful fallback
            print(f"Error in retro_work_history: {e}")
            doc.append("Error loading employment history.")

    def modern_work_history(self, doc: Document) -> None:
        """
        Print standard detail work history.
        :param Document doc: PyLatex document handler.
        :return None: None
        """
        try:
            # Start writing.
            with doc.create(Section("Employment", False)):
                # Get achievements and positions data
                achievements_data = self.resume_data.get_achievements()
                if not achievements_data:
                    # Handle empty achievements gracefully
                    doc.append("No employment data available.")
                    return

                # Process achievements to get a list of employers
                achievements = listify(achievements_data)

                # Get unique employers from achievements
                employers = unique([ach.get("employer", "") for ach in achievements if "employer" in ach])

                for employer in employers:
                    if employer:  # Skip empty employer entries
                        employer_name = self.resume_data.query_name(employer, "employer")
                        with doc.create(Subsection(employer_name, False)):
                            # Get positions for this employer
                            positions = [pos for pos in listify(self.resume_data.get_positions())
                                         if pos.get("employer") == employer]

                            for position in positions:
                                position_name = self.resume_data.query_name(position.get("position", ""), "position")
                                with doc.create(Subsection(position_name, False)) as position_sub:
                                    position_sub.append(self.cmd.vspace("-0.25"))

                                    # Format dates
                                    end_date = "Present" if self.cmd.format_date(
                                        position.get("enddate", "")) == "" else self.cmd.format_date(
                                        position.get("enddate", ""))
                                    start_date = self.cmd.format_date(position.get("startdate", ""))

                                    position_sub.append(NoEscape(
                                        r"\hfill{\textbf{"
                                        + f"{start_date} "
                                        + r"{--} "
                                        + end_date
                                        + r"}}"))
                                    position_sub.append(NewLine())

                                    # Get achievements for this employer and position
                                    position_achievements = [ach for ach in achievements
                                                             if ach.get("employer") == employer
                                                             and ach.get("position") == position.get("position")]

                                    for achievement in position_achievements:
                                        if "shortdesc" in achievement:
                                            with doc.create(Itemize()) as itemize:
                                                itemize.add_item(NoEscape(
                                                    self.cmd.glossary_inject(
                                                        achievement["shortdesc"], "modern")))
        except Exception as e:
            # Log the error and provide a graceful fallback
            print(f"Error in modern_work_history: {e}")
            doc.append("Error loading employment data.")

    @staticmethod
    def count_instances(instance_list: list[str | bool], x: any) -> int:
        """
        Count the number of times a list element shows up.
        :param list[str | bool] instance_list:
        :param any x:
        :return int: Match count.
        """

        count_int = 0
        for element in instance_list:
            if element == x:
                count_int = count_int + 1
        return count_int
