"""cellspell.spells.xpath — XPath magic powered by xmllint.

Usage:
    %load_ext cellspell.xpath    # Load only this spell
    %load_ext cellspell          # Or load all spells

Commands:
    %xpath                             Show xmllint version
    %xpath books.xml                   Check well-formedness
    %xpath --rng s.rng books.xml       Validate against RelaxNG
    %xpath --dtd s.dtd books.xml       Validate against DTD
    %xpath --xsd s.xsd books.xml       Validate against XSD

    %%xpath books.xml                  Query an XML file
    %%xpath --format books.xml         Pretty-print XML results
    %%xpath --html page.html           Parse as HTML
    %%xpath --ns dc=http://... f.xml   With namespace
"""

import shutil
import subprocess
import textwrap
from pathlib import Path

from IPython.core.magic import Magics, line_cell_magic, magics_class


def _check_xmllint():
    """Check if xmllint is available on the system."""
    if shutil.which("xmllint") is None:
        raise RuntimeError(
            "xmllint not found. Install it with:\n"
            "  Ubuntu/Debian: sudo apt-get install libxml2-utils\n"
            "  macOS:         brew install libxml2\n"
            "  Alpine:        apk add libxml2-utils\n"
            "  Colab:         !apt-get install -y libxml2-utils"
        )


def _run_xmllint(args, input_text=None):
    """Run xmllint with given arguments and return (stdout, stderr, returncode)."""
    result = subprocess.run(
        ["xmllint"] + args,
        input=input_text,
        capture_output=True,
        text=True,
    )
    return result.stdout, result.stderr, result.returncode


def _format_xml(xml_string):
    """Pretty-print an XML string using xmllint --format."""
    wrapped = xml_string.strip()
    if not wrapped.startswith("<?xml") and not wrapped.startswith("<root>"):
        wrapped = f"<wrapper>{wrapped}</wrapper>"

    stdout, stderr, rc = _run_xmllint(["--format", "-"], input_text=wrapped)
    if rc != 0:
        return xml_string

    lines = stdout.strip().split("\n")
    result_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("<?xml"):
            continue
        if stripped in ("<wrapper>", "</wrapper>"):
            continue
        result_lines.append(line)

    result = "\n".join(result_lines)
    return textwrap.dedent(result).strip()


@magics_class
class XPathMagics(Magics):
    """Jupyter magics for running XPath queries via xmllint."""

    def _show_info(self):
        """Show xmllint version."""
        _, stderr, _ = _run_xmllint(["--version"])
        version = stderr.strip()
        print(f"xmllint: {version}")

    def _validate(self, parts):
        """Validate an XML file.

        Usage:
            %xpath file.xml
            %xpath --dtd schema.dtd file.xml
            %xpath --xsd schema.xsd file.xml
            %xpath --rng schema.rng file.xml
        """
        args = ["--noout"]
        i = 0
        while i < len(parts):
            if parts[i] == "--dtd" and i + 1 < len(parts):
                args.extend(["--dtdvalid", parts[i + 1]])
                i += 2
            elif parts[i] == "--xsd" and i + 1 < len(parts):
                args.extend(["--schema", parts[i + 1]])
                i += 2
            elif parts[i] == "--rng" and i + 1 < len(parts):
                args.extend(["--relaxng", parts[i + 1]])
                i += 2
            else:
                args.append(parts[i])
                i += 1

        stdout, stderr, rc = _run_xmllint(args)
        output = (stdout + stderr).strip()

        if rc == 0:
            print("✓ Valid")
            if output:
                print(output)
        else:
            print("✗ Validation failed:")
            print(output)

    @line_cell_magic
    def xpath(self, line, cell=None):
        """Run XPath queries or validate XML files.

        Line magic (%xpath):
            %xpath                             Show xmllint version
            %xpath file.xml                    Check well-formedness
            %xpath --rng schema.rng file.xml   Validate against RelaxNG
            %xpath --dtd schema.dtd file.xml   Validate against DTD
            %xpath --xsd schema.xsd file.xml   Validate against XSD

        Cell magic (%%xpath):
            %%xpath file.xml
            <xpath expression>
        """
        _check_xmllint()
        line = line.strip()

        # Line magic: %xpath
        if cell is None:
            if not line:
                self._show_info()
                return
            parts = line.split()
            self._validate(parts)
            return

        # Cell magic: %%xpath
        parts = line.split()
        fmt = False
        html_mode = False
        namespaces = []
        xml_file = None

        i = 0
        while i < len(parts):
            if parts[i] == "--format":
                fmt = True
                i += 1
            elif parts[i] == "--html":
                html_mode = True
                i += 1
            elif parts[i] == "--ns" and i + 1 < len(parts):
                namespaces.append(parts[i + 1])
                i += 2
            elif not parts[i].startswith("--"):
                xml_file = parts[i]
                i += 1
            else:
                print(f"Unknown option: {parts[i]}")
                return

        if xml_file is None:
            print("Error: No XML file specified. Usage: %%xpath <filename>")
            return

        if not Path(xml_file).exists():
            print(f"Error: File not found: {xml_file}")
            return

        xpath_expr = cell.strip()
        if not xpath_expr:
            print("Error: No XPath expression provided.")
            return

        cmd_args = []
        if html_mode:
            cmd_args.append("--html")

        if namespaces:
            shell_commands = ""
            for ns in namespaces:
                shell_commands += f"setns {ns}\n"
            shell_commands += f"xpath {xpath_expr}\n"
            shell_commands += "quit\n"

            cmd_args.extend(["--shell", xml_file])
            stdout, stderr, rc = _run_xmllint(cmd_args, input_text=shell_commands)

            lines = stdout.strip().split("\n")
            result_lines = []
            capture = False
            for l in lines:
                if l.startswith("Object is a"):
                    capture = True
                    continue
                if l.strip().startswith("/ >"):
                    continue
                if capture:
                    result_lines.append(l)

            output = "\n".join(result_lines).strip()
        else:
            cmd_args.extend(["--xpath", xpath_expr, xml_file])
            stdout, stderr, rc = _run_xmllint(cmd_args)

            if rc != 0:
                error_msg = stderr.strip() or stdout.strip()
                print(f"XPath error: {error_msg}")
                return

            output = stdout

        if not output or not output.strip():
            print("(no results)")
            return

        if fmt and output.strip().startswith("<"):
            output = _format_xml(output)

        self.shell.user_ns["_xpath"] = output.strip()
        print(output)


def load_ipython_extension(ipython):
    """Load the XPath spell.

    Usage: %load_ext cellspell.xpath
    """
    ipython.register_magics(XPathMagics)
    print("✓ xpath spell loaded — %xpath, %%xpath")


def unload_ipython_extension(ipython):
    """Unload the XPath spell."""
    pass
