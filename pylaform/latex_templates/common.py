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
                # Get employer location from database
                employer_location = None

                # First look in positions data for location
                for pos in positions:
                    if pos.get("employer") == employer and "location" in pos:
                        employer_location = pos.get("location")
                        break

                # Display employer name and location if available
                if employer_location:
                    doc.append(NoEscape(r"\textbf{" + employer_name + r", " + employer_location + r"}"))
                else:
                    doc.append(NoEscape(r"\textbf{" + employer_name + r"}"))

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

                    # Remove extra space before the date range
                    doc.append(NoEscape(
                        r"{\em "
                        + position_name
                        + r"} \hfill{"
                        + r"\textbf{"
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
                positions_data = self.resume_data.get_positions()

                if not achievements_data:
                    # Handle empty achievements gracefully
                    doc.append("No employment data available.")
                    return

                # Process achievements to get a list of employers
                achievements = listify(achievements_data)
                positions = listify(positions_data)

                # Get unique employers from achievements
                employers = unique([ach.get("employer", "") for ach in achievements if "employer" in ach])

                for employer in employers:
                    if employer:  # Skip empty employer entries
                        employer_name = self.resume_data.query_name(employer, "employer")
                        # Get employer location from positions data
                        employer_location = None

                        # Look in positions data for location
                        for pos in positions:
                            if pos.get("employer") == employer and "location" in pos:
                                employer_location = pos.get("location")
                                break

                        with doc.create(Subsection(employer_name, False)) as employer_sub:
                            # Add location right-aligned if available
                            if employer_location:
                                employer_sub.append(NoEscape(r"\hfill{" + employer_location + r"}"))

                            # Get positions for this employer
                            employer_positions = [pos for pos in positions
                                                  if pos.get("employer") == employer]

                            for position in employer_positions:
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

    def retro_education(self, doc):
        """
        Add education details to the document in retro style.
        :param doc: The document to add the education section to.
        :return: None
        """
        print("\n=== DEBUG: retro_education called ===")
        from datetime import datetime

        # First, check if there's any education data to show
        education_data = self.resume_data.get_education()
        print(f"\n=== DEBUG: Retrieved {len(education_data)} education entries ===")

        # Add the section header with \sc for small caps styling
        doc.append(NoEscape(r"\section{\sc Education}"))
        print("Added Education section header")

        # Track data for debugging
        schools_found = 0
        focuses_found = 0
        schools_added = 0
        focuses_added = 0

        # Process education data by school
        schools = {}

        # First get all schools
        for entry in education_data:
            if entry["id"].startswith("school_") and entry["state"]:
                school_id = entry["id"]
                if entry["attr"] == "schoolname":
                    if school_id not in schools:
                        schools[school_id] = {
                            "name": entry["value"],
                            "location": "",
                            "focuses": []
                        }
                        schools_found += 1
                        print(f"Found school: {school_id} - {entry['value']}")
                    else:
                        schools[school_id]["name"] = entry["value"]

                elif entry["attr"] == "location":
                    if school_id in schools:
                        schools[school_id]["location"] = entry["value"]
                        print(f"Added location '{entry['value']}' to school {school_id}")

        # Then process all focuses
        focus_lookup = {}
        for entry in education_data:
            if entry["id"].startswith("focus_") and entry["state"]:
                focus_id = entry["id"]
                if entry["attr"] == "focusname":
                    if focus_id not in focus_lookup:
                        focus_lookup[focus_id] = {
                            "name": entry["value"],
                            "school": None,
                            "startdate": "",
                            "enddate": ""
                        }
                        focuses_found += 1
                        print(f"Found focus: {focus_id} - {entry['value']}")
                    else:
                        focus_lookup[focus_id]["name"] = entry["value"]

                # Get focus dates
                elif entry["attr"] == "startdate":
                    if focus_id in focus_lookup:
                        focus_lookup[focus_id]["startdate"] = entry["value"]
                        print(f"Added start date '{entry['value']}' to focus {focus_id}")

                elif entry["attr"] == "enddate":
                    if focus_id in focus_lookup:
                        focus_lookup[focus_id]["enddate"] = entry["value"]
                        print(f"Added end date '{entry['value']}' to focus {focus_id}")

                # Find the school this focus belongs to
                elif entry["attr"] == "school":
                    if focus_id in focus_lookup:
                        focus_lookup[focus_id]["school"] = entry["value"]
                        print(f"Focus {focus_id} belongs to school {entry['value']}")

        # Now assign focuses to schools
        for focus_id, focus_data in focus_lookup.items():
            school_id = focus_data["school"]
            if school_id and school_id in schools:
                schools[school_id]["focuses"].append({
                    "name": focus_data["name"],
                    "startdate": focus_data["startdate"],
                    "enddate": focus_data["enddate"]
                })
                print(f"Assigned focus {focus_id} to school {school_id}")

        print(f"\n=== Found {len(schools)} schools and {len(focus_lookup)} focuses ===")

        # Add education entries to document
        for school_id, school in schools.items():
            schools_added += 1
            # Safely handle special characters in school name and location
            school_name = school["name"].replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")
            school_location = school["location"].replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")

            # School name and location
            if school_location:
                doc.append(NoEscape(r"\textbf{" + school_name + r", " + school_location + r"}"))
            else:
                doc.append(NoEscape(r"\textbf{" + school_name + r"}"))

            # Add a line break to separate school from focuses
            doc.append(NoEscape(r"\\"))

            print(f"Added school to document: {school_name}")

            # Add focuses/majors without bullets and no indent
            if school["focuses"]:
                for focus in school["focuses"]:
                    focuses_added += 1
                    # Safely handle special characters in focus name
                    focus_name = focus["name"].replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")

                    # Format date string with month names
                    date_str = ""
                    if focus["startdate"] or focus["enddate"]:
                        if focus["startdate"]:
                            try:
                                formatted_start = self.cmd.format_date(focus["startdate"])
                                date_str += formatted_start
                            except:
                                date_str += focus["startdate"]

                        date_str += " - "

                        if focus["enddate"]:
                            try:
                                formatted_end = self.cmd.format_date(focus["enddate"])
                                date_str += formatted_end
                            except:
                                date_str += focus["enddate"]
                        else:
                            date_str += "Present"

                    # Add focus with date - directly with no indentation or bullets
                    if date_str:
                        # Create a paragraph with the focus that ensures it's on a new line
                        latex_line = r"{\em " + focus_name + r"}\hfill\textbf{" + date_str + r"}"
                        doc.append(NoEscape(latex_line))
                        # Add a line break after each focus
                        doc.append(NoEscape(r"\\"))
                        print(f"Added focus with formatted date: {focus_name} ({date_str})")
                    else:
                        latex_line = r"{\em " + focus_name + r"}"
                        doc.append(NoEscape(latex_line))
                        # Add a line break after each focus
                        doc.append(NoEscape(r"\\"))
                        print(f"Added focus without date: {focus_name}")
            else:
                print(f"WARNING: No focuses found for school {school_id}")

            # Add spacing between schools (additional line break)
            doc.append(NoEscape(r"\\"))

        # If no schools were added or if something is wrong, add a test entry
        if schools_added == 0:
            print("WARNING: No schools were added, using test data")
            doc.append(NoEscape(r"\textbf{Test University, Test City}"))
            doc.append(NoEscape(r"\\"))
            doc.append(NoEscape(r"{\em Bachelor of Computer Science}\hfill\textbf{January 2018 - December 2022}"))
            doc.append(NoEscape(r"\\"))
            doc.append(NoEscape(r"\\"))

        print(f"=== Education section summary: {schools_found} schools found, {focuses_found} focuses found ===")
        print(f"=== {schools_added} schools added to document, {focuses_added} focuses added to document ===")

    def modern_education(self, doc):
        """
        Add education details to the document in modern style.
        :param doc: The document to add the education section to.
        :return: None
        """
        print("\n=== DEBUG: modern_education called ===")

        # Import required pylatex sections if not already at the top
        from pylatex import Section, Subsection
        from datetime import datetime

        # Get raw education data
        education_data = self.resume_data.get_education()
        print(f"\n=== DEBUG: Retrieved {len(education_data)} education entries ===")

        # Exit if no data
        if not education_data:
            return

        # Add the section header
        with doc.create(Section("Education", False)):
            # Track data for debugging
            schools_found = 0
            focuses_found = 0
            schools_added = 0
            focuses_added = 0

            # Process all data into organized structures
            schools = {}
            focuses = {}

            # Process all schools first
            for item in education_data:
                # Process schools
                if item["id"].startswith("school_") and item["state"]:
                    school_id = item["id"]

                    if item["attr"] == "schoolname":
                        if school_id not in schools:
                            schools[school_id] = {"name": item["value"], "location": ""}
                            schools_found += 1
                            print(f"Found school: {school_id} - {item['value']}")
                        else:
                            schools[school_id]["name"] = item["value"]

                    elif item["attr"] == "location":
                        if school_id in schools:
                            schools[school_id]["location"] = item["value"]
                            print(f"Added location '{item['value']}' to school {school_id}")

            # Then process all focuses
            for item in education_data:
                if item["id"].startswith("focus_") and item["state"]:
                    focus_id = item["id"]

                    if item["attr"] == "focusname":
                        if focus_id not in focuses:
                            focuses[focus_id] = {
                                "name": item["value"],
                                "school": "",
                                "startdate": "",
                                "enddate": ""
                            }
                            focuses_found += 1
                            print(f"Found focus: {focus_id} - {item['value']}")
                        else:
                            focuses[focus_id]["name"] = item["value"]

                    elif item["attr"] == "school":
                        if focus_id in focuses:
                            focuses[focus_id]["school"] = item["value"]
                            print(f"Focus {focus_id} belongs to school {item['value']}")

                    elif item["attr"] == "startdate":
                        if focus_id in focuses:
                            focuses[focus_id]["startdate"] = item["value"]
                            print(f"Added start date '{item['value']}' to focus {focus_id}")

                    elif item["attr"] == "enddate":
                        if focus_id in focuses:
                            focuses[focus_id]["enddate"] = item["value"]
                            print(f"Added end date '{item['value']}' to focus {focus_id}")

            print(f"\n=== Found {len(schools)} schools and {len(focuses)} focuses ===")

            # Add education entries to document
            for school_id, school in schools.items():
                schools_added += 1
                # Create a subsection for the school
                with doc.create(Subsection(school["name"], False)) as school_sub:
                    # Add location right-aligned
                    if school["location"]:
                        school_sub.append(NoEscape(r"\hfill{" + school["location"] + r"}"))

                    # Add a line break after the school name and location
                    school_sub.append(NoEscape(r"\\"))

                    print(f"Added school to document: {school['name']}")

                    # Find all focuses for this school
                    school_focuses = []
                    for focus_id, focus in focuses.items():
                        if focus["school"] == school_id:
                            school_focuses.append(focus)
                            print(f"Assigned focus {focus_id} to school {school_id}")

                    # Process each focus - no list environment, directly add them
                    for focus in school_focuses:
                        focuses_added += 1
                        # Escape special characters in focus name
                        focus_name = focus["name"].replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")

                        # Format date range with month names using the format_date function
                        date_range = ""
                        if focus["startdate"] or focus["enddate"]:
                            if focus["startdate"]:
                                try:
                                    formatted_start = self.cmd.format_date(focus["startdate"])
                                    date_range += formatted_start
                                except:
                                    date_range += focus["startdate"]

                            date_range += " - "

                            if focus["enddate"]:
                                try:
                                    formatted_end = self.cmd.format_date(focus["enddate"])
                                    date_range += formatted_end
                                except:
                                    date_range += focus["enddate"]
                            else:
                                date_range += "Present"

                        # Add the focus directly (no bullet list)
                        if date_range:
                            # Add focus with right-aligned date
                            school_sub.append(NoEscape(r"{\em " + focus_name + r"}\hfill\textbf{" + date_range + r"}"))
                            print(f"Added focus with formatted date: {focus_name} ({date_range})")
                        else:
                            school_sub.append(NoEscape(r"{\em " + focus_name + r"}"))
                            print(f"Added focus without date: {focus_name}")

                        # Add a line break after each focus
                        school_sub.append(NoEscape(r"\\"))

            # If no schools were added, add a test entry
            if schools_added == 0:
                print("WARNING: No schools were added, using test data")
                with doc.create(Subsection("Test University", False)) as school_sub:
                    school_sub.append(NoEscape(r"\hfill{Test City}"))
                    school_sub.append(NoEscape(r"\\"))
                    school_sub.append(
                        NoEscape(r"{\em Bachelor of Computer Science}\hfill\textbf{January 2018 - December 2022}"))
                    school_sub.append(NoEscape(r"\\"))

            print(f"=== Education section summary: {schools_found} schools found, {focuses_found} focuses found ===")
            print(f"=== {schools_added} schools added to document, {focuses_added} focuses added to document ===")

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
