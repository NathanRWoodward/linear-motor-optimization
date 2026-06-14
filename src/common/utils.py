import re

from rich.text import Text


class COLORS:
    """For use in rich console output. Not for physical materials."""

    PROPERTY_NAME = "bright_cyan"
    PROPERTY_VALUE = "#FFB86D"

    MAGNITUDE = "#FFB86C"
    UNITS = "#E1E446"

    HEADER_1 = "#FF5555"
    HEADER_2 = "#FF5555"  # CE6534
    HEADER_3 = "#FF5555"  # 50FA7B

    @staticmethod
    def gradient(start_color: str, end_color: str, steps: int) -> list[str]:
        """Generate a gradient of colors between start_color and end_color.

        Args:
            start_color (str): Hex code for the starting color (e.g., "#FF0000").
            end_color (str): Hex code for the ending color (e.g., "#00FF00").
            steps (int): Number of colors to generate in the gradient.
        Returns:
            list[str]: List of hex color codes representing the gradient.
        """
        start_rgb = tuple(int(start_color[i : i + 2], 16) for i in (1, 3, 5))
        end_rgb = tuple(int(end_color[i : i + 2], 16) for i in (1, 3, 5))

        gradient_colors = []
        for step in range(steps):
            ratio = step / max(steps - 1, 1)
            intermediate_rgb = tuple(int(start + (end - start) * ratio) for start, end in zip(start_rgb, end_rgb))
            gradient_colors.append("#{:02X}{:02X}{:02X}".format(*intermediate_rgb))

        return gradient_colors

    @staticmethod
    def Prop(name: str, value: str) -> Text:
        """Format a property name and value with colors for rich console output.

        Args:
            name (str): The property name.
            value (str): The property value.

        Returns:
            Text: Formatted string with colors.
        """
        if contains_rich_markup(value):
            return COLORS.PropName(name).append(Text(": ", style="bold")).append(preserve_and_format(value))

        return COLORS.PropName(name) + Text(": ", style="bold") + COLORS.PropValue(value)

    @staticmethod
    def PropName(name: str) -> Text:
        return Text(name, style=COLORS.PROPERTY_NAME)

    @staticmethod
    def PropValue(value: str) -> Text:
        return Text(value, style=COLORS.PROPERTY_VALUE)

    @staticmethod
    def H1(text: str) -> Text:
        return Text(text, style=COLORS.HEADER_1 + " bold")

    @staticmethod
    def H2(text: str) -> Text:
        return Text(text, style=COLORS.HEADER_2 + " bold")

    @staticmethod
    def H3(text: str) -> Text:
        return Text(text, style=COLORS.HEADER_3 + " bold")

    @staticmethod
    def Units(text: str) -> Text:
        return Text(text, style=COLORS.UNITS)


def title(value: str) -> str:
    """Convert a string to title case, replacing underscores with spaces."""
    return value.replace("_", " ").title()


def contains_rich_markup(text: str) -> bool:
    if not isinstance(text, str):
        return False
    # Checks for unbalanced/basic Rich markup sequences
    return "[" in text and "]" in text and any(style in text for style in ["bold", "italic", "underline", "on ", "color", "dim", "[#", "[/]"])


def preserve_and_format(content, new_style: str = "bold") -> Text:
    """Preserves existing string formatting and applies a new style safely."""
    # Initialize a clean parent container holding the new global style
    container = Text(style=new_style)

    # 1. Handle already instantiated Rich Text objects
    if isinstance(content, Text):
        container.append(content)
        return container

    if not isinstance(content, str):
        container.append(str(content))
        return container

    # 2. Handle ANSI Escape Codes (e.g., \x1b[32m)
    ansi_regex = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    if ansi_regex.search(content):
        container.append(Text.from_ansi(content))
        return container

    # 3. Handle Rich Console Markup (e.g., [red]text[/red])
    if "[" in content and "]" in content:
        container.append(Text.from_markup(content))
        return container

    # 4. Handle plain text
    container.append(content)
    return container
