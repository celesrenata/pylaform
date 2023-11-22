# pylaform
PDF resume/cv generator based on MariaDB, Python3.10 and PyLaTeX

This project requires the installation of the **mariadb** (required by the mariadb python plugin!) as well as

## Installation Instructions
1. Install **jq**, **mariadb**, **mariadb_client**, **your favorite query editor or IDE**.
2. Create a database on your server.
3. Update `config.json` to reflect the configuration you have made for this module.
4. Run: `./inject_db.sh`
5. Edit the database and link: **Employers &rarr; Positions &rarr; Achievements**<br/>
  In addition, link: *Employer*<br/>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&darr;<br/>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Skills**<br/>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&uarr;<br/>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;*Position*<br/>
  From the **Skills** table by filling all the tables with your data!
6. Run: `pip install -r requrements.txt`
7. Navigate to the provided resources directory and follow one of the articles to install the `res.cls` class:
   * [Windows](https://tex.stackexchange.com/questions/2063/how-can-i-manually-install-a-package-on-miktex-windows)
   * [Mac and Linux](https://tex.stackexchange.com/questions/8357/how-to-have-local-package-override-default-package)
## Execute
1. `python pylaform.py --help`
2. Try one of the available options
  * `python pylaform.py --template one-page`
  * `python pylaform.py --template hybrid`
3. Find your resume in the *cwd* as `full.pdf`
4. Get hired!
## Todo
* Find a way to implement nested URLs.
* Implement additional templates