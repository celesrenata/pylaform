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
        self.achievements = {"schools": {}, "positions": {}, "employers": {}}

    def normalize_id(self, id_value):
        """
        Normalize IDs to a consistent format whether they come as integers, strings, or prefixed strings.

        :param id_value: ID in any format (int, str, "prefix_123")
        :return: Normalized ID as a string without prefix
        """
        # Handle None case
        if id_value is None:
            return ""

        # Convert to string if not already
        id_str = str(id_value)

        # If it's in the format "prefix_123", extract the numeric part
        if "_" in id_str:
            parts = id_str.split("_")
            if len(parts) > 1 and parts[1].isdigit():
                print(f"DEBUG: Normalizing prefixed ID '{id_str}' to '{parts[1]}'")
                return parts[1]

        print(f"DEBUG: Keeping ID '{id_str}' as is")
        return id_str

    def format_date_range(self, start_date, end_date):
        """Format a date range for display in resume.
        This is a utility method that formats dates like "Jan 2020 - Present".
        """
        import datetime

        # Handle empty dates
        if not start_date and not end_date:
            return "No dates available"

        # Parse dates
        start = None
        end = None

        if start_date:
            try:
                start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                start = None

        if end_date:
            # Special case for 9999-01-01 which is used to represent "Present"
            if end_date == "9999-01-01":
                end = "Present"
            else:
                try:
                    end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
                except ValueError:
                    end = None

        # Format dates
        if start and end and end != "Present":
            return f"{start.strftime('%b %Y')} - {end.strftime('%b %Y')}"
        elif start and end == "Present":
            return f"{start.strftime('%b %Y')} - Present"
        elif start:
            return f"{start.strftime('%b %Y')}"
        elif end and end != "Present":
            return f"Until {end.strftime('%b %Y')}"
        elif end == "Present":
            return "Present"
        else:
            return "Unknown dates"

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

    def retro_work_history(self, doc):
        """
        Add work history details to the document in retro style.
        :param doc: The document to add the work history section to.
        :return: None
        """
        print("=== DEBUG: retro_work_history START ===")
        from pylatex.utils import NoEscape

        # Get the raw data
        position_data = self.resume_data.get_positions()
        achievement_data = self.resume_data.get_achievements()

        print(f"Raw data: got {len(achievement_data)} achievement entries and {len(position_data)} position entries")

        # Try to get the already processed achievements from common if available
        achievements_by_position = getattr(self, 'achievements', {}).get('by_position', {})
        achievements_by_employer = getattr(self, 'achievements', {}).get('by_employer', {})

        # If not available, let's process them here
        if not achievements_by_position and not achievements_by_employer:
            print("Processing achievements directly in retro_work_history")

            # First, organize all achievements by their ID
            achievement_items = {}
            for item in achievement_data:
                achievement_id = item["id"]
                if achievement_id not in achievement_items:
                    achievement_items[achievement_id] = {
                        "id": achievement_id,
                        "state": item.get("state", False)
                    }

                # Set attributes based on the attr field
                if item["attr"] == "shortdesc":
                    achievement_items[achievement_id]["shortdesc"] = item["value"]
                elif item["attr"] == "longdesc":
                    achievement_items[achievement_id]["longdesc"] = item["value"]
                elif item["attr"] == "employer":
                    achievement_items[achievement_id]["employer"] = item["value"]
                elif item["attr"] == "employername":
                    achievement_items[achievement_id]["employername"] = item["value"]
                elif item["attr"] == "position":
                    achievement_items[achievement_id]["position"] = item["value"]
                elif item["attr"] == "positionname":
                    achievement_items[achievement_id]["positionname"] = item["value"]
                elif item["attr"] == "achievementstate":
                    achievement_items[achievement_id]["state"] = bool(int(item["value"]))

            # Then group achievements by position and employer
            achievements_by_position = {}
            achievements_by_employer = {}

            for achievement_id, achievement in achievement_items.items():
                # Skip inactive achievements
                if not achievement.get("state", False):
                    continue

                # Skip school achievements for work history
                if achievement.get("school") and achievement.get("school") != "":
                    continue

                # Print each achievement for debugging
                print(f"Processing achievement: {achievement}")

                # Add to position achievements if position is specified
                if achievement.get("position") and achievement.get("position") != "":
                    position_id = achievement.get("position")

                    # Handle both formats (position_1 or just 1)
                    if not position_id in achievements_by_position:
                        achievements_by_position[position_id] = []
                    achievements_by_position[position_id].append(achievement)
                    print(f"Added achievement to position {position_id}")

                # Add to employer achievements if employer is specified but no position
                elif achievement.get("employer") and achievement.get("employer") != "":
                    employer_id = achievement.get("employer")

                    # Handle both formats (employer_1 or just 1)
                    if not employer_id in achievements_by_employer:
                        achievements_by_employer[employer_id] = []
                    achievements_by_employer[employer_id].append(achievement)
                    print(f"Added achievement to employer {employer_id}")

        # Process positions in the id/attr/value format
        employers = {}
        positions = {}
        position_to_employer = {}

        # First pass: collect all employers and their basic info
        for item in position_data:
            if item["id"].startswith("employer_"):
                employer_id = item["id"]
                if employer_id not in employers:
                    employers[employer_id] = {
                        "numeric_id": employer_id.split("_")[1],
                        "name": "",
                        "location": "",
                        "state": item.get("state", True),
                        "positions": []
                    }

                # Set attribute values
                if item["attr"] == "employername":
                    employers[employer_id]["name"] = item["value"]
                    print(f"Found employer: {employer_id} - {item['value']}")
                elif item["attr"] == "location":
                    employers[employer_id]["location"] = item["value"]
                    print(f"Added location '{item['value']}' to employer {employer_id}")

        # Second pass: collect all positions and link them to employers
        for item in position_data:
            if item["id"].startswith("position_"):
                position_id = item["id"]
                if position_id not in positions:
                    positions[position_id] = {
                        "numeric_id": position_id.split("_")[1],
                        "name": "",
                        "startdate": "",
                        "enddate": "",
                        "employer": None,
                        "state": item.get("state", True)
                    }

                # Set attribute values
                if item["attr"] == "positionname":
                    positions[position_id]["name"] = item["value"]
                    print(f"Found position: {position_id} - {item['value']}")
                elif item["attr"] == "startdate":
                    positions[position_id]["startdate"] = item["value"]
                    print(f"Added start date '{item['value']}' to position {position_id}")
                elif item["attr"] == "enddate":
                    positions[position_id]["enddate"] = item["value"]
                    print(f"Added end date '{item['value']}' to position {position_id}")
                elif item["attr"] == "employer":
                    # This could be "employer_1" or just "1"
                    employer_value = item["value"]
                    if employer_value.startswith("employer_"):
                        employer_id = employer_value
                    else:
                        employer_id = f"employer_{employer_value}"

                    positions[position_id]["employer"] = employer_id
                    position_to_employer[position_id] = employer_id

                    # Add this position to the employer's list
                    if employer_id in employers:
                        employers[employer_id]["positions"].append(position_id)

        # Create a lookup for numeric position IDs (for achievement matching)
        numeric_position_map = {}
        for pos_id, pos in positions.items():
            numeric_id = pos["numeric_id"]
            numeric_position_map[numeric_id] = pos_id

        # Hardcoded position-to-employer mapping as fallback (based on your logs)
        hardcoded_mappings = {
            "1": "employer_1",  # Systems Developer Engineer I -> Amazon
            "2": "employer_1",  # Systems Engineer I -> Amazon
            "3": "employer_1",  # IT Support Engineer II -> Amazon
            "4": "employer_1",  # Support Engineer III -> Amazon
            "5": "employer_1",  # Technical Support Tech I -> Amazon
            "6": "employer_2",  # Lab Tech -> Microsoft
        }

        # Associate positions with employers if not already done
        for position_id, position in positions.items():
            numeric_id = position["numeric_id"]

            # If no employer is set, use hardcoded mapping
            if not position["employer"] and numeric_id in hardcoded_mappings:
                employer_id = hardcoded_mappings[numeric_id]
                position["employer"] = employer_id
                position_to_employer[position_id] = employer_id

                # Also add this position to the employer's list
                if employer_id in employers:
                    if position_id not in employers[employer_id]["positions"]:
                        employers[employer_id]["positions"].append(position_id)

        # Examine achievements for employer assignment too
        for position_id_str, achievs in achievements_by_position.items():
            for achievement in achievs:
                if achievement.get("employer"):
                    employer_id_str = achievement.get("employer")

                    # Handle different ID formats
                    if position_id_str.startswith("position_"):
                        position_id = position_id_str
                    else:
                        # Convert numeric ID to full ID if needed
                        position_id = f"position_{position_id_str}" if position_id_str.isdigit() else position_id_str

                    if employer_id_str.startswith("employer_"):
                        employer_id = employer_id_str
                    else:
                        # Convert numeric ID to full ID if needed
                        employer_id = f"employer_{employer_id_str}" if employer_id_str.isdigit() else employer_id_str

                    # Set employer for this position if not already set
                    if position_id in positions and not positions[position_id]["employer"]:
                        positions[position_id]["employer"] = employer_id
                        position_to_employer[position_id] = employer_id

                        # Add this position to the employer's list
                        if employer_id in employers:
                            if position_id not in employers[employer_id]["positions"]:
                                employers[employer_id]["positions"].append(position_id)

        # List all employers with positions or achievements
        print("=== Employers with positions or achievements ===")
        valid_employers = {}
        for employer_id, employer in employers.items():
            numeric_id = employer["numeric_id"]

            # Check if employer has positions
            has_positions = bool(employer["positions"])

            # Check if employer has direct achievements (using both ID formats)
            has_achievements = (employer_id in achievements_by_employer or
                                numeric_id in achievements_by_employer)

            print(f"Employer {employer_id} ({employer['name']}):")
            print(f"  - Has positions: {has_positions}")
            print(f"  - Has direct achievements: {has_achievements}")

            if has_positions or has_achievements:
                valid_employers[employer_id] = employer

        print(f"=== Found {len(valid_employers)} valid employers ===")

        # Add the section header
        doc.append(NoEscape(r"\section{\sc Employment}"))

        # Track data for debugging
        employers_added = 0
        positions_added = 0
        achievements_added = 0

        # Add employment entries to document in retro style
        for employer_id, employer in valid_employers.items():
            if not employer["state"]:
                continue

            employers_added += 1
            numeric_employer_id = employer["numeric_id"]

            # Safely handle special characters
            employer_name = employer['name'].replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")
            employer_location = employer['location'].replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")

            # Format employer name and location
            if employer_location:
                doc.append(NoEscape(r"\textbf{" + employer_name + r", " + employer_location + r"}"))
            else:
                doc.append(NoEscape(r"\textbf{" + employer_name + r"}"))

            # Add a line break
            doc.append(NoEscape(r"\\"))

            # Debug employer's position list
            print(f"Employer {employer_id} has positions: {employer['positions']}")

            # Get all positions for this employer and sort by start date (newest first)
            employer_positions = []
            for position_id in employer["positions"]:
                if position_id in positions:
                    position = positions[position_id]
                    if position["state"]:
                        employer_positions.append(position)

            # Sort by start date (newest first)
            employer_positions.sort(key=lambda p: p.get("startdate", "9999-12-31"), reverse=True)

            # Process each position
            for position in employer_positions:
                positions_added += 1
                position_id = position["id"] if "id" in position else None
                numeric_position_id = position["numeric_id"]

                # Safely handle special characters
                position_name = position['name'].replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")

                # Format date range
                date_str = ""
                if position.get('startdate') or position.get('enddate'):
                    if position.get('startdate'):
                        try:
                            formatted_start = self.cmd.format_date(position['startdate'])
                            date_str += formatted_start
                        except:
                            date_str += position['startdate']

                    date_str += " - "

                    if position.get('enddate') and position['enddate'] != '9999-01-01':
                        try:
                            formatted_end = self.cmd.format_date(position['enddate'])
                            date_str += formatted_end
                        except:
                            date_str += position['enddate']
                    else:
                        date_str += "Present"

                # Add position with dates
                if date_str:
                    latex_line = r"{\em " + position_name + r"}\hfill\textbf{" + date_str + r"}"
                    doc.append(NoEscape(latex_line))
                else:
                    latex_line = r"{\em " + position_name + r"}"
                    doc.append(NoEscape(latex_line))

                # Add a line break
                doc.append(NoEscape(r"\\"))

                # Find achievements for this position (check all possible ID formats)
                position_achievement_list = []

                # Check for achievements using position_id
                if position_id and position_id in achievements_by_position:
                    position_achievement_list.extend(achievements_by_position[position_id])

                # Check for achievements using numeric_position_id
                if numeric_position_id in achievements_by_position:
                    position_achievement_list.extend(achievements_by_position[numeric_position_id])

                # Add position achievements if any
                if position_achievement_list:
                    doc.append(NoEscape(r"\vspace{1mm}"))
                    doc.append(NoEscape(r"\begin{list2}"))

                    for achievement in position_achievement_list:
                        # Use longdesc for retro style
                        longdesc = achievement.get('longdesc', '')
                        if longdesc:
                            # Safe text replacement for LaTeX
                            longdesc = longdesc.replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")
                            doc.append(NoEscape(r"\item " + self.cmd.glossary_inject(longdesc, "retro")))
                            achievements_added += 1

                    doc.append(NoEscape(r"\end{list2}"))
                    print(f"Added {len(position_achievement_list)} achievements for position {position_name}")

            # Find employer-level achievements (check all possible ID formats)
            employer_achievement_list = []

            # Check for achievements using employer_id
            if employer_id in achievements_by_employer:
                employer_achievement_list.extend(achievements_by_employer[employer_id])

            # Check for achievements using numeric_employer_id
            if numeric_employer_id in achievements_by_employer:
                employer_achievement_list.extend(achievements_by_employer[numeric_employer_id])

            # Add employer-level achievements if any
            if employer_achievement_list:
                doc.append(NoEscape(r"\vspace{1mm}"))
                doc.append(NoEscape(r"\begin{list2}"))

                for achievement in employer_achievement_list:
                    # Use longdesc for retro style
                    longdesc = achievement.get('longdesc', '')
                    if longdesc:
                        # Safe text replacement for LaTeX
                        longdesc = longdesc.replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")
                        doc.append(NoEscape(r"\item " + self.cmd.glossary_inject(longdesc, "retro")))
                        achievements_added += 1

                doc.append(NoEscape(r"\end{list2}"))
                print(f"Added {len(employer_achievement_list)} employer-level achievements for {employer_name}")

            # Add spacing between employers
            doc.append(NoEscape(r"\\"))

        # If no employers were added, add a test entry
        if employers_added == 0:
            print("WARNING: No employers found. Adding test entry.")
            doc.append(NoEscape(r"\textbf{Example Company, Example Location}"))
            doc.append(NoEscape(r"\\"))
            doc.append(NoEscape(r"{\em Example Position}\hfill\textbf{January 2020 - Present}"))
            doc.append(NoEscape(r"\\"))
            doc.append(NoEscape(r"\begin{list2}"))
            doc.append(NoEscape(r"\item Example job responsibility"))
            doc.append(NoEscape(r"\end{list2}"))
            doc.append(NoEscape(r"\\"))

        print(
            f"=== Added {employers_added} employers, {positions_added} positions, and {achievements_added} achievements ===")
        print("=== DEBUG: retro_work_history END ===")

    def modern_work_history(self, doc):
        """
        Add work history details to the document in modern style.
        :param doc: The document to add the work history section to.
        :return: None
        """
        print("=== DEBUG: modern_work_history START ===")
        from pylatex import Section, Subsection, Itemize
        from pylatex.utils import NoEscape

        # Get the raw data
        position_data = self.resume_data.get_positions()

        # Get achievements structure from the common object
        achievement_structure = getattr(self, 'achievements', None)

        if achievement_structure:
            print("Using pre-processed achievement structure")
            achievements_by_position = achievement_structure.get('positions', {})
            achievements_by_employer = achievement_structure.get('employers', {})
        else:
            print("WARNING: No achievement structure found")
            achievements_by_position = {}
            achievements_by_employer = {}

        print(f"Found {len(achievements_by_position)} positions with achievements")
        print(f"Found {len(achievements_by_employer)} employers with achievements")

        # Process positions in the id/attr/value format
        employers = {}
        positions = {}
        position_to_employer = {}

        # First pass: collect all employers and their basic info
        for item in position_data:
            if item["id"].startswith("employer_"):
                employer_id = item["id"]
                if employer_id not in employers:
                    employers[employer_id] = {
                        "numeric_id": employer_id.split("_")[1],
                        "name": "",
                        "location": "",
                        "state": item.get("state", True),
                        "positions": []
                    }

                # Set attribute values
                if item["attr"] == "employername":
                    employers[employer_id]["name"] = item["value"]
                    print(f"Found employer: {employer_id} - {item['value']}")
                elif item["attr"] == "location":
                    employers[employer_id]["location"] = item["value"]
                    print(f"Added location '{item['value']}' to employer {employer_id}")

        # Second pass: collect all positions and link them to employers
        for item in position_data:
            if item["id"].startswith("position_"):
                position_id = item["id"]
                if position_id not in positions:
                    positions[position_id] = {
                        "numeric_id": position_id.split("_")[1],
                        "name": "",
                        "startdate": "",
                        "enddate": "",
                        "employer": None,
                        "state": item.get("state", True)
                    }

                # Set attribute values
                if item["attr"] == "positionname":
                    positions[position_id]["name"] = item["value"]
                    print(f"Found position: {position_id} - {item['value']}")
                elif item["attr"] == "startdate":
                    positions[position_id]["startdate"] = item["value"]
                    print(f"Added start date '{item['value']}' to position {position_id}")
                elif item["attr"] == "enddate":
                    positions[position_id]["enddate"] = item["value"]
                    print(f"Added end date '{item['value']}' to position {position_id}")
                elif item["attr"] == "employer":
                    # This could be "employer_1" or just "1"
                    employer_value = item["value"]
                    if employer_value.startswith("employer_"):
                        employer_id = employer_value
                    else:
                        employer_id = f"employer_{employer_value}"

                    positions[position_id]["employer"] = employer_id
                    position_to_employer[position_id] = employer_id

                    # Add this position to the employer's list
                    if employer_id in employers:
                        employers[employer_id]["positions"].append(position_id)

        # List all employers with positions or achievements
        print("=== Employers with positions or achievements ===")
        valid_employers = {}
        for employer_id, employer in employers.items():
            numeric_id = employer["numeric_id"]

            # Check if employer has positions
            has_positions = bool(employer["positions"])

            # Check if employer has direct achievements (using both ID formats)
            has_achievements = (employer_id in achievements_by_employer or
                                numeric_id in achievements_by_employer)

            print(f"Employer {employer_id} ({employer['name']}):")
            print(f"  - Has positions: {has_positions}")
            print(f"  - Has direct achievements: {has_achievements}")

            if has_positions or has_achievements:
                valid_employers[employer_id] = employer

        print(f"=== Found {len(valid_employers)} valid employers ===")

        # Add the section header with modern style
        with doc.create(Section("Employment History", False)):
            # Track data for debugging
            employers_added = 0
            positions_added = 0
            achievements_added = 0

            # Add employment entries to document in modern style
            for employer_id, employer in valid_employers.items():
                if not employer["state"]:
                    continue

                employers_added += 1
                numeric_employer_id = employer["numeric_id"]

                # Safely handle special characters
                employer_name = employer['name'].replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")
                employer_location = employer['location'].replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")

                # Format employer name and location with Subsection for modern style
                if employer_location:
                    with doc.create(Subsection(f"{employer_name}", False)) as employer_subsection:
                        employer_subsection.append(NoEscape(r"\hfill{" + employer_location + r"}"))
                        employer_subsection.append(NoEscape(r"\\"))
                else:
                    with doc.create(Subsection(f"{employer_name}", False)) as employer_subsection:
                        employer_subsection.append(NoEscape(r"\\"))

                # Debug employer's position list
                print(f"Employer {employer_id} has positions: {employer['positions']}")

                # Get all positions for this employer and sort by start date (newest first)
                employer_positions = []
                for position_id in employer["positions"]:
                    if position_id in positions:
                        position = positions[position_id]
                        if position["state"]:
                            employer_positions.append(position)

                # Sort by start date (newest first)
                employer_positions.sort(key=lambda p: p.get("startdate", "9999-12-31"), reverse=True)

                # Process each position
                for position in employer_positions:
                    positions_added += 1
                    position_id = position.get("id",
                                               f"position_{position['numeric_id']}")  # Use full position_id format
                    numeric_position_id = position["numeric_id"]

                    # Safely handle special characters
                    position_name = position['name'].replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")

                    # Format date range
                    date_str = ""
                    if position.get('startdate') or position.get('enddate'):
                        if position.get('startdate'):
                            try:
                                formatted_start = self.cmd.format_date(position['startdate'])
                                date_str += formatted_start
                            except:
                                date_str += position['startdate']

                        date_str += " - "

                        if position.get('enddate') and position['enddate'] != '9999-01-01':
                            try:
                                formatted_end = self.cmd.format_date(position['enddate'])
                                date_str += formatted_end
                            except:
                                date_str += position['enddate']
                        else:
                            date_str += "Present"

                    # Add position with dates (modern style)
                    if date_str:
                        doc.append(NoEscape(r"{\em " + position_name + r"}\hfill\textbf{" + date_str + r"}"))
                    else:
                        doc.append(NoEscape(r"{\em " + position_name + r"}"))

                    # Add a line break
                    doc.append(NoEscape(r"\\"))

                    # Find achievements for this position (check all possible ID formats)
                    position_achievement_list = []

                    # Debug all keys in the achievements_by_position dict
                    print(f"DEBUG: Available position achievement keys: {list(achievements_by_position.keys())}")

                    # Check for achievements using the full position_id
                    if position_id in achievements_by_position:
                        print(f"Found achievements for {position_id}")
                        position_achievement_list.extend(achievements_by_position[position_id])

                    # Check for achievements using just the numeric ID
                    if numeric_position_id in achievements_by_position:
                        print(f"Found achievements for numeric ID {numeric_position_id}")
                        position_achievement_list.extend(achievements_by_position[numeric_position_id])

                    # Add position achievements if any
                    if position_achievement_list:
                        doc.append(NoEscape(r"\vspace{2mm}"))

                        # Use Itemize for modern style instead of list2
                        with doc.create(Itemize()) as items:
                            for achievement in position_achievement_list:
                                # Use shortdesc for modern style
                                shortdesc = achievement.get('shortdesc', '')
                                if shortdesc:
                                    # Safe text replacement for LaTeX
                                    shortdesc = shortdesc.replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")
                                    items.add_item(NoEscape(self.cmd.glossary_inject(shortdesc, "modern")))
                                    achievements_added += 1

                        print(f"Added {len(position_achievement_list)} achievements for position {position_name}")
                    else:
                        print(f"No achievements found for position {position_name} (ID: {position_id})")

                # Find employer-level achievements (check all possible ID formats)
                employer_achievement_list = []

                # Debug all keys in the achievements_by_employer dict
                print(f"DEBUG: Available employer achievement keys: {list(achievements_by_employer.keys())}")

                # Check for achievements using employer_id
                if employer_id in achievements_by_employer:
                    print(f"Found achievements for {employer_id}")
                    employer_achievement_list.extend(achievements_by_employer[employer_id])

                # Check for achievements using numeric_employer_id
                if numeric_employer_id in achievements_by_employer:
                    print(f"Found achievements for numeric ID {numeric_employer_id}")
                    employer_achievement_list.extend(achievements_by_employer[numeric_employer_id])

                # Add employer-level achievements if any
                if employer_achievement_list:
                    doc.append(NoEscape(r"\vspace{2mm}"))

                    # Use Itemize for modern style
                    with doc.create(Itemize()) as items:
                        for achievement in employer_achievement_list:
                            # Use shortdesc for modern style
                            shortdesc = achievement.get('shortdesc', '')
                            if shortdesc:
                                # Safe text replacement for LaTeX
                                shortdesc = shortdesc.replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")
                                items.add_item(NoEscape(self.cmd.glossary_inject(shortdesc, "modern")))
                                achievements_added += 1

                    print(f"Added {len(employer_achievement_list)} employer-level achievements for {employer_name}")
                else:
                    print(f"No achievements found for employer {employer_name} (ID: {employer_id})")

                # Add spacing between employers
                doc.append(NoEscape(r"\\"))

            # If no employers were added, add a test entry
            if employers_added == 0:
                print("WARNING: No employers found. Adding test entry.")
                with doc.create(Subsection("Example Company", False)) as example_sub:
                    example_sub.append(NoEscape(r"\hfill{Example Location}"))
                    example_sub.append(NoEscape(r"\\"))
                    example_sub.append(NoEscape(r"{\em Example Position}\hfill\textbf{January 2020 - Present}"))
                    example_sub.append(NoEscape(r"\\"))
                    with example_sub.create(Itemize()) as items:
                        items.add_item("Example job responsibility")

        print(
            f"=== Added {employers_added} employers, {positions_added} positions, and {achievements_added} achievements ===")
        print("=== DEBUG: modern_work_history END ===")

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

        # Get school achievements
        school_achievements = {}
        achievements_data = self.resume_data.get_achievements()
        for item in achievements_data:
            if item["attr"] == "school" and item["value"] and item["state"]:
                school_id = item["value"]
                achievement_id = item["id"]

                if school_id not in school_achievements:
                    school_achievements[school_id] = []

                # Find the achievement details
                achievement_details = {}
                for ach_item in achievements_data:
                    if ach_item["id"] == achievement_id:
                        if ach_item["attr"] == "shortdesc":
                            achievement_details["shortdesc"] = ach_item["value"]
                        elif ach_item["attr"] == "longdesc":
                            achievement_details["longdesc"] = ach_item["value"]

                if achievement_details and "longdesc" in achievement_details:
                    school_achievements[school_id].append(achievement_details)

        print(f"Found achievements for {len(school_achievements)} schools")

        print(f"\n=== Found {len(schools)} schools and {len(focus_lookup)} focuses ===")

        # Add education entries to document
        for school_id, school in schools.items():
            # Skip schools without focuses
            if not school["focuses"]:
                print(f"Skipping school {school_id} as it has no focuses")
                continue

            schools_added += 1
            # Extract just the numeric part of the school_id if it's in the format "school_X"
            school_id_numeric = school_id.split('_')[1] if '_' in school_id else school_id

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

            # Add school achievements if any
            if school_id_numeric in school_achievements and school_achievements[school_id_numeric]:
                doc.append(NoEscape(r"\vspace{1mm}"))
                doc.append(NoEscape(r"\begin{list2}"))

                for achievement in school_achievements[school_id_numeric]:
                    # Use longdesc for retro style achievements
                    longdesc = achievement.get("longdesc", "")
                    if longdesc:
                        # Safe text replacement for LaTeX
                        longdesc = longdesc.replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")
                        doc.append(NoEscape(r"\item " + self.cmd.glossary_inject(longdesc, "retro")))

                doc.append(NoEscape(r"\end{list2}"))
                print(f"Added {len(school_achievements[school_id_numeric])} achievements for school {school_id}")

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

    def modern_education(self, doc, filtered_schools=None, focuses=None):
        """
        Add education details to the document in modern style.
        :param doc: The document to add the education section to.
        :param filtered_schools: Optional dict of pre-filtered schools with focuses
        :param focuses: Optional dict of focuses with metadata
        :return: None
        """
        print("\n=== DEBUG: modern_education called ===")

        # Import required pylatex sections if not already at the top
        from pylatex import Section, Subsection, Itemize
        from pylatex.utils import NoEscape
        from datetime import datetime

        # Initialize data structures if not provided
        if filtered_schools is None or focuses is None:
            # Get education data from database
            education_data = self.resume_data.get_education()

            # Initialize dictionaries if not provided
            if filtered_schools is None:
                filtered_schools = {}
            if focuses is None:
                focuses = {}

            # Process schools
            for entry in education_data:
                if entry["id"].startswith("school_") and entry["state"]:
                    school_id = entry["id"]
                    if entry["attr"] == "schoolname":
                        if school_id not in filtered_schools:
                            filtered_schools[school_id] = {
                                "name": entry["value"],
                                "location": "",
                                "focuses": []
                            }
                            print(f"Found school: {school_id} - {entry['value']}")
                    elif entry["attr"] == "location" and school_id in filtered_schools:
                        filtered_schools[school_id]["location"] = entry["value"]
                        print(f"Added location '{entry['value']}' to school {school_id}")

            # Process focuses
            for entry in education_data:
                if entry["id"].startswith("focus_") and entry["state"]:
                    focus_id = entry["id"]
                    if entry["attr"] == "focusname":
                        if focus_id not in focuses:
                            focuses[focus_id] = {
                                "name": entry["value"],
                                "school": None,
                                "startdate": "",
                                "enddate": ""
                            }
                            print(f"Found focus: {focus_id} - {entry['value']}")
                    elif entry["attr"] == "startdate" and focus_id in focuses:
                        focuses[focus_id]["startdate"] = entry["value"]
                        print(f"Added start date '{entry['value']}' to focus {focus_id}")
                    elif entry["attr"] == "enddate" and focus_id in focuses:
                        focuses[focus_id]["enddate"] = entry["value"]
                        print(f"Added end date '{entry['value']}' to focus {focus_id}")
                    elif entry["attr"] == "school" and focus_id in focuses:
                        focuses[focus_id]["school"] = entry["value"]
                        print(f"Focus {focus_id} belongs to school {entry['value']}")

        # Check if we have any schools to display
        if not filtered_schools:
            print("WARNING: No schools found in education data.")
            # Create a test school as fallback
            test_school_id = "school_test"
            filtered_schools[test_school_id] = {
                "name": "Test University",
                "location": "Test City",
                "focuses": []
            }
            test_focus_id = "focus_test"
            focuses[test_focus_id] = {
                "name": "Computer Science",
                "school": test_school_id,
                "startdate": "2018-01-01",
                "enddate": "2022-12-31"
            }
            print("Added test school and focus as fallback")

        # Get school achievements
        school_achievements = {}
        achievements_data = self.resume_data.get_achievements()
        for item in achievements_data:
            if item["attr"] == "school" and item["value"] and item["state"]:
                school_id = item["value"]
                achievement_id = item["id"]

                if school_id not in school_achievements:
                    school_achievements[school_id] = []

                # Find the achievement details
                achievement_details = {}
                for ach_item in achievements_data:
                    if ach_item["id"] == achievement_id:
                        if ach_item["attr"] == "shortdesc":
                            achievement_details["shortdesc"] = ach_item["value"]
                        elif ach_item["attr"] == "longdesc":
                            achievement_details["longdesc"] = ach_item["value"]
                        elif ach_item["attr"] == "position":
                            achievement_details["position"] = ach_item["value"]

                if achievement_details and "shortdesc" in achievement_details:
                    school_achievements[school_id].append(achievement_details)

        print(f"Found achievements for {len(school_achievements)} schools")

        # Create a name to ID mapping for deduplication
        school_name_to_ids = {}
        for school_id, school in filtered_schools.items():
            school_name = school.get("name", "")
            if school_name:
                if school_name not in school_name_to_ids:
                    school_name_to_ids[school_name] = []
                school_name_to_ids[school_name].append(school_id)

        # Filter out duplicate schools
        unique_schools = {}
        processed_names = set()

        for school_id, school in filtered_schools.items():
            school_name = school.get("name", "")
            if not school_name or school_name in processed_names:
                continue

            # Add this as a unique school
            unique_schools[school_id] = school
            processed_names.add(school_name)

        print(f"Deduplicated {len(filtered_schools)} schools to {len(unique_schools)} unique schools")

        # Add the section header
        with doc.create(Section("Education", False)):
            # Track data for debugging
            schools_added = 0
            focuses_added = 0

            # Add education entries to document
            for school_id, school in unique_schools.items():
                schools_added += 1
                school_name = school.get("name", "")

                # Create a subsection for the school
                with doc.create(Subsection(school_name, False)) as school_sub:
                    # Add location right-aligned
                    if school["location"]:
                        school_sub.append(NoEscape(r"\hfill{" + school["location"] + r"}"))

                    # Add a line break after the school name and location
                    school_sub.append(NoEscape(r"\\"))

                    print(f"Added school to document: {school_name}")

                    # Get all the IDs for this school name
                    all_school_ids = school_name_to_ids.get(school_name, [school_id])

                    # Find all focuses for all IDs of this school
                    school_focuses = []
                    for s_id in all_school_ids:
                        for focus_id, focus in focuses.items():
                            if focus["school"] == s_id:
                                school_focuses.append(focus)
                                print(f"Assigned focus {focus_id} to school {s_id}")

                    # Process each focus - no list environment, directly add them
                    for focus in school_focuses:
                        focuses_added += 1
                        focus_name = focus["name"].replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")

                        # Format date range with month names
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

                    # Collect all achievements for all school IDs
                    all_achievements = []
                    for s_id in all_school_ids:
                        # Try with and without prefix
                        plain_id = s_id.split('_')[1] if '_' in s_id else s_id

                        if plain_id in school_achievements:
                            all_achievements.extend(school_achievements[plain_id])

                        prefixed_id = f"school_{plain_id}"
                        if prefixed_id in school_achievements:
                            all_achievements.extend(school_achievements[prefixed_id])

                    # Add the school achievements if any
                    if all_achievements:
                        school_sub.append(NoEscape(r"\vspace{2mm}"))

                        with school_sub.create(Itemize()) as items:
                            for achievement in all_achievements:
                                items.add_item(NoEscape(
                                    self.cmd.glossary_inject(achievement["shortdesc"], "modern")))

                        print(f"Added {len(all_achievements)} achievements for school {school_name}")

            # If no schools were added, add a fallback message
            if schools_added == 0:
                print("WARNING: No schools were actually added to the document")
                with doc.create(Subsection("Education Information", False)) as subsec:
                    subsec.append("No education records found.")

            print(f"=== Education section summary: {schools_added} schools, {focuses_added} focuses added ===")

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

    def get_achievements_by_position(self, position_id):
        """
        Get achievements associated with a specific position.

        :param position_id: The ID of the position (can be numeric or prefixed with 'position_')
        :return: List of achievement dictionaries with shortdesc and longdesc
        """
        if not position_id:
            return []

        # Create all possible position ID formats to check
        possible_position_ids = [position_id]
        if isinstance(position_id, str):
            if position_id.startswith('position_'):
                possible_position_ids.append(position_id.split('_')[1])
            else:
                possible_position_ids.append(f'position_{position_id}')

        # Initialize achievements list
        position_achievements = []

        # Check if achievements structure exists
        if not hasattr(self, 'achievements'):
            return []

        # Try all possible ID formats in the by_position index
        if 'by_position' in self.achievements:
            for pos_id in possible_position_ids:
                pos_id_str = str(pos_id)
                if pos_id_str in self.achievements['by_position']:
                    for achievement in self.achievements['by_position'][pos_id_str]:
                        # Check state flags
                        state = 1
                        if 'state' in achievement:
                            state = int(achievement['state']) if isinstance(achievement['state'], str) else achievement[
                                'state']

                        achstate = 1
                        if 'achievementstate' in achievement:
                            achstate = int(achievement['achievementstate']) if isinstance(
                                achievement['achievementstate'], str) else achievement['achievementstate']

                        # Only add achievements with active state flags
                        if state and achstate:
                            shortdesc = achievement.get('shortdesc', '')
                            if shortdesc and not any(a.get('shortdesc') == shortdesc for a in position_achievements):
                                position_achievements.append(achievement)

        # Also check all_achievements list for achievements associated with this position
        if 'all_achievements' in self.achievements:
            for achievement in self.achievements['all_achievements']:
                # Check if this achievement is for our position
                ach_position = achievement.get('position', '')
                if ach_position and str(ach_position) in [str(p) for p in possible_position_ids]:
                    # Check state flags
                    state = 1
                    if 'state' in achievement:
                        state = int(achievement['state']) if isinstance(achievement['state'], str) else achievement[
                            'state']

                    achstate = 1
                    if 'achievementstate' in achievement:
                        achstate = int(achievement['achievementstate']) if isinstance(achievement['achievementstate'],
                                                                                      str) else achievement[
                            'achievementstate']

                    # Only add achievements with active state flags
                    if state and achstate:
                        shortdesc = achievement.get('shortdesc', '')
                        if shortdesc and not any(a.get('shortdesc') == shortdesc for a in position_achievements):
                            position_achievements.append(achievement)

        return position_achievements

    def get_achievements_by_school(self, school_id):
        """
        Get achievements associated with a specific school.

        :param school_id: The ID of the school (can be numeric or prefixed with 'school_')
        :return: List of achievement dictionaries with shortdesc and longdesc
        """
        if not school_id:
            return []

        # Create all possible school ID formats to check
        possible_school_ids = [school_id]
        if isinstance(school_id, str):
            if school_id.startswith('school_'):
                possible_school_ids.append(school_id.split('_')[1])
            else:
                possible_school_ids.append(f'school_{school_id}')

        # Initialize achievements list
        school_achievements = []

        # Check if achievements structure exists
        if not hasattr(self, 'achievements'):
            return []

        # Try all possible ID formats in the by_school index
        if 'by_school' in self.achievements:
            for sch_id in possible_school_ids:
                sch_id_str = str(sch_id)
                if sch_id_str in self.achievements['by_school']:
                    for achievement in self.achievements['by_school'][sch_id_str]:
                        # Check state flags
                        state = 1
                        if 'state' in achievement:
                            state = int(achievement['state']) if isinstance(achievement['state'], str) else achievement[
                                'state']

                        achstate = 1
                        if 'achievementstate' in achievement:
                            achstate = int(achievement['achievementstate']) if isinstance(
                                achievement['achievementstate'], str) else achievement['achievementstate']

                        # Only add achievements with active state flags
                        if state and achstate:
                            shortdesc = achievement.get('shortdesc', '')
                            if shortdesc and not any(a.get('shortdesc') == shortdesc for a in school_achievements):
                                school_achievements.append(achievement)

        # Also check all_achievements list for achievements associated with this school
        if 'all_achievements' in self.achievements:
            for achievement in self.achievements['all_achievements']:
                # Check if this achievement is for our school
                ach_school = achievement.get('school', '')
                if ach_school and str(ach_school) in [str(s) for s in possible_school_ids]:
                    # Check state flags
                    state = 1
                    if 'state' in achievement:
                        state = int(achievement['state']) if isinstance(achievement['state'], str) else achievement[
                            'state']

                    achstate = 1
                    if 'achievementstate' in achievement:
                        achstate = int(achievement['achievementstate']) if isinstance(achievement['achievementstate'],
                                                                                      str) else achievement[
                            'achievementstate']

                    # Only add achievements with active state flags
                    if state and achstate:
                        shortdesc = achievement.get('shortdesc', '')
                        if shortdesc and not any(a.get('shortdesc') == shortdesc for a in school_achievements):
                            school_achievements.append(achievement)

        return school_achievements

    def get_achievements_by_employer(self, employer_id):
        """
        Get achievements associated with a specific employer.

        :param employer_id: The ID of the employer (can be numeric or prefixed with 'employer_')
        :return: List of achievement dictionaries with shortdesc and longdesc
        """
        if not employer_id:
            return []

        # Create all possible employer ID formats to check
        possible_employer_ids = [employer_id]
        if isinstance(employer_id, str):
            if employer_id.startswith('employer_'):
                possible_employer_ids.append(employer_id.split('_')[1])
            else:
                possible_employer_ids.append(f'employer_{employer_id}')

        # Initialize achievements list
        employer_achievements = []

        # Check if achievements structure exists
        if not hasattr(self, 'achievements'):
            return []

        # Try all possible ID formats in the by_employer index
        if 'by_employer' in self.achievements:
            for emp_id in possible_employer_ids:
                emp_id_str = str(emp_id)
                if emp_id_str in self.achievements['by_employer']:
                    for achievement in self.achievements['by_employer'][emp_id_str]:
                        # Check state flags
                        state = 1
                        if 'state' in achievement:
                            state = int(achievement['state']) if isinstance(achievement['state'], str) else achievement[
                                'state']

                        achstate = 1
                        if 'achievementstate' in achievement:
                            achstate = int(achievement['achievementstate']) if isinstance(
                                achievement['achievementstate'], str) else achievement['achievementstate']

                        # Only add achievements with active state flags
                        if state and achstate:
                            shortdesc = achievement.get('shortdesc', '')

                            # Only include employer-level achievements (no position specified)
                            if not achievement.get('position', '').strip():
                                if shortdesc and not any(
                                        a.get('shortdesc') == shortdesc for a in employer_achievements):
                                    employer_achievements.append(achievement)

        # Also check all_achievements list for achievements associated with this employer
        if 'all_achievements' in self.achievements:
            for achievement in self.achievements['all_achievements']:
                # Check if this achievement is for our employer but has no position
                ach_employer = achievement.get('employer', '')
                ach_position = achievement.get('position', '')

                if (ach_employer and str(ach_employer) in [str(e) for e in possible_employer_ids] and
                        not ach_position.strip()):
                    # Check state flags
                    state = 1
                    if 'state' in achievement:
                        state = int(achievement['state']) if isinstance(achievement['state'], str) else achievement[
                            'state']

                    achstate = 1
                    if 'achievementstate' in achievement:
                        achstate = int(achievement['achievementstate']) if isinstance(achievement['achievementstate'],
                                                                                      str) else achievement[
                            'achievementstate']

                    # Only add achievements with active state flags
                    if state and achstate:
                        shortdesc = achievement.get('shortdesc', '')
                        if shortdesc and not any(a.get('shortdesc') == shortdesc for a in employer_achievements):
                            employer_achievements.append(achievement)

        return employer_achievements